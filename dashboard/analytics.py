"""Pembacaan warehouse dan perhitungan analitik; tidak menulis ke database."""
import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, connections

logger = logging.getLogger(__name__)
TRILLION = Decimal("1000000000000")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
EXPECTED_TABLES = {
    "dim_waktu", "dim_jenis_asuransi", "dim_provinsi", "dim_indikator",
    "fact_posisi_keuangan", "fact_premi_klaim", "fact_indikator_asuransi",
    "fact_penduduk", "fact_makroekonomi",
}


def query(sql, params=None):
    with connections["analytics"].cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def ratio(numerator, denominator, scale=100):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return Decimal(str(numerator)) / Decimal(str(denominator)) * scale


def number(value, divisor=1):
    return None if value is None else float(Decimal(str(value)) / Decimal(str(divisor)))


def monthly_value(current, previous, month):
    # Tidak menganggap bulan hilang sebagai nol; reset YTD setiap Januari.
    if current is None or (month != 1 and previous is None):
        return None
    return current if month == 1 else current - previous


def build_dashboard(finance, premiums, population, macro, companies, requested_year=None):
    """Gabungkan sumber pada grain tahun, bukan join fakta yang menggandakan baris."""
    years = sorted({int(r["tahun"]) for r in finance + premiums})
    if not years:
        return {"status": "empty"}
    try:
        selected = int(requested_year)
    except (ValueError, TypeError):
        selected = years[-1]
    if selected not in years:
        selected = years[-1]
    fin = {(int(r["tahun"]), int(r["bulan"])): r for r in finance}
    pre = {(int(r["tahun"]), int(r["bulan"])): r for r in premiums}
    national = {int(r["tahun"]): r for r in population if r["is_nasional"]}
    macros = {(int(r["tahun"]), r["kode_indikator"]): r for r in macro}
    annual = []
    for year in years:
        f, p, prev = fin.get((year, 12), {}), pre.get((year, 12), {}), pre.get((year-1, 12), {})
        pop = national.get(year, {}).get("jumlah_penduduk_ribu")
        premium, claim = p.get("premi_ytd"), p.get("klaim_ytd")
        growth = ratio(premium, prev.get("premi_ytd"))
        annual.append({
            "tahun": year, "premium": premium, "claim": claim,
            "asset": f.get("total_aset"), "investment": f.get("total_investasi"),
            "claim_ratio": ratio(claim, premium),
            "growth": None if growth is None else growth-100,
            "population": None if pop is None else pop*1000,
            "density": ratio(premium, None if pop is None else pop*1000, 1),
        })
    current = next(r for r in annual if r["tahun"] == selected)
    cards = []
    for label, key, unit, divisor in [
        ("Aset akhir tahun", "asset", "Rp triliun · posisi Desember", TRILLION),
        ("Premi tahunan", "premium", "Rp triliun · YTD Desember", TRILLION),
        ("Klaim tahunan", "claim", "Rp triliun · YTD Desember", TRILLION),
        ("Klaim terhadap premi", "claim_ratio", "% · klaim ÷ premi", 1),
    ]:
        cards.append({"label": label, "value": number(current[key], divisor), "unit": unit})
    labels, monthly_premiums, monthly_claims, ytd_premiums, ytd_claims, ratios = MONTHS, [], [], [], [], []
    monthly_rows = []
    for month in range(1, 13):
        p, prev, f = pre.get((selected, month), {}), pre.get((selected, month-1), {}), fin.get((selected, month), {})
        pm = monthly_value(p.get("premi_ytd"), prev.get("premi_ytd"), month)
        cm = monthly_value(p.get("klaim_ytd"), prev.get("klaim_ytd"), month)
        monthly_premiums.append(number(pm, TRILLION))
        monthly_claims.append(number(cm, TRILLION))
        ytd_premiums.append(number(p.get("premi_ytd"), TRILLION))
        ytd_claims.append(number(p.get("klaim_ytd"), TRILLION))
        ratios.append(number(ratio(p.get("klaim_ytd"), p.get("premi_ytd"))))
        monthly_rows.append({"month": MONTHS[month-1], "premium": monthly_premiums[-1], "claim": monthly_claims[-1], "premium_ytd": ytd_premiums[-1], "claim_ytd": ytd_claims[-1], "asset": number(f.get("total_aset"), TRILLION), "investment": number(f.get("total_investasi"), TRILLION), "equity": number(f.get("total_ekuitas"), TRILLION), "liability": number(f.get("total_liabilitas"), TRILLION), "liability_flag": selected == 2023 and month <= 10})
    chart_data = {
        "monthly": {"labels": labels, "series": [{"name": "Premi", "values": monthly_premiums}, {"name": "Klaim", "values": monthly_claims}]},
        "ytd": {"labels": labels, "series": [{"name": "Premi YTD", "values": ytd_premiums}, {"name": "Klaim YTD", "values": ytd_claims}]},
        "ratio": {"labels": labels, "series": [{"name": "Klaim / premi YTD", "values": ratios}]},
        "finance": {"labels": labels, "series": [{"name": title, "values": [None if key == "total_liabilitas" and selected == 2023 and month <= 10 else number(fin.get((selected, month), {}).get(key), TRILLION) for month in range(1, 13)]} for title, key in [("Aset", "total_aset"), ("Investasi", "total_investasi"), ("Ekuitas", "total_ekuitas"), ("Liabilitas", "total_liabilitas")]]},
        "density": {"labels": [str(r["tahun"]) for r in annual], "series": [{"name": "Premi per penduduk", "values": [number(r["density"]) for r in annual]}]},
        "macro": {"labels": [str(r["tahun"]) for r in annual], "series": [{"name": "Pertumbuhan premi YoY", "values": [number(r["growth"]) for r in annual]}] + [{"name": title, "values": [number(macros.get((r["tahun"], code), {}).get("nilai")) for r in annual]} for title, code in [("Pertumbuhan ekonomi", "T2-038"), ("Inflasi YoY", "T2-045"), ("BI Rate", "T2-044")]]},
    }
    company_rows = [r for r in companies if int(r["tahun"]) == selected]
    chart_data["companies"] = {"labels": [r["nama_indikator"] for r in company_rows], "series": [{"name": "Perusahaan", "values": [number(r["nilai"]) for r in company_rows]}]}
    province_rows = sorted([r for r in population if int(r["tahun"]) == selected and not r["is_nasional"]], key=lambda r: (r["jumlah_penduduk_ribu"] is not None, r["jumlah_penduduk_ribu"] or 0), reverse=True)
    chart_data["population"] = {"labels": [r["nama_provinsi"] for r in province_rows[:10]], "series": [{"name": "Penduduk (juta jiwa)", "values": [number(r["jumlah_penduduk_ribu"], 1000) for r in province_rows[:10]]}]}
    macro_rows = [{"year": int(r["tahun"]), "label": r["nama_indikator"], "value": number(r["nilai"]), "status": r.get("status_angka") or "", "unit": r["satuan"]} for r in macro]
    return {
        "status": "ready", "year": selected, "years": years, "period": f"{selected}-12",
        "cards": cards, "charts": chart_data, "monthly_rows": monthly_rows,
        "density": number(current["density"]), "population": number(current["population"], 1000000),
        "growth": number(current["growth"]), "investment_share": number(ratio(current["investment"], current["asset"])),
        "province_rows": province_rows, "macro_rows": macro_rows,
        "annual_complete": all(current[k] is not None for k in ["asset", "premium", "claim"]),
    }


