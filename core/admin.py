# core/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group  # Importa o Grupo original do Django
from .models import UsuarioCustomizado, Grupo  # Importa o nosso Grupo (agora ele existe!)

# 1. Remove o Grupo original do menu antigo
admin.site.unregister(Group)

# 2. Registra o nosso Grupo Proxy no menu novo
admin.site.register(Grupo, GroupAdmin)


# 3. Registra o Usuário
class UsuarioCustomizadoAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'acesso_despesa', 'is_staff')

    fieldsets = UserAdmin.fieldsets + (
        ('Regras de Negócio (Workflow)', {'fields': ('acesso_despesa', 'troca_senha_obrigatoria')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Regras de Negócio', {'fields': ('acesso_despesa', 'troca_senha_obrigatoria')}),
    )


admin.site.register(UsuarioCustomizado, UsuarioCustomizadoAdmin)