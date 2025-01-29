from django import template
from django.db.models import Sum

register = template.Library()

@register.filter
def sum_attr(iterable, attr):
    """
    Sum a specific attribute across a list of dictionaries
    """
    return sum(item.get(attr, 0) for item in iterable)

@register.filter
def get_dict_item(dictionary, key):
    """
    Safely retrieve an item from a dictionary
    """
    return dictionary.get(key, '')
