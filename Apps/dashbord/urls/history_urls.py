from django.urls import path

from Apps.dashbord.views.history_views import ActionHistoryListView


urlpatterns = [
    path(
        'historique/actions/',
        ActionHistoryListView.as_view(),
        name='action-history',
    ),
]
