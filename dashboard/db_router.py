class AnalyticsRouter:
    """Tabel warehouse dimiliki ETL, bukan migrasi Django."""

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'analytics':
            return False
        return None
