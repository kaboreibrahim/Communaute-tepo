# dashboard/templatetags/pagination_tags.py
# ============================================================
#  Tags et filtres custom pour la pagination
#  Utilisation dans les templates :
#      {% load pagination_tags %}
#      {% for i in nb_pages|get_range %}
# ============================================================

from django import template

register = template.Library()


@register.filter(name='get_range')
def get_range(value):
    """
    Retourne un range(1, value+1) pour la pagination.
    Utilisation : {% for i in nb_pages|get_range %}
    """
    try:
        return range(1, int(value) + 1)
    except (ValueError, TypeError):
        return range(0)