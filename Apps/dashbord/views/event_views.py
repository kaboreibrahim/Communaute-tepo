from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from Apps.dashbord.security import ensure_registry_management
from Apps.dashbord.views.user_views import _pagination_range, _safe_positive_int
from Apps.events.forms import DashboardEventForm
from Apps.events.models import Event, TypeEvenement
from Apps.villages.models import Village


MONTH_LABELS = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Avr",
    5: "Mai",
    6: "Juin",
    7: "Juil",
    8: "Aout",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

TYPE_THEMES = {
    "naissance": {
        "badge_classes": "bg-cyan-500 text-white",
        "surface_classes": "bg-cyan-50",
        "icon_classes": "text-cyan-500",
    },
    "deces": {
        "badge_classes": "bg-slate-800 text-white",
        "surface_classes": "bg-slate-100",
        "icon_classes": "text-slate-400",
    },
    "mariage": {
        "badge_classes": "bg-pink-500 text-white",
        "surface_classes": "bg-pink-50",
        "icon_classes": "text-pink-500",
    },
    "bapteme": {
        "badge_classes": "bg-amber-500 text-white",
        "surface_classes": "bg-amber-50",
        "icon_classes": "text-amber-500",
    },
    "diplome": {
        "badge_classes": "bg-sky-500 text-white",
        "surface_classes": "bg-sky-50",
        "icon_classes": "text-sky-500",
    },
    "deuil": {
        "badge_classes": "bg-slate-700 text-white",
        "surface_classes": "bg-slate-100",
        "icon_classes": "text-slate-500",
    },
    "fete": {
        "badge_classes": "bg-orange-500 text-white",
        "surface_classes": "bg-orange-50",
        "icon_classes": "text-orange-500",
    },
    "communaute": {
        "badge_classes": "bg-primary text-white",
        "surface_classes": "bg-primary/5",
        "icon_classes": "text-primary",
    },
    "autre": {
        "badge_classes": "bg-slate-600 text-white",
        "surface_classes": "bg-slate-50",
        "icon_classes": "text-slate-500",
    },
}

STATUS_META = {
    "pending": {
        "label": "En attente",
        "classes": "bg-amber-100 text-amber-700",
    },
    "approved": {
        "label": "Publie",
        "classes": "bg-emerald-100 text-emerald-700",
    },
    "rejected": {
        "label": "Refuse",
        "classes": "bg-rose-100 text-rose-700",
    },
}


def _safe_photo_url(event) -> str:
    if not event.photo:
        return ""
    try:
        return event.photo.url
    except Exception:
        return ""


def _time_label(event_date):
    today = timezone.localdate()
    if event_date == today:
        return "Aujourd'hui"
    if event_date == today - timedelta(days=1):
        return "Hier"
    if event_date == today + timedelta(days=1):
        return "Demain"
    if event_date > today:
        delta = (event_date - today).days
        if delta <= 7:
            return f"Dans {delta} jours"
    return event_date.strftime("%d %b %Y")


def _event_theme(event_type: str) -> dict:
    return TYPE_THEMES.get(event_type, TYPE_THEMES["autre"])


def _event_status_meta(status_value: str) -> dict:
    return STATUS_META.get(
        status_value,
        {"label": status_value, "classes": "bg-slate-100 text-slate-600"},
    )


def _public_submission_q() -> Q:
    return (
        Q(nom_contact__gt="")
        | Q(telephone_contact__gt="")
        | Q(email_contact__gt="")
    )


def _event_location(event) -> str:
    return event.lieu_affichage


def _event_village_name(event) -> str:
    if event.village_id:
        return event.village.nom
    if event.personne_id and event.personne.famille_id:
        return event.personne.famille.village.nom
    return "Tous les villages"


