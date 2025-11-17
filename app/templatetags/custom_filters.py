from django import template
#Создание понтяного отступа доля комментариев на которые ответили
register = template.Library()

@register.filter
def mul(value, args):
    try:
        return value * args
    except (TypeError, ValueError):
        return ''