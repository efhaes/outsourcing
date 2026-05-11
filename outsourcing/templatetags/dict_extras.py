# File: outsourcing/templatetags/dict_extras.py
#
# Struktur folder:
# outsourcing/
# ├── templatetags/
# │   ├── __init__.py   ← file kosong
# │   └── dict_extras.py  ← file ini
#
# Di template, load dengan:
# {% load dict_extras %}
# Lalu pakai: {{ info_hari|get_item:day }}

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Akses dict dengan variable key di template Django.
    Mendukung integer key (untuk info_hari yang keynya integer hari).

    Contoh:
        {{ info_hari|get_item:day }}          → dict info hari ke-day
        {{ info_hari|get_item:day.is_libur }} → JANGAN pakai ini, chain dulu via {% with %}
    """
    if not isinstance(dictionary, dict):
        return None

    # Coba langsung
    if key in dictionary:
        return dictionary[key]

    # Coba konversi ke int (karena days_range berisi int,
    # tapi kadang key dari template bisa masuk sebagai string)
    try:
        return dictionary.get(int(key))
    except (ValueError, TypeError):
        return dictionary.get(key)