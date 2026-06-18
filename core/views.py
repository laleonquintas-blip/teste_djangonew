from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect


@staff_member_required
def trocar_senha_obrigatoria(request):
    if not request.user.troca_senha_obrigatoria:
        return redirect('/admin/')

    erro = None

    if request.method == 'POST':
        nova = request.POST.get('nova_senha', '')
        confirma = request.POST.get('confirma_senha', '')

        if len(nova) < 8:
            erro = 'A senha deve ter pelo menos 8 caracteres.'
        elif nova != confirma:
            erro = 'As senhas não coincidem.'
        else:
            request.user.set_password(nova)
            request.user.troca_senha_obrigatoria = False
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, '✅ Senha alterada com sucesso!')
            return redirect('/admin/')

    return render(request, 'admin/trocar_senha.html', {
        'erro': erro,
        'site_header': 'Malupe Admin',
        'site_title': 'Malupe Admin',
    })
