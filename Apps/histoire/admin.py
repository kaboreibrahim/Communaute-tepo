from django.contrib import admin

from Apps.histoire.models import ActionHistory


@admin.register(ActionHistory)
class ActionHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'date_action',
        'user_name',
        'user_role',
        'fonction',
        'action',
        'adresse_ip',
        'pays',
        'ville',
        'statut_code',
    )
    list_filter = ('action', 'fonction', 'user_role', 'pays', 'ville')
    search_fields = (
        'user_name',
        'fonction',
        'action',
        'adresse_ip',
        'pays',
        'ville',
        'chemin',
    )
    ordering = ('-date_action',)
