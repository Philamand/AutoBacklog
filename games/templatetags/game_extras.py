from django import template

register = template.Library()


@register.filter(name="hours")
def hours(value):
    return str(int(value / 60)) + "h" + str(value % 60) + "m"
