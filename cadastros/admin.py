from django.contrib import admin
# Importa a funcionalidade de Importação/Exportação para carga em massa
from import_export.admin import ImportExportModelAdmin
from .models import (
    Banco, Empresa, Cliente, Fornecedor,
    Colaborador, Tomador, TipoServico,
    MotivoAusencia, Filial  # <-- Filial incluída
)


# --- 1. CLASSES ADMIN CUSTOMIZADAS (Para Import/Export ou Listagem Detalhada) ---

# Usa ImportExportModelAdmin para habilitar a Carga em Massa
class ColaboradorAdmin(ImportExportModelAdmin):
    list_display = ('id', 'nome', 'cpf', 'departamento', 'empresa')
    search_fields = ('nome', 'cpf')


# Usa ImportExportModelAdmin para habilitar a Carga em Massa
class FilialAdmin(ImportExportModelAdmin):
    list_display = ('id', 'nome', 'cnpj')
    search_fields = ('nome',)


class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'razao_social', 'cnpj_cpf', 'tipo', 'valor_contrato', 'data_cadastro')
    search_fields = ('razao_social', 'cnpj_cpf')


class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('id', 'razao_social', 'cnpj_cpf', 'letra_acesso', 'conta_contabil')
    search_fields = ('razao_social', 'cnpj_cpf')


# --- 2. REGISTRO DOS MODELOS NO PAINEL ADMIN ---

# Modelos Simples (sem customização extra)
admin.site.register(Banco)
admin.site.register(Empresa)
admin.site.register(TipoServico)
admin.site.register(MotivoAusencia)
admin.site.register(Tomador)

# Modelos que usam as classes customizadas
admin.site.register(Colaborador, ColaboradorAdmin)  # Agora com Import/Export
admin.site.register(Filial, FilialAdmin)  # Agora incluso e com Import/Export
admin.site.register(Cliente, ClienteAdmin)
admin.site.register(Fornecedor, FornecedorAdmin)