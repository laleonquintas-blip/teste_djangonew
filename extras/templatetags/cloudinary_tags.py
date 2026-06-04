from django import template
from django.conf import settings
import cloudinary
import cloudinary.api

register = template.Library()

@register.simple_tag
def cloudinary_usage():
    try:
        cfg = settings.CLOUDINARY_STORAGE
        cloudinary.config(
            cloud_name=cfg['CLOUD_NAME'],
            api_key=cfg['API_KEY'],
            api_secret=cfg['API_SECRET'],
        )
        result = cloudinary.api.usage()
        credits = result.get('credits', {})
        used = credits.get('usage', 0)
        limit = credits.get('limit', 25.0)
        percent = credits.get('used_percent', 0)
        return {
            'used': round(used, 2),
            'limit': round(limit, 2),
            'percent': round(percent, 1),
            'available': round(limit - used, 2),
        }
    except Exception:
        return None