def _build_event_card(event) -> dict:
    return {
        "id": event.id,
        "title": event.titre,
        "summary": event.resume_affichage,
        "type_label": event.type.nom if event.type_id else "",
        "time_label": _time_label(event.date_evenement),
        "location": _event_location(event),
        "village_name": _event_village_name(event),
        "image_url": _safe_photo_url(event),
        "status": _event_status_meta(event.statut_validation),
        "status_value": event.statut_validation,
        "is_public": event.est_public,
        "detail_url": reverse("dashbord:event-update", args=[event.id]),
        "is_public_submission": event.est_soumission_publique,
        "contact_name": event.nom_contact,
        "created_at": event.date_creation,
        "icon": event.icone,
        **_event_theme(event.type.slug if event.type_id else "autre"),
    }


def _archive_label(value):
    return f"{MONTH_LABELS.get(value.month, value.strftime('%b'))} {value.year}"


def _bind_event_form(request, instance=None):
    post_data = request.POST.copy()
    if post_data.get("visibility_scope") == "public":
        post_data["est_public"] = "on"
    else:
        post_data.pop("est_public", None)
    return DashboardEventForm(post_data, request.FILES, instance=instance)


def _build_event_form_context(form, event=None):
    review_mode = bool(
        event
        and event.est_soumission_publique
        and event.statut_validation == "pending"
    )

    if review_mode:
        heading = "Verifier une demande venue du site public"
        intro = (
            "Completer ou corriger l'annonce avant validation. "
            "Cette interface remplace la moderation via Django admin."
        )
        browser_title = "Verifier un evenement - Olodio"
        topbar_title = "Verification evenement"
        breadcrumb_current = "Verification"
        primary_action_label = "Valider et publier"
        secondary_action_label = "Conserver en attente"
    elif event:
        heading = "Modifier une annonce"
        intro = (
            "Ajustez le contenu, la visibilite ou les informations de "
            "publication directement depuis le dashboard."
        )
        browser_title = "Modifier un evenement - Olodio"
        topbar_title = "Edition evenement"
        breadcrumb_current = "Modification"
        primary_action_label = "Enregistrer les modifications"
        secondary_action_label = "Mettre en attente"
    else:
        heading = "Creer une nouvelle annonce"
        intro = (
            "Partagez une actualite, un evenement ou une communication "
            "officielle avec les villages de la communaute d'Olodio."
        )
        browser_title = "Publier un evenement - Olodio"
        topbar_title = "Nouvel evenement"
        breadcrumb_current = "Creation"
        primary_action_label = "Publier l'annonce"
        secondary_action_label = "Enregistrer comme brouillon"

    return {
        "form": form,
        "event_obj": event,
        "review_mode": review_mode,
        "show_submission_panel": bool(event and event.est_soumission_publique),
        "status_meta": _event_status_meta(event.statut_validation) if event else None,
        "browser_title": browser_title,
        "topbar_page_title": topbar_title,
        "breadcrumb_current": breadcrumb_current,
        "heading": heading,
        "intro": intro,
        "primary_action_label": primary_action_label,
        "secondary_action_label": secondary_action_label,
        "show_reject_button": bool(event and event.statut_validation != "approved"),
        "cancel_url": reverse("dashbord:event-list"),
    }


@method_decorator(login_required, name="dispatch")
class EventManagementMixin(View):
    def dispatch(self, request, *args, **kwargs):
        ensure_registry_management(request.user)
        return super().dispatch(request, *args, **kwargs)


