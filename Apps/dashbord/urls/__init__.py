from django.urls import path, include
from .dahbord_admin_url import urlpatterns as admin_urls
from .village_url import urlpatterns as village_urls
from .person_urls import urlpatterns as person_urls
from .families_urls import urlpatterns as families_urls
from .user_urls import urlpatterns as user_urls
from .event_urls import urlpatterns as event_urls
from .rapports_urls import urlpatterns as rapports_urls
from .history_urls import urlpatterns as history_urls
from .cotisations_urls import urlpatterns as cotisations_urls
from .blog_urls import urlpatterns as blog_urls

app_name = 'dashbord'

urlpatterns = [
    path('', include(admin_urls)),
    path('', include(village_urls)),
    path('', include(person_urls)),
    path('', include(families_urls)),
    path('', include(user_urls)),
    path('', include(event_urls)),
    path('', include(rapports_urls)),
    path('', include(history_urls)),
    path('', include(cotisations_urls)),
    path('', include(blog_urls)),
]
