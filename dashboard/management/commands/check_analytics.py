from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connections
from django.core.exceptions import ImproperlyConfigured

from dashboard.analytics import EXPECTED_TABLES, get_summary


class Command(BaseCommand):
    help = 'Periksa koneksi dan tabel warehouse tanpa mengubah data.'

    def handle(self, *args, **options):
        if not settings.ANALYTICS_ENABLED:
            raise CommandError('Koneksi belum aktif. Isi ANALYTICS_ENABLED=1 terlebih dahulu.')
        expected = {
            'dim_waktu': 39, 'dim_jenis_asuransi': 5, 'dim_provinsi': 39,
            'dim_indikator': 214, 'fact_posisi_keuangan': 36,
            'fact_premi_klaim': 36, 'fact_indikator_asuransi': 329,
            'fact_penduduk': 117, 'fact_makroekonomi': 9,
        }
        try:
            connection = connections['analytics']
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
                missing = EXPECTED_TABLES - tables
                if missing:
                    raise CommandError('Tabel belum tersedia: ' + ', '.join(sorted(missing)))
                for table, baseline in expected.items():
                    # Nama tabel berasal dari konstanta internal, bukan input pengguna.
                    cursor.execute('SELECT COUNT(*) FROM ' + connection.ops.quote_name(table))
                    count = cursor.fetchone()[0]
                    self.stdout.write(f'{table}: {count} baris (snapshot dokumen: {baseline})')
            status = get_summary()['status']
            if status == 'unavailable':
                raise CommandError('Tabel tersedia tetapi kolom/kueri ringkasan gagal. Periksa skema SQL.')
            self.stdout.write(self.style.SUCCESS(f'Koneksi berhasil. Status ringkasan: {status}'))
        except (DatabaseError, ImproperlyConfigured) as exc:
            raise CommandError('Tidak dapat membaca warehouse. Periksa driver, versi server, koneksi, dan hak SELECT.') from exc
