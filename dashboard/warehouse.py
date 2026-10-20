"""Penelusuran seluruh tabel warehouse dengan nama tabel dari whitelist tetap."""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import DatabaseError, connections
from .analytics import query

TABLES = {
    "fact_posisi_keuangan": ("Posisi keuangan", "OJK · uang dalam rupiah penuh; snapshot bulanan. Liabilitas Januari–Oktober 2023 perlu pemeriksaan.", "id_keuangan"),
    "fact_premi_klaim": ("Premi dan klaim", "OJK · rupiah penuh · kumulatif YTD; bukan nilai bulanan.", "id_premi_klaim"),
    "fact_indikator_asuransi": ("Indikator asuransi BI", "BI Tabel 6 · satuan mengikuti masing-masing indikator; klasifikasi jenis mengikuti ETL.", "id_statistik"),
    "fact_penduduk": ("Penduduk", "BPS · penduduk dalam ribu jiwa; persentase/laju dalam %, kepadatan jiwa/km², rasio JK laki-laki per 100 perempuan. Indonesia merupakan baris nasional.", "id_penduduk"),
    "fact_makroekonomi": ("Makroekonomi", "BI Tabel 2 · satuan dan penanda angka mengikuti sumber.", "id_makro"),
    "dim_waktu": ("Dimensi waktu", "Periode bulanan dan tahunan memiliki ID berbeda.", "id_waktu"),
    "dim_jenis_asuransi": ("Dimensi jenis asuransi", "Daftar jenis; keberadaan dimensi tidak berarti setiap fakta memiliki semua jenis.", "id_jenis_asuransi"),
    "dim_provinsi": ("Dimensi provinsi", "38 provinsi dan Indonesia; is_nasional=1 untuk total nasional.", "id_provinsi"),
    "dim_indikator": ("Katalog indikator", "Semua indikator, termasuk indikator tanpa nilai fakta pada periode yang dimuat. Nama dapat sama; kode indikator menjadi pembeda.", "id_indikator"),
}


def table_rows(table):
    # Input wajib sudah divalidasi terhadap TABLES; tidak menerima SQL dari pengguna.
    if table not in TABLES:
        raise ValueError("Tabel tidak tersedia")
    pk = TABLES[table][2]
    select, joins = "f.*", ""
    if table.startswith("fact_"):
        select += ",w.kode_periode,w.tingkat_periode,w.tahun,w.bulan"
        joins += " LEFT JOIN dim_waktu w ON w.id_waktu=f.id_waktu"
        if table in {"fact_posisi_keuangan", "fact_premi_klaim", "fact_indikator_asuransi"}:
            select += ",j.kode_industri,j.nama_industri"
            joins += " LEFT JOIN dim_jenis_asuransi j ON j.id_jenis_asuransi=f.id_jenis_asuransi"
        if table in {"fact_indikator_asuransi", "fact_makroekonomi"}:
            select += ",i.kode_indikator,i.nama_indikator,i.satuan,i.sumber_tabel"
            joins += " LEFT JOIN dim_indikator i ON i.id_indikator=f.id_indikator"
        if table == "fact_penduduk":
            select += ",p.nama_provinsi,p.is_nasional"
            joins += " LEFT JOIN dim_provinsi p ON p.id_provinsi=f.id_provinsi"
    # Seluruh nilai asli tetap tersedia, termasuk ID, NULL, status angka, dan desimal.
    with connections["analytics"].cursor() as cursor:
        cursor.execute(f"SELECT {select} FROM {table} f {joins} ORDER BY f.{pk}")
        columns = [column[0] for column in cursor.description]
        rows = [list(row) for row in cursor.fetchall()]
    return columns, rows


def get_warehouse(table):
    if not settings.ANALYTICS_ENABLED:
        return {"status": "disabled"}
    try:
        count_rows = query(" UNION ALL ".join(f"SELECT '{name}' AS table_name,COUNT(*) AS total FROM {name}" for name in TABLES))
        counts = {r["table_name"]: r["total"] for r in count_rows}
        columns, rows = table_rows(table)
        return {
            "status": "ready", "table": table,
            "title": TABLES[table][0], "description": TABLES[table][1],
            "tables": [{"key": key, "label": value[0], "count": counts[key]} for key, value in TABLES.items()],
            "columns": columns, "rows": rows, "count": len(rows),
            "total_rows": sum(counts.values()),
        }
    except (DatabaseError, ImproperlyConfigured):
        return {"status": "unavailable"}
