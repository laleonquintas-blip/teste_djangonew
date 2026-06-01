from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import CharWidget
from .models import (
    Banco, Empresa, Cliente, Fornecedor,
    Colaborador, Tomador, TipoServico,
    MotivoAusencia, Filial
)


# --- RESOURCES (definem layout e regras de importação) ---

class ColaboradorResource(resources.ModelResource):
    nome = fields.Field(attribute='nome', column_name='nome')
    cpf = fields.Field(attribute='cpf', column_name='cpf')
    departamento = fields.Field(attribute='departamento', column_name='departamento')
    empresa = fields.Field(attribute='empresa', column_name='empresa')

    class Meta:
        model = Colaborador
        import_id_fields = ('cpf',)   # CPF é a chave — evita duplicatas
        fields = ('nome', 'cpf', 'departamento', 'empresa')
        export_order = ('nome', 'cpf', 'departamento', 'empresa')
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        if not row.get('departamento'):
            row['departamento'] = ''


class FilialResource(resources.ModelResource):
    nome = fields.Field(attribute='nome', column_name='nome')
    cnpj = fields.Field(attribute='cnpj', column_name='cnpj')

    class Meta:
        model = Filial
        import_id_fields = ('nome',)   # Nome é a chave — evita duplicatas
        fields = ('nome', 'cnpj')
        export_order = ('nome', 'cnpj')
        skip_unchanged = True
        report_skipped = True


class TomadorResource(resources.ModelResource):
    nome = fields.Field(attribute='nome', column_name='nome')

    class Meta:
        model = Tomador
        import_id_fields = ('nome',)   # Nome é a chave — evita duplicatas
        fields = ('nome',)
        export_order = ('nome',)
        skip_unchanged = True
        report_skipped = True


# --- ADMIN ---

class ColaboradorAdmin(ImportExportModelAdmin):
    resource_classes = [ColaboradorResource]
    list_display = ('id', 'nome', 'cpf', 'departamento', 'empresa')
    search_fields = ('nome', 'cpf')


class FilialAdmin(ImportExportModelAdmin):
    resource_classes = [FilialResource]
    list_display = ('id', 'nome', 'cnpj')
    search_fields = ('nome',)


class TomadorAdmin(ImportExportModelAdmin):
    resource_classes = [TomadorResource]
    list_display = ('id', 'nome')
    search_fields = ('nome',)


class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'razao_social', 'cnpj_cpf', 'tipo', 'valor_contrato', 'data_cadastro')
    search_fields = ('razao_social', 'cnpj_cpf')


class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('id', 'razao_social', 'cnpj_cpf', 'letra_acesso', 'conta_contabil')
    search_fields = ('razao_social', 'cnpj_cpf')


# --- REGISTRO ---

admin.site.register(Banco)
admin.site.register(Empresa)
admin.site.register(TipoServico)
admin.site.register(MotivoAusencia)
admin.site.register(Tomador, TomadorAdmin)
admin.site.register(Colaborador, ColaboradorAdmin)
admin.site.register(Filial, FilialAdmin)
admin.site.register(Cliente, ClienteAdmin)
admin.site.register(Fornecedor, FornecedorAdmin)