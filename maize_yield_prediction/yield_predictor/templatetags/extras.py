from django import template

register = template.Library()

@register.filter
def pluck(objects, attr):
    return [getattr(obj, attr).isoformat() if hasattr(getattr(obj, attr), 'isoformat') else getattr(obj, attr) for obj in objects]