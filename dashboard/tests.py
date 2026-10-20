from decimal import Decimal as D
from django.test import SimpleTestCase
from .analytics import build_dashboard, monthly_value, ratio


class AnalyticsCalculationsTests(SimpleTestCase):
    def fixture(self, requested=2024):
        finance = [{"tahun": y, "bulan": 12, "total_aset": D("600000000000000"), "total_investasi": D("480000000000000"), "total_ekuitas": D("100000000000000")} for y in [2023, 2024]]
        premiums = [
            {"tahun": 2023, "bulan": 12, "premi_ytd": D("100000000000000"), "klaim_ytd": D("80000000000000")},
            {"tahun": 2024, "bulan": 1, "premi_ytd": D("10000000000000"), "klaim_ytd": D("7000000000000")},
            {"tahun": 2024, "bulan": 2, "premi_ytd": D("25000000000000"), "klaim_ytd": D("16000000000000")},
            {"tahun": 2024, "bulan": 12, "premi_ytd": D("120000000000000"), "klaim_ytd": D("90000000000000")},
        ]
        population = [
            {"tahun": 2024, "is_nasional": 1, "jumlah_penduduk_ribu": D("200000"), "nama_provinsi": "Indonesia"},
            {"tahun": 2024, "is_nasional": 0, "jumlah_penduduk_ribu": D("100000"), "nama_provinsi": "Provinsi A"},
            {"tahun": 2024, "is_nasional": 0, "jumlah_penduduk_ribu": None, "nama_provinsi": "Provinsi B"},
        ]
        return build_dashboard(finance, premiums, population, [], [], requested)

    def test_ytd_is_not_summed_and_units_are_converted(self):
        result = self.fixture()
        self.assertEqual(result["cards"][1]["value"], 120)
        self.assertEqual(result["cards"][3]["value"], 75)
        self.assertEqual(result["charts"]["monthly"]["series"][0]["values"][:2], [10, 15])
        self.assertEqual(result["charts"]["ytd"]["series"][0]["values"][:2], [10, 25])

    def test_national_population_is_used_once(self):
        result = self.fixture()
        self.assertEqual(result["density"], 600000)
        self.assertEqual(result["population"], 200)
        self.assertEqual(len(result["province_rows"]), 2)
        self.assertNotIn("Indonesia", result["charts"]["population"]["labels"])

    def test_growth_requires_previous_year_and_missing_month_stays_missing(self):
        result = self.fixture()
        self.assertEqual(result["charts"]["macro"]["series"][0]["values"], [None, 20])
        self.assertIsNone(result["charts"]["monthly"]["series"][0]["values"][11])
        self.assertEqual(monthly_value(D(10), D(100), 1), 10)
        self.assertIsNone(monthly_value(D(10), None, 2))
        self.assertIsNone(ratio(1, 0))

    def test_invalid_year_and_absent_sources(self):
        self.assertEqual(self.fixture("invalid")["year"], 2024)
        result = self.fixture(2023)
        self.assertIsNone(result["density"])
        self.assertEqual(build_dashboard([], [], [], [], [])["status"], "empty")