def get_dashboard(requested_year=None):
    if not settings.ANALYTICS_ENABLED:
        return {"status": "disabled"}
    try:
        with connections["analytics"].cursor() as cursor:
            tables = set(connections["analytics"].introspection.table_names(cursor))
        if EXPECTED_TABLES - tables:
            return {"status": "schema_missing"}
        finance = query("""
            SELECT w.tahun,w.bulan,f.total_aset,f.total_investasi,f.total_ekuitas,f.total_liabilitas
            FROM fact_posisi_keuangan f JOIN dim_waktu w USING(id_waktu)
            JOIN dim_jenis_asuransi j USING(id_jenis_asuransi)
            WHERE j.kode_industri=%s AND w.tingkat_periode=%s ORDER BY w.tahun,w.bulan
        """, ["PAJ", "BULANAN"])
        premiums = query("""
            SELECT w.tahun,w.bulan,f.premi_ytd,f.klaim_ytd FROM fact_premi_klaim f
            JOIN dim_waktu w USING(id_waktu) JOIN dim_jenis_asuransi j USING(id_jenis_asuransi)
            WHERE j.kode_industri=%s AND w.tingkat_periode=%s ORDER BY w.tahun,w.bulan
        """, ["PAJ", "BULANAN"])
        population = query("""
            SELECT w.tahun,p.nama_provinsi,p.is_nasional,f.jumlah_penduduk_ribu,
                   f.laju_pertumbuhan,f.kepadatan_penduduk,f.persentase_penduduk,f.rasio_jenis_kelamin
            FROM fact_penduduk f JOIN dim_waktu w USING(id_waktu)
            JOIN dim_provinsi p USING(id_provinsi) WHERE w.tingkat_periode=%s
            ORDER BY w.tahun,p.nama_provinsi
        """, ["TAHUNAN"])
        macro = query("""
            SELECT w.tahun,i.kode_indikator,i.nama_indikator,i.satuan,f.nilai,f.status_angka
            FROM fact_makroekonomi f JOIN dim_waktu w USING(id_waktu)
            JOIN dim_indikator i USING(id_indikator) WHERE w.tingkat_periode=%s
            ORDER BY w.tahun,i.kode_indikator
        """, ["TAHUNAN"])
        indicators = query("""
            SELECT w.tahun,w.kode_periode,w.tingkat_periode,
                   j.kode_industri,j.nama_industri,i.kode_indikator,
                   i.nama_indikator,i.satuan,i.sumber_tabel,f.nilai,f.status_angka
            FROM fact_indikator_asuransi f
            JOIN dim_waktu w USING(id_waktu)
            JOIN dim_indikator i USING(id_indikator)
            JOIN dim_jenis_asuransi j USING(id_jenis_asuransi)
            ORDER BY i.kode_indikator,j.kode_industri,w.tahun
        """)
        catalogue = query("SELECT * FROM dim_indikator ORDER BY kode_indikator")
        # Company chart is a subset; all BI facts are also available in the explorer.
        companies = [row for row in indicators if row["kode_indikator"] in {"T6-002", "T6-003", "T6-004"}]
        result = build_dashboard(finance, premiums, population, macro, companies, requested_year)
        if result["status"] == "ready":
            result.update(build_exploration(indicators, macro, catalogue, population, result["year"]))
            from .population_map import build_population_map
            result["population_map"] = build_population_map(population, result["year"])
        return result
    except (DatabaseError, ImproperlyConfigured):
        logger.warning("Database analitik belum dapat dibaca; periksa koneksi dan skema.")
        return {"status": "unavailable"}