class EventListView(EventManagementMixin):
    template_name = "events/liste_evenements.html"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        event_type = request.GET.get("type", "").strip()
        village_id = request.GET.get("village", "").strip()
        archive = request.GET.get("archive", "").strip()
        page = _safe_positive_int(request.GET.get("page", 1), 1)
        par_page = _safe_positive_int(request.GET.get("par_page", 4), 4)

        base_qs = Event.objects.select_related(
            "personne",
            "personne__famille",
            "personne__famille__village",
            "village",
            "valide_par",
        )
        filtered_qs = base_qs.order_by("-date_evenement", "-date_creation")

        if q:
            filtered_qs = filtered_qs.filter(
                Q(titre__icontains=q)
                | Q(resume__icontains=q)
                | Q(description__icontains=q)
                | Q(lieu__icontains=q)
                | Q(village__nom__icontains=q)
                | Q(personne__nom__icontains=q)
                | Q(personne__prenom__icontains=q)
                | Q(personne__famille__village__nom__icontains=q)
                | Q(nom_contact__icontains=q)
                | Q(telephone_contact__icontains=q)
                | Q(email_contact__icontains=q)
            )

        valid_types = set(TypeEvenement.objects.values_list("slug", flat=True))
        if event_type in valid_types:
            filtered_qs = filtered_qs.filter(type__slug=event_type)

        if village_id:
            filtered_qs = filtered_qs.filter(
                Q(village_id=village_id)
                | Q(village__isnull=True, personne__famille__village_id=village_id)
            )

        if archive:
            try:
                archive_year, archive_month = archive.split("-")
                filtered_qs = filtered_qs.filter(
                    date_evenement__year=int(archive_year),
                    date_evenement__month=int(archive_month),
                )
            except (TypeError, ValueError):
                archive = ""

        featured = filtered_qs.first()
        feed_qs = filtered_qs.exclude(pk=featured.pk) if featured else filtered_qs
        filtered_total = filtered_qs.count()

        paginator = Paginator(feed_qs, par_page)
        page_obj = paginator.get_page(page)
        current_page = page_obj.number
        total = paginator.count
        display_start = ((current_page - 1) * par_page) + 1 if total else 0
        display_end = min(current_page * par_page, total) if total else 0

        type_counts = {
            item["type__slug"]: item["total"]
            for item in base_qs.values("type__slug").annotate(total=Count("id"))
        }
        all_types = TypeEvenement.objects.all()
        categories = [
            {
                "value": "",
                "label": "Toutes",
                "count": base_qs.count(),
                "active": event_type == "",
            }
        ]
        for t in all_types:
            categories.append(
                {
                    "value": t.slug,
                    "label": t.nom,
                    "count": type_counts.get(t.slug, 0),
                    "active": event_type == t.slug,
                }
            )

        archive_rows = []
        for item in (
            base_qs.annotate(month=TruncMonth("date_evenement"))
            .values("month")
            .annotate(total=Count("id"))
            .order_by("-month")[:6]
        ):
            month_value = item["month"]
            if not month_value:
                continue
            archive_value = f"{month_value.year}-{month_value.month:02d}"
            archive_rows.append(
                {
                    "value": archive_value,
                    "label": _archive_label(month_value),
                    "count": item["total"],
                    "active": archive == archive_value,
                }
            )

        public_submission_filter = _public_submission_q()
        stats = {
            "total": base_qs.count(),
            "published": base_qs.filter(statut_validation="approved").count(),
            "pending": base_qs.filter(statut_validation="pending").count(),
            "public": base_qs.filter(
                est_public=True,
                statut_validation="approved",
            ).count(),
            "pending_public_submissions": base_qs.filter(
                public_submission_filter,
                statut_validation="pending",
            ).count(),
        }

        return render(
            request,
            self.template_name,
            {
                "q": q,
                "event_type": event_type,
                "village_id": village_id,
                "archive": archive,
                "villages": Village.objects.filter(deleted__isnull=True).order_by("nom"),
                "featured_event": _build_event_card(featured) if featured else None,
                "event_cards": [_build_event_card(event) for event in page_obj.object_list],
                "categories": categories,
                "archive_rows": archive_rows,
                "stats": stats,
                "page": current_page,
                "nb_pages": paginator.num_pages,
                "page_range": _pagination_range(current_page, paginator.num_pages),
                "total": total,
                "filtered_total": filtered_total,
                "par_page": par_page,
                "display_start": display_start,
                "display_end": display_end,
            },
        )


