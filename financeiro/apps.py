from django.apps import AppConfig


class FinanceiroConfig(AppConfig):
    nefault_auto_field = 'django.db.models.BigAutoField'
    name = 'financeiro'
    verbose_name = 'Financeiro'

    def ready(self):
        # Esta linha é OBRIGATÓRIA para os Signals funcionarem
        import financeiro.signals
