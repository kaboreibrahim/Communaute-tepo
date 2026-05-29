from django.apps import AppConfig


class HistoireConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Apps.histoire'
    verbose_name = "Historique"

    def ready(self):
        from . import signals  # noqa: F401