class CompleteDataTests(SimpleTestCase):
    def test_indicator_catalogue_keeps_unpopulated_entries_and_zero(self):
        from .analytics import build_exploration
        catalogue = [
            {"kode_indikator": "T6-001", "nama_indikator": "Contoh", "satuan": "%"},
            {"kode_indikator": "T2-002", "nama_indikator": "Belum dimuat", "satuan": "%"},
        ]
        records = [{"tahun": 2024, "kode_indikator": "T6-001", "nilai": D("0.0000"), "kode_industri": "PAJ"}]
        population = [{"tahun": 2024, "nama_provinsi": "Contoh", "is_nasional": 0, "jumlah_penduduk_ribu": None, "persentase_penduduk": D("0.00"), "rasio_jenis_kelamin": D("101.20")}]
        result = build_exploration(records, [], catalogue, population, 2024)
        self.assertEqual(result["catalogue_count"], 2)
        self.assertEqual(result["catalogue_with_values"], 1)
        self.assertEqual(result["explorer"]["catalogue"][1]["fact_count"], 0)
        self.assertEqual(result["explorer"]["records"][0]["nilai"], 0)
        self.assertIsNone(result["explorer"]["population"][0]["jumlah_penduduk_ribu"])
        self.assertEqual(result["explorer"]["population"][0]["rasio_jenis_kelamin"], 101.2)
        self.assertEqual(len(result["explorer"]["metrics"]), 5)

    def test_table_names_are_whitelisted_before_database_access(self):
        from .warehouse import table_rows
        with self.assertRaises(ValueError):
            table_rows("fact_penduduk; DROP TABLE dim_waktu")

    def test_raw_display_distinguishes_zero_and_missing(self):
        from .templatetags.data_format import data_value
        self.assertEqual(data_value(None), "—")
        self.assertNotEqual(data_value(D("0.00")), "—")
        self.assertIn("1234", data_value(D("0.1234")))

    def test_explorer_and_csv_require_login(self):
        from types import SimpleNamespace
        from django.test import RequestFactory
        from .views import warehouse
        request = RequestFactory().get("/data/?format=csv", HTTP_HOST="localhost")
        request.user = SimpleNamespace(is_authenticated=False)
        self.assertEqual(warehouse(request).status_code, 302)

    def test_csv_preserves_money_and_null(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from django.test import RequestFactory
        from .views import warehouse
        request = RequestFactory().get("/data/?tabel=fact_posisi_keuangan&format=csv")
        request.user = SimpleNamespace(is_authenticated=True)
        with patch("dashboard.warehouse.get_warehouse", return_value={"status":"ready", "columns":["money","missing"], "rows":[[D("515759574762370.00"),None]]}):
            response = warehouse(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("515759574762370.00,", response.content.decode("utf-8-sig"))


class PopulationMapTests(SimpleTestCase):
    def test_geography_has_38_distinct_provinces(self):
        from .population_map import map_shapes, province_key
        shapes = map_shapes()
        self.assertEqual(len(shapes), 38)
        self.assertEqual(len({r["key"] for r in shapes}), 38)
        self.assertEqual(province_key("Daerah Istimewa Yogyakarta"), province_key("DI Yogyakarta"))
        self.assertTrue(all(r["path"].startswith("M") and r["path"].endswith("Z") for r in shapes))

    def test_color_thresholds_are_fixed_and_null_is_not_zero(self):
        from .population_map import population_color, MISSING_COLOR
        self.assertEqual(population_color(None)[0], MISSING_COLOR)
        self.assertNotEqual(population_color(0)[0], MISSING_COLOR)
        self.assertEqual(population_color(999999)[0], "#d1fae5")
        self.assertEqual(population_color(1000000)[0], "#a7f3d0")
        self.assertEqual(population_color(20000000)[0], "#065f46")

    def test_map_uses_people_units_and_excludes_national_total(self):
        from .population_map import build_population_map
        rows = [
            {"tahun":2023,"nama_provinsi":"Jawa Barat","is_nasional":0,"jumlah_penduduk_ribu":D("49860.3")},
            {"tahun":2024,"nama_provinsi":"Jawa Barat","is_nasional":0,"jumlah_penduduk_ribu":D("50000")},
            {"tahun":2023,"nama_provinsi":"Indonesia","is_nasional":1,"jumlah_penduduk_ribu":D("278696.2")},
            {"tahun":2023,"nama_provinsi":"Papua Selatan","is_nasional":0,"jumlah_penduduk_ribu":None},
        ]
        result = build_population_map(rows,2023)
        records = {r["name"]:r for r in result["payload"]["provinces"]}
        self.assertEqual(records["Jawa Barat"]["people"],49860300)
        self.assertIsNone(records["Papua Selatan"]["people"])
        self.assertEqual(result["available"],1)
        self.assertNotIn("Indonesia",records)
