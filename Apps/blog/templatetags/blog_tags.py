from django import template
from django.utils import timezone

from Apps.blog.models import Article, Categorie, Tag

register = template.Library()


@register.simple_tag
def articles_recents(limit=5):
    return (
        Article.objects.filter(
            statut=Article.STATUT_PUBLIE,
            date_publication__lte=timezone.now(),
            deleted__isnull=True,
        )
        .select_related("auteur")
        .order_by("-date_publication")[:limit]
    )


@register.simple_tag
def categories_blog():
    return Categorie.objects.all().order_by("ordre", "nom")


@register.inclusion_tag("blog/partials/_tags_cloud.html")
def nuage_tags(limit=20):
    tags = Tag.objects.all()[:limit]
    return {"tags": tags}


@register.filter
def badge_statut(statut):
    mapping = {
        "publie": ("bg-emerald-100 text-emerald-700", "Publié"),
        "brouillon": ("bg-slate-100 text-slate-600", "Brouillon"),
        "planifie": ("bg-sky-100 text-sky-700", "Planifié"),
        "archive": ("bg-amber-100 text-amber-700", "Archivé"),
    }
    return mapping.get(statut, ("bg-gray-100 text-gray-600", statut))
