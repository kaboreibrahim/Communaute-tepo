from datetime import timedelta

from django.utils import timezone
from django.views.generic import TemplateView

from Apps.events.models import Event
from Apps.families.models import Family
from Apps.person.models import Person
from Apps.villages.models import Village
from Apps.website.models import AccueilImage


MONTH_LABELS = {
    1: "JAN",
    2: "FEV",
    3: "MAR",
    4: "AVR",
    5: "MAI",
    6: "JUI",
    7: "JUL",
    8: "AOU",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DEC",
}

EVENT_THEMES = {
    "naissance": {
        "badge_classes": "bg-emerald-500 text-white",
        "surface_classes": "bg-emerald-50",
        "icon_classes": "text-emerald-600",
        "agenda_classes": "bg-emerald-50 border-emerald-500",
        "date_classes": "text-emerald-700",
    },
    "deces": {
        "badge_classes": "bg-slate-800 text-white",
        "surface_classes": "bg-slate-100",
        "icon_classes": "text-slate-500",
        "agenda_classes": "bg-slate-100 border-slate-500",
        "date_classes": "text-slate-700",
    },
    "mariage": {
        "badge_classes": "bg-accent text-white",
        "surface_classes": "bg-accent/5",
        "icon_classes": "text-accent",
        "agenda_classes": "bg-accent/5 border-accent",
        "date_classes": "text-accent",
    },
    "bapteme": {
        "badge_classes": "bg-amber-500 text-white",
        "surface_classes": "bg-amber-50",
        "icon_classes": "text-amber-600",
        "agenda_classes": "bg-amber-50 border-amber-500",
        "date_classes": "text-amber-700",
    },
    "diplome": {
        "badge_classes": "bg-sky-600 text-white",
        "surface_classes": "bg-sky-50",
        "icon_classes": "text-sky-600",
        "agenda_classes": "bg-sky-50 border-sky-500",
        "date_classes": "text-sky-700",
    },
    "deuil": {
        "badge_classes": "bg-slate-900 text-white",
        "surface_classes": "bg-slate-100",
        "icon_classes": "text-slate-600",
        "agenda_classes": "bg-slate-100 border-slate-700",
        "date_classes": "text-slate-800",
    },
    "fete": {
        "badge_classes": "bg-orange-500 text-white",
        "surface_classes": "bg-orange-50",
        "icon_classes": "text-orange-600",
        "agenda_classes": "bg-orange-50 border-orange-500",
        "date_classes": "text-orange-700",
    },
    "communaute": {
        "badge_classes": "bg-primary text-white",
        "surface_classes": "bg-primary/5",
        "icon_classes": "text-primary",
        "agenda_classes": "bg-primary/5 border-primary",
        "date_classes": "text-primary",
    },
    "autre": {
        "badge_classes": "bg-slate-600 text-white",
        "surface_classes": "bg-slate-50",
        "icon_classes": "text-slate-500",
        "agenda_classes": "bg-slate-50 border-slate-400",
        "date_classes": "text-slate-700",
    },
}

DEFAULT_HERO_IMAGES = [
    {
        "title": "Communaute TEPO",
        "subtitle": "Grabo, Olodio et la diaspora avancent ensemble autour d'une meme histoire.",
        "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuD044O23yCEBrLiyRO-xHVp_0herUo0ebtV6mKPpQrtKnMXNvTqW8vX3Xv5L8IGB52g89SQqGdV1yYfNPJOkRFjNEK-Q6Q4QzXlP33nQRZopc5uDh03tasFMy2MVKTa8de0eC-J7Sv3Sj3fHSkt-gbvu02001NHePLPXo2kFuZQTM6qzm762sQxPhhBuDxEJl36sbXbF6gveKblt7oJ7jRKFDpK2M53xyVCgJkrv1xr5Ild_wrEFETCeoxXwPkf9e6L9QVhFIyym88",
        "alt_text": "Vue communautaire de la communaute TEPO",
    },
    {
        "title": "Memoire et transmission",
        "subtitle": "Une terre de culture kroumen, de solidarite et de transmission entre generations.",
        "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuDb7ShSXH2SAZ0zex7Elyq-HfIj2YzdgQUhkPQIHh10iEZ9yetDGvkI-TZMdwkt4ZmaxWmOu5NtloaOlVm9wAvUehibC4Q5Wi7VAi9yB0PjNVDYGf-POBkS7xP9xHAenB6jJqX5x82C0Mtww546xJVC1gEYhtz-fJGt-n5ONVYt0qruirGtPGpVFHe0P4KMxlKt9Geydda_HBDEof_pIMV3Wffib8BGB_jckDafuBv5sLzkvXtnemjGz9igsyu8XxZC7yGNjW8wyDQ",
        "alt_text": "Rassemblement de la communaute TEPO",
    },
]

DEFAULT_ABOUT_IMAGE = {
    "title": "Presence TEPO a Olodio",
    "subtitle": "Tepo Iboke demeure un foyer important de peuplement et d'ancrage communautaire.",
    "image_url": "https://lh3.googleusercontent.com/aida-public/AB6AXuDb7ShSXH2SAZ0zex7Elyq-HfIj2YzdgQUhkPQIHh10iEZ9yetDGvkI-TZMdwkt4ZmaxWmOu5NtloaOlVm9wAvUehibC4Q5Wi7VAi9yB0PjNVDYGf-POBkS7xP9xHAenB6jJqX5x82C0Mtww546xJVC1gEYhtz-fJGt-n5ONVYt0qruirGtPGpVFHe0P4KMxlKt9Geydda_HBDEof_pIMV3Wffib8BGB_jckDafuBv5sLzkvXtnemjGz9igsyu8XxZC7yGNjW8wyDQ",
    "alt_text": "Rassemblement dans un village TEPO",
}


