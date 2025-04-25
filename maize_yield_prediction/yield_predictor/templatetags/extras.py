from django import template

register = template.Library()

@register.filter
def pluck(list_of_dicts, key):
    return [item.get(key) for item in list_of_dicts if isinstance(item, dict)]

@register.filter
def avg(queryset, field):
    values = [getattr(item, field) for item in queryset]
    return sum(values) / len(values) if values else 0