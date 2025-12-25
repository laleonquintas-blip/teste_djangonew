from django.apps import AppConfig

class ExtrasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'extras'
    verbose_name = 'Novos Extras' # Nome bonito para o menu

    def ready(self):
        # Esta linha carrega o arquivo signals.py quando o sistema inicia
        import extras.signals