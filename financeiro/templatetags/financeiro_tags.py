from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def fmt_brl(value):
    """Formata Decimal/float para moeda brasileira: 1.234,56"""
    if not value:
        return ''
    try:
        return '{:,.2f}'.format(float(value)).replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return ''


@register.filter
def index(lst, i):
    """Acessa lista por índice no template."""
    try:
        return lst[i]
    except (IndexError, TypeError):
        return ''
