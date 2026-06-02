from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone

from Apps.blog.models import Article
from Apps.events.models import Event


class ArticleSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8
    protocol = "https"
    i18n = True

    def items(self):
        return Article.objects.filter(
            statut=Article.STATUT_PUBLIE,
            date_publication__lte=timezone.now(),
            deleted__isnull=True,
        ).order_by("-date_publication")

    def lastmod(self, obj):
        return obj.date_maj

    def location(self, obj):
        return reverse("blog:article-detail", kwargs={"slug": obj.slug})


class EventSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    protocol = "https"
    i18n = True

    def items(self):
        return Event.objects.filter(
            est_public=True,
            statut_validation="approved",
        ).order_by("-date_evenement")

    def lastmod(self, obj):
        return obj.date_creation

    def location(self, obj):
        return reverse("website:evenement-detail", kwargs={"pk": obj.pk})


class StaticSitemap(Sitemap):
    changefreq = "weekly"
    priority = 1.0
    protocol = "https"
    i18n = True

    _pages = [
        ("website:accueil", {}),
        ("website:evenement-list", {}),
        ("website:galerie", {}),
        ("blog:article-list", {}),
    ]

    def items(self):
        return self._pages

    def location(self, item):
        name, kwargs = item
        return reverse(name, kwargs=kwargs)


sitemaps = {
    "static": StaticSitemap,
    "articles": ArticleSitemap,
    "evenements": EventSitemap,
}