class EventCreateView(EventManagementMixin):
    template_name = "events/formulaire_evenement.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            _build_event_form_context(DashboardEventForm()),
        )

    def post(self, request):
        submit_action = request.POST.get("submit_action", "publish")
        publish = submit_action != "draft"
        form = _bind_event_form(request)

        if form.is_valid():
            event = form.save(
                validator=request.user if publish else None,
                publish=publish,
            )
            if publish:
                messages.success(
                    request,
                    f"L'evenement '{event.titre}' a ete publie avec succes.",
                )
            else:
                messages.success(
                    request,
                    f"L'evenement '{event.titre}' a ete enregistre en attente.",
                )
            return redirect("dashbord:event-list")

        messages.error(
            request,
            "Impossible d'enregistrer cet evenement. Verifiez le formulaire.",
        )
        return render(
            request,
            self.template_name,
            _build_event_form_context(form),
        )


class EventUpdateView(EventManagementMixin):
    template_name = "events/formulaire_evenement.html"

    def _get_event(self, event_id):
        return get_object_or_404(
            Event.objects.select_related(
                "personne",
                "personne__famille",
                "personne__famille__village",
                "village",
                "valide_par",
            ),
            id=event_id,
        )

    def get(self, request, event_id):
        event = self._get_event(event_id)
        return render(
            request,
            self.template_name,
            _build_event_form_context(
                DashboardEventForm(instance=event),
                event=event,
            ),
        )

    def post(self, request, event_id):
        event = self._get_event(event_id)
        submit_action = request.POST.get("submit_action", "publish")

        if submit_action == "reject":
            event.statut_validation = "rejected"
            event.est_public = False
            event.valide_par = request.user
            event.date_validation = timezone.now()
            event.save(
                update_fields=[
                    "statut_validation",
                    "est_public",
                    "valide_par",
                    "date_validation",
                ]
            )
            messages.warning(
                request,
                f"La demande '{event.titre}' a ete refusee.",
            )
            return redirect("dashbord:event-list")

        form = _bind_event_form(request, instance=event)
        if form.is_valid():
            publish = submit_action != "draft"
            previous_status = event.statut_validation
            was_public_submission = event.est_soumission_publique

            event = form.save(
                validator=request.user if publish else None,
                publish=publish,
            )
            if publish:
                if was_public_submission and previous_status != "approved":
                    messages.success(
                        request,
                        f"La demande '{event.titre}' a ete validee et publiee.",
                    )
                else:
                    messages.success(
                        request,
                        f"L'annonce '{event.titre}' a ete mise a jour.",
                    )
            else:
                messages.success(
                    request,
                    f"L'annonce '{event.titre}' reste en attente de validation.",
                )
            return redirect("dashbord:event-list")

        messages.error(
            request,
            "Impossible d'enregistrer cet evenement. Verifiez le formulaire.",
        )
        return render(
            request,
            self.template_name,
            _build_event_form_context(form, event=event),
        )


# ---------------------------------------------------------------------------
# TypeEvenement — CRUD
# ---------------------------------------------------------------------------

def _type_values(type_obj=None, post=None):
    """Retourne un dict de valeurs toujours complet pour le template formulaire."""
    if post is not None:
        return {
            "nom": post.get("nom", ""),
            "slug": post.get("slug", ""),
            "icone": post.get("icone", "event_note") or "event_note",
            "couleur_fond": post.get("couleur_fond", "#F8FAFC"),
            "couleur_texte": post.get("couleur_texte", "#334155"),
            "ordre": post.get("ordre", "0"),
            "est_communautaire": "est_communautaire" in post,
        }
    if type_obj is not None:
        return {
            "nom": type_obj.nom,
            "slug": type_obj.slug,
            "icone": type_obj.icone,
            "couleur_fond": type_obj.couleur_fond,
            "couleur_texte": type_obj.couleur_texte,
            "ordre": str(type_obj.ordre),
            "est_communautaire": type_obj.est_communautaire,
        }
    return {
        "nom": "",
        "slug": "",
        "icone": "event_note",
        "couleur_fond": "#F8FAFC",
        "couleur_texte": "#334155",
        "ordre": "0",
        "est_communautaire": False,
    }


class TypeEvenementListView(EventManagementMixin):
    template_name = "events/liste_types_evenement.html"

    def get(self, request):
        types = (
            TypeEvenement.objects
            .annotate(nb_evenements=Count("evenements"))
            .order_by("ordre", "nom")
        )
        return render(request, self.template_name, {"types": types})