def _get_event_theme(event_type_slug):
    return EVENT_THEMES.get(event_type_slug, EVENT_THEMES["autre"])


def _build_accueil_image_payload(image, default_title):
    return {
        "title": image.titre or default_title,
        "subtitle": image.sous_titre,
        "image_url": image.source_url,
        "alt_text": image.texte_alt or image.titre or default_title,
    }


def _get_event_time_label(event_date, today):
    if event_date == today:
        return "Aujourd'hui"
    if event_date == today - timedelta(days=1):
        return "Hier"
    if event_date == today + timedelta(days=1):
        return "Demain"

    delta = event_date - today
    if 1 < delta.days <= 7:
        return f"Dans {delta.days} jours"

    return event_date.strftime("%d/%m/%Y")


def _get_event_description(event):
    description = (event.resume or event.description or "").strip()
    if description:
        return description

    type_label = event.type.nom if event.type_id else "Evenement"
    if event.personne_id:
        return (
            f"{type_label} concernant {event.personne.nom_complet} "
            f"dans la communaute d'Olodio."
        )

    return f"{type_label} annonce pour la communaute d'Olodio."


def _get_event_full_description(event):
    description = (event.description or event.resume or "").strip()
    if description:
        return description

    type_label = event.type.nom if event.type_id else "Evenement"
    if event.personne_id:
        return (
            f"{type_label} concernant {event.personne.nom_complet} "
            f"dans la communaute d'Olodio."
        )

    return f"{type_label} annonce pour la communaute d'Olodio."


def _get_event_location(event):
    return event.lieu_affichage


def _get_event_subject(event):
    if event.personne_id:
        return event.personne.nom_complet
    return "Communaute d'Olodio"


def _safe_photo_url(event):
    if not event.photo:
        return ""
    try:
        return event.photo.url
    except Exception:
        return ""


def _build_news_event(event, today):
    theme = _get_event_theme(event.type.slug if event.type_id else "autre")
    return {
        "id": str(event.pk),
        "title": event.titre,
        "description": _get_event_description(event),
        "full_description": _get_event_full_description(event),
        "type_label": event.type.nom if event.type_id else "",
        "time_label": _get_event_time_label(event.date_evenement, today),
        "date_label": event.date_evenement.strftime("%d/%m/%Y"),
        "location": _get_event_location(event),
        "subject": _get_event_subject(event),
        "icon": event.icone,
        "photo_url": _safe_photo_url(event),
        **theme,
    }


def _build_agenda_event(event):
    theme = _get_event_theme(event.type.slug if event.type_id else "autre")
    return {
        "id": str(event.pk),
        "title": event.titre,
        "description": _get_event_description(event),
        "type_label": event.type.nom if event.type_id else "",
        "location": _get_event_location(event),
        "icon": event.icone,
        "day": f"{event.date_evenement.day:02d}",
        "month": MONTH_LABELS[event.date_evenement.month],
        **theme,
    }


class AccueilView(TemplateView):
    template_name = "accueil.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        hero_images_qs = AccueilImage.objects.filter(
            section="hero",
            est_active=True,
        ).order_by("ordre", "-date_creation")
        about_image_obj = (
            AccueilImage.objects.filter(
                section="about",
                est_active=True,
            )
            .order_by("ordre", "-date_creation")
            .first()
        )
        published_events = (
            Event.objects.filter(
                est_public=True,
                statut_validation="approved",
            )
            .select_related(
                "personne",
                "personne__famille",
                "personne__famille__village",
                "village",
            )
            .order_by("-date_evenement", "-date_creation")
        )

        agenda_qs = published_events.filter(
            type__slug__in=("communaute", "fete"),
            date_evenement__gte=today,
        ).order_by("date_evenement", "-date_creation")

        if not agenda_qs.exists():
            agenda_qs = published_events.filter(
                type__slug__in=("communaute", "fete")
            ).order_by("-date_evenement", "-date_creation")

        context["title"] = "Accueil"
        context["villages"] = (
            Village.objects.filter(deleted__isnull=True)
            .only(
                "nom",
                "population_estimee",
            )
            .order_by("nom")
        )
        # Calculate real statistics from database
        stats = {
            'villages_count': Village.objects.filter(deleted__isnull=True).count(),
            'families_count': Family.objects.filter(deleted__isnull=True).count(),
            'residents_count': Person.objects.filter(
                deleted__isnull=True,
                est_vivant=True,
                type_residence__in=['village', 'ci']
            ).count(),
            'diaspora_count': Person.objects.filter(
                deleted__isnull=True,
                est_vivant=True,
                type_residence='diaspora'
            ).count(),
        }
        context['stats'] = stats
        context["hero_images"] = [
            _build_accueil_image_payload(image, "Communaute TEPO")
            for image in hero_images_qs
            if image.source_url
        ] or DEFAULT_HERO_IMAGES
        context["hero_featured_image"] = context["hero_images"][0]
        context["about_image"] = (
            _build_accueil_image_payload(about_image_obj, "Communaute TEPO")
            if about_image_obj and about_image_obj.source_url
            else DEFAULT_ABOUT_IMAGE
        )

        context["actualites_events"] = [
            _build_news_event(event, today)
            for event in published_events[:3]
        ]
        context["agenda_events"] = [
            _build_agenda_event(event)
            for event in agenda_qs[:4]
        ]
        return context
