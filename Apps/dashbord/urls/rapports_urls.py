from django.urls import path
from ..views.rapports_views import (
    export_cotisations_annuelles_excel,
    export_cotisations_personnes_excel,
    export_cotisations_villages_excel,
    export_demographie_excel,
    export_familles_excel,
    export_personnes_excel,
    export_relances_excel,
    export_villages_excel,
    rapports_dashboard,
)

app_name = 'dashbord'

urlpatterns = [
    path('rapports/', rapports_dashboard, name='rapports'),
    path('rapports/personnes/', export_personnes_excel, name='export_personnes'),
    path('rapports/familles/', export_familles_excel, name='export_familles'),
    path('rapports/villages/', export_villages_excel, name='export_villages'),
    path('rapports/demographie/', export_demographie_excel, name='export_demographie'),
    path(
        'rapports/cotisations/personnes/',
        export_cotisations_personnes_excel,
        name='export_cotisations_personnes',
    ),
    path(
        'rapports/cotisations/villages/',
        export_cotisations_villages_excel,
        name='export_cotisations_villages',
    ),
    path(
        'rapports/cotisations/annuel/',
        export_cotisations_annuelles_excel,
        name='export_cotisations_annuelles',
    ),
    path(
        'rapports/cotisations/relances/',
        export_relances_excel,
        name='export_relances',
    ),
]
