from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import CharWidget
from .models import (
    Banco, Empresa, Cliente, Fornecedor,
    Colaborador, ColaboradorInfo, Tomador, TipoServico,
    MotivoAusencia, Filial, PlanoDeContas
)


# --- RESOURCES (definem layout e regras de importação) ---

class ColaboradorResource(resources.ModelResource):
    nome = fields.Field(attribute='nome', column_name='nome')
    cpf = fields.Field(attribute='cpf', column_name='cpf')
    departamento = fields.Field(attribute='departamento', column_name='departamento')
    empresa = fields.Field(attribute='empresa', column_name='empresa')
    filial = fields.Field(column_name='filial')

    class Meta:
        model = Colaborador
        import_id_fields = ('cpf',)
        fields = ('nome', 'cpf', 'departamento', 'empresa', 'filial')
        export_order = ('nome', 'cpf', 'departamento', 'empresa', 'filial')
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        if not row.get('departamento'):
            row['departamento'] = ''

    def dehydrate_filial(self, obj):
        return obj.filial.nome if obj.filial else ''

    def import_field(self, field, obj, data, is_m2m=False, **kwargs):
        if field.column_name == 'filial':
            nome_filial = data.get('filial', '').strip()
            if nome_filial:
                filial_obj = Filial.objects.filter(nome__iexact=nome_filial).first()
                obj.filial = filial_obj
            return
        super().import_field(field, obj, data, is_m2m, **kwargs)


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
    list_display = ('id', 'nome', 'cpf', 'departamento', 'empresa', 'filial')
    search_fields = ('nome', 'cpf', 'departamento', 'empresa')

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
    fields = (
        'tipo',
        'razao_social', 'cnpj_cpf',
        'dia_vencimento', 'valor_contrato',
        'descricao_atividade', 'forma_recebimento',
        'ativo',
    )

    class Media:
        js = ('admin/js/jquery.init.js', 'js/admin_cliente_tipo.js',)


class PlanoDeContasAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'conta_contabil')
    search_fields = ('nome', 'conta_contabil')


class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('id', 'razao_social', 'cnpj_cpf', 'letra_acesso', 'plano_de_contas')
    search_fields = ('razao_social', 'cnpj_cpf')


class ColaboradorInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'cpf', 'tipo_pix', 'chave_pix')
    search_fields = ('nome', 'cpf', 'chave_pix')
    list_per_page = 30
    fields = ('nome', 'cpf', 'tipo_pix', 'chave_pix', 'observacoes')

    def has_module_perms(self, request):
        return request.user.is_active

    def has_view_permission(self, request, obj=None):
        return request.user.is_active

    def has_add_permission(self, request):
        return request.user.is_active

    def has_change_permission(self, request, obj=None):
        return request.user.is_active

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# --- REGISTRO ---
admin.site.register(ColaboradorInfo, ColaboradorInfoAdmin)

admin.site.register(Banco)
admin.site.register(Empresa)
admin.site.register(TipoServico)
admin.site.register(MotivoAusencia)
admin.site.register(Tomador, TomadorAdmin)
admin.site.register(Colaborador, ColaboradorAdmin)
admin.site.register(Filial, FilialAdmin)
admin.site.register(Cliente, ClienteAdmin)
admin.site.register(Fornecedor, FornecedorAdmin)
admin.site.register(PlanoDeContas, PlanoDeContasAdmin)