class TypeEvenementCreateView(EventManagementMixin):
    template_name = "events/formulaire_type_evenement.html"

    def get(self, request):
        return render(request, self.template_name, {
            "action": "create",
            "values": _type_values(),
        })

    def post(self, request):
        values = _type_values(post=request.POST)

        if not values["nom"] or not values["slug"]:
            messages.error(request, "Le nom et le slug sont obligatoires.")
            return render(request, self.template_name, {"action": "create", "values": values})

        if TypeEvenement.objects.filter(slug=values["slug"]).exists():
            messages.error(request, f"Un type avec le slug « {values['slug']} » existe deja.")
            return render(request, self.template_name, {"action": "create", "values": values})

        t = TypeEvenement.objects.create(
            slug=values["slug"], nom=values["nom"], icone=values["icone"],
            couleur_fond=values["couleur_fond"], couleur_texte=values["couleur_texte"],
            est_communautaire=values["est_communautaire"],
            ordre=_safe_positive_int(values["ordre"], default=0),
        )
        messages.success(request, f"Type « {t.nom} » cree avec succes.")
        return redirect(reverse("dashbord:type-evenement-list"))


class TypeEvenementUpdateView(EventManagementMixin):
    template_name = "events/formulaire_type_evenement.html"

    def _get_type(self, type_id):
        return get_object_or_404(TypeEvenement, pk=type_id)

    def get(self, request, type_id):
        t = self._get_type(type_id)
        return render(request, self.template_name, {
            "action": "update",
            "type_obj": t,
            "values": _type_values(type_obj=t),
        })

    def post(self, request, type_id):
        t = self._get_type(type_id)
        values = _type_values(post=request.POST)

        if not values["nom"] or not values["slug"]:
            messages.error(request, "Le nom et le slug sont obligatoires.")
            return render(request, self.template_name, {"action": "update", "type_obj": t, "values": values})

        if TypeEvenement.objects.filter(slug=values["slug"]).exclude(pk=type_id).exists():
            messages.error(request, f"Un type avec le slug « {values['slug']} » existe deja.")
            return render(request, self.template_name, {"action": "update", "type_obj": t, "values": values})

        t.slug = values["slug"]
        t.nom = values["nom"]
        t.icone = values["icone"]
        t.couleur_fond = values["couleur_fond"]
        t.couleur_texte = values["couleur_texte"]
        t.est_communautaire = values["est_communautaire"]
        t.ordre = _safe_positive_int(values["ordre"], default=0)
        t.save()
        messages.success(request, f"Type « {t.nom} » mis a jour.")
        return redirect(reverse("dashbord:type-evenement-list"))


class TypeEvenementDetailView(EventManagementMixin):
    template_name = "events/detail_type_evenement.html"

    def get(self, request, type_id):
        t = get_object_or_404(
            TypeEvenement.objects.annotate(nb_evenements=Count("evenements")),
            pk=type_id,
        )
        evenements = (
            t.evenements
            .select_related("personne", "village", "valide_par")
            .order_by("-date_evenement", "-date_creation")[:20]
        )
        stats = {
            "total": t.nb_evenements,
            "publies": t.evenements.filter(statut_validation="approved", est_public=True).count(),
            "en_attente": t.evenements.filter(statut_validation="pending").count(),
            "refuses": t.evenements.filter(statut_validation="rejected").count(),
        }
        return render(request, self.template_name, {
            "type_obj": t,
            "evenements": evenements,
            "stats": stats,
        })


class TypeEvenementDeleteView(EventManagementMixin):
    def post(self, request, type_id):
        t = get_object_or_404(TypeEvenement, pk=type_id)
        nb = t.evenements.count()
        if nb:
            messages.error(request, f"Impossible : {nb} evenement(s) utilisent ce type.")
        else:
            nom = t.nom
            t.delete()
            messages.success(request, f"Type « {nom} » supprime.")
        return redirect(reverse("dashbord:type-evenement-list"))
