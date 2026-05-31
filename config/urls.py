"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls import handler404, handler403, handler500, handler400
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.i18n import i18n_patterns
from django.urls import include as django_include
from django.views.generic import TemplateView
from django.views.static import serve as serve_media
from Apps.accounts.views import error_views
from config.sitemaps import sitemaps

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    *i18n_patterns(
        path('accounts/', include('Apps.accounts.urls')),
        path('diaspora/', include('Apps.diaspora.urls')),
        path('families/', include('Apps.families.urls')),
        path('villages/', include('Apps.villages.urls')),
        path('dashbord/', include('Apps.dashbord.urls')),
        path('medias/', include('Apps.medias.urls')),
        path('blog/', include('Apps.blog.urls')),
        path('', include('Apps.website.urls')),
    ),
]

# Servir les fichiers media directement (fonctionne même avec DEBUG=False)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_media, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

handler404 = error_views.custom_page_not_found
handler403 = error_views.custom_permission_denied
handler500 = error_views.custom_server_error
handler400 = error_views.custom_bad_request

