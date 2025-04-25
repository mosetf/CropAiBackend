from django import template

register = template.Library()

@register.filter
def pluck(objects, attr):
    return [getattr(obj, attr).isoformat() if hasattr(getattr(obj, attr), 'isoformat') else getattr(obj, attr) for obj in objects]

@register.filter
def avg(queryset, field):
    values = [getattr(item, field) for item in queryset]
    return sum(values) / len(values) if values else 0