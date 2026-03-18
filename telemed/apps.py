from django.apps import AppConfig


class TelemedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'telemed'

    def ready(self):
        import telemed.signals
