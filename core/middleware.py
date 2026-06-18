from django.shortcuts import redirect
from django.urls import reverse


class TrocaSenhaObrigatoriaMiddleware:
    """Redireciona usuários com troca_senha_obrigatoria=True para a página de troca."""

    URLS_LIVRES = [
        '/admin/trocar-senha/',
        '/admin/login/',
        '/admin/logout/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and hasattr(request.user, 'troca_senha_obrigatoria')
            and request.user.troca_senha_obrigatoria
            and request.path not in self.URLS_LIVRES
        ):
            return redirect('/admin/trocar-senha/')
        return self.get_response(request)
