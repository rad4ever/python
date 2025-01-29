from django import template

register = template.Library()

@register.filter
def sum_attr(query_set, attr_name):
    return sum(getattr(item, attr_name, 0) for item in query_set)

@register.filter
def get_dict_item(dictionary, key):
    return dictionary.get(key, '')
