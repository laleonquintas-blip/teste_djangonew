from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.contrib import messages
import cloudinary
import cloudinary.api
import cloudinary.uploader
import io, zipfile, urllib.request, os, mimetypes


def _configure_cloudinary():
    cfg = settings.CLOUDINARY_STORAGE
    cloudinary.config(
        cloud_name=cfg['CLOUD_NAME'],
        api_key=cfg['API_KEY'],
        api_secret=cfg['API_SECRET'],
    )


@staff_member_required
def cloudinary_usage_api(request):
    if not request.user.has_perm('workflow.view_cloudinary_storage'):
        return JsonResponse({'error': 'forbidden'}, status=403)
    try:
        _configure_cloudinary()
        result = cloudinary.api.usage()
        credits = result.get('credits', {})
        used = credits.get('usage', 0)
        limit = credits.get('limit', 25.0)
        percent = credits.get('used_percent', 0)
        return JsonResponse({
            'used': round(used, 2),
            'limit': round(limit, 2),
            'percent': round(percent, 1),
            'available': round(limit - used, 2),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def cloudinary_storage_page(request):
    if not request.user.has_perm('workflow.view_cloudinary_storage'):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    from workflow.models import Despesa

    if request.method == 'POST':
        ids = request.POST.getlist('ids')
        despesas = Despesa.objects.filter(id__in=ids).exclude(comprovante='').exclude(comprovante__isnull=True)
        _configure_cloudinary()
        buffer = io.BytesIO()
        total, erros = 0, 0
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for despesa in despesas:
                try:
                    url = despesa.comprovante.url
                    with urllib.request.urlopen(url) as resp:
                        data = resp.read()
                        content_type = resp.headers.get('Content-Type', '').split(';')[0].strip()
                        ext = mimetypes.guess_extension(content_type) or ''
                        # mimetypes pode retornar .jpe/.jpeg → normaliza para .jpg
                        ext = {'.jpe': '.jpg', '.jpeg': '.jpg'}.get(ext, ext)
                    if not ext:
                        _, ext = os.path.splitext(despesa.comprovante.name)
                    ext = ext.lstrip('.').lower() or 'bin'
                    nome = f"ocorrencia_{despesa.id}_comprovante.{ext}"
                    zf.writestr(nome, data)
                    public_id = despesa.comprovante.name.rsplit('.', 1)[0]
                    cloudinary.uploader.destroy(public_id, resource_type='raw', invalidate=True)
                    cloudinary.uploader.destroy(public_id, resource_type='image', invalidate=True)
                    despesa.comprovante = None
                    despesa.save(update_fields=['comprovante'])
                    total += 1
                except Exception:
                    erros += 1
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="comprovantes_malupe.zip"'
        return response

    despesas = Despesa.objects.exclude(comprovante='').exclude(comprovante__isnull=True).order_by('-id')
    context = {
        'title': 'Armazenamento Cloudinary',
        'despesas': despesas,
        'opts': Despesa._meta,
    }
    return render(request, 'admin/workflow/cloudinary_storage.html', context)
