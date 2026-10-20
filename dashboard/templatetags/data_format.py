from decimal import Decimal
from django import template
from django.utils.formats import number_format

register = template.Library()


@register.filter
def data_value(value):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (Decimal, int, float)):
        return number_format(value, use_l10n=True, force_grouping=True)
    return str(value)
