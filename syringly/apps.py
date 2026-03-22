from django.apps import AppConfig


class SyringlyConfig(AppConfig):
    name = 'syringly'

    def ready(self):
        import syringly.signals  # noqa
