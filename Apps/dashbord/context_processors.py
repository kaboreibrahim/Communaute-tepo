from django.urls import reverse

from Apps.cotisations.models import Paiement
from Apps.dashbord.security import filter_person_queryset_for_user
from Apps.events.models import Event
from Apps.person.models import Person
from Apps.villages.models import Village
from Apps.website.models import PublicPersonSubmission


def admin_navigation_context(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    villages_count = Village.objects.filter(deleted__isnull=True).count()
    pending_public_submissions_count = 0
    pending_events_count = 0
    pending_payments_count = 0
    notification_items = []

    if getattr(user, "est_agent_saisie", False):
        pending_public_submissions_count = PublicPersonSubmission.objects.filter(
            statut_validation="pending"
        ).count()
        if pending_public_submissions_count:
            notification_items.append(
                {
                    "title": "Pre-inscriptions",
                    "count": pending_public_submissions_count,
                    "icon": "fact_check",
                    "icon_classes": "bg-amber-100 text-amber-700",
                    "description": "Dossiers publics en attente de verification",
                    "url": reverse("dashbord:public-person-submission-list"),
                }
            )

    if getattr(user, "est_agent_saisie", False):
        pending_events_count = Event.objects.filter(
            statut_validation="pending"
        ).count()
        if pending_events_count:
            notification_items.append(
                {
                    "title": "Evenements",
                    "count": pending_events_count,
                    "icon": "newspaper",
                    "icon_classes": "bg-sky-100 text-sky-700",
                    "description": "Annonces ou evenements en attente de validation",
                    "url": reverse("dashbord:event-list"),
                }
            )

    if getattr(user, "est_agent_saisie", False):
        visible_persons = filter_person_queryset_for_user(
            Person.objects.filter(deleted__isnull=True),
            user,
        )
        pending_payments_count = Paiement.objects.filter(
            statut_validation="pending",
            personne__in=visible_persons,
        ).count()
        if pending_payments_count:
            notification_items.append(
                {
                    "title": "Paiements",
                    "count": pending_payments_count,
                    "icon": "payments",
                    "icon_classes": "bg-emerald-100 text-emerald-700",
                    "description": "Paiements en attente de validation",
                    "url": reverse("dashbord:cotisation-list"),
                }
            )

    notif_count = sum(item["count"] for item in notification_items)

    return {
        "villages_count": villages_count,
        "pending_public_submissions_count": pending_public_submissions_count,
        "pending_events_count": pending_events_count,
        "pending_payments_count": pending_payments_count,
        "notification_items": notification_items,
        "notif_count": notif_count,
    }