def get_summary():
    return get_dashboard()


POPULATION_METRICS = [
    ("jumlah_penduduk_ribu", "Jumlah penduduk", "ribu jiwa"),
    ("laju_pertumbuhan", "Laju pertumbuhan", "%"),
    ("persentase_penduduk", "Persentase penduduk nasional", "%"),
    ("kepadatan_penduduk", "Kepadatan penduduk", "jiwa/km²"),
    ("rasio_jenis_kelamin", "Rasio jenis kelamin", "laki-laki per 100 perempuan"),
]


def build_exploration(indicators, macro, catalogue, population, year):
    records = [{**r, "nilai": number(r["nilai"])} for r in indicators]
    records += [{**r, "kode_industri": "MAKRO", "nama_industri": "Makroekonomi", "sumber_tabel": "Tabel 2", "nilai": number(r["nilai"])} for r in macro]
    by_code = {}
    for r in records:
        by_code.setdefault(r["kode_indikator"], []).append(r)
    catalogue_rows = [{**r, "fact_count": len(by_code.get(r["kode_indikator"], []))} for r in catalogue]
    people = [{**r, **{key: number(r.get(key)) for key, _, _ in POPULATION_METRICS}} for r in population]
    return {
        "explorer": {"catalogue": catalogue_rows, "records": records,
                     "population": people, "metrics": [{"key": k, "label": label, "unit": unit} for k, label, unit in POPULATION_METRICS], "year": year},
        "indicator_rows": [r for r in records if int(r["tahun"]) == year],
        "catalogue_count": len(catalogue), "indicator_fact_count": len(indicators), "macro_fact_count": len(macro),
        "catalogue_with_values": len(by_code),
    }
