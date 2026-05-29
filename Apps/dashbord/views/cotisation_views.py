from collections import Counter
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from Apps.cotisations.forms import (
    ComptePaiementForm,
    CotisationForm,
    CotisationPersonneForm,
    PaiementForm,
)
from Apps.cotisations.models import (
    PERSON_TRACKING_STATUS_LABELS,
    ComptePaiement,
    Cotisation,
    CotisationPersonne,
    Paiement,
    compute_remaining_amount,
    resolve_person_tracking_status,
)
from Apps.dashbord.security import ensure_registry_management, filter_person_queryset_for_user
from Apps.dashbord.views.user_views import _pagination_range, _safe_positive_int
from Apps.families.models import Family
from Apps.person.models import Person
from Apps.villages.models import Village


PAYMENT_STATUS_META = {
    "approved": {
        "label": "Valide",
        "classes": "bg-emerald-100 text-emerald-700",
    },
    "pending": {
        "label": "En attente",
        "classes": "bg-amber-100 text-amber-700",
    },
    "rejected": {
        "label": "Refuse",
        "classes": "bg-rose-100 text-rose-700",
    },
}

PAYMENT_MODE_META = {
    "wave": {"label": "Wave", "classes": "bg-sky-100 text-sky-700"},
    "orange_money": {"label": "Orange Money", "classes": "bg-orange-100 text-orange-700"},
    "moov": {"label": "Moov", "classes": "bg-teal-100 text-teal-700"},
    "mtn": {"label": "MTN", "classes": "bg-yellow-100 text-yellow-700"},
    "virement": {"label": "Virement", "classes": "bg-indigo-100 text-indigo-700"},
    "espece": {"label": "Espece", "classes": "bg-slate-100 text-slate-700"},
}

COTISATION_STATUS_META = {
    "ouverte": {
        "label": "Ouverte",
        "classes": "bg-emerald-100 text-emerald-700",
    },
    "fermee": {
        "label": "Fermee",
        "classes": "bg-slate-100 text-slate-700",
    },
}

TRACKING_STATUS_META = {
    "solde": {
        "label": PERSON_TRACKING_STATUS_LABELS["solde"],
        "classes": "bg-emerald-100 text-emerald-700",
    },
    "partiel": {
        "label": PERSON_TRACKING_STATUS_LABELS["partiel"],
        "classes": "bg-orange-100 text-orange-700",
    },
    "versement": {
        "label": PERSON_TRACKING_STATUS_LABELS["versement"],
        "classes": "bg-sky-100 text-sky-700",
    },
    "pending": {
        "label": PERSON_TRACKING_STATUS_LABELS["pending"],
        "classes": "bg-amber-100 text-amber-700",
    },
    "retry": {
        "label": PERSON_TRACKING_STATUS_LABELS["retry"],
        "classes": "bg-rose-100 text-rose-700",
    },
    "unpaid": {
        "label": PERSON_TRACKING_STATUS_LABELS["unpaid"],
        "classes": "bg-slate-100 text-slate-700",
    },
}


def payment_status_meta(value: str) -> dict:
    return PAYMENT_STATUS_META.get(
        value,
        {"label": value, "classes": "bg-slate-100 text-slate-600"},
    )


def payment_mode_meta(value: str) -> dict:
    return PAYMENT_MODE_META.get(
        value,
        {"label": value, "classes": "bg-slate-100 text-slate-600"},
    )


def cotisation_status_meta(value: str) -> dict:
    return COTISATION_STATUS_META.get(
        value,
        {"label": value, "classes": "bg-slate-100 text-slate-600"},
    )


def tracking_status_meta(value: str) -> dict:
    return TRACKING_STATUS_META.get(
        value,
        {"label": PERSON_TRACKING_STATUS_LABELS.get(value, value), "classes": "bg-slate-100 text-slate-600"},
    )


def pending_payment_count() -> int:
    return Paiement.objects.filter(statut_validation="pending").count()


def _safe_media_url(file_field) -> str:
    if not file_field:
        return ""
    try:
        return file_field.url
    except Exception:
        return ""


def _cotisation_base_qs():
    return Cotisation.objects.select_related(
        "village",
        "famille",
        "famille__village",
    ).annotate(
        total_collecte_value=Coalesce(
            Sum(
                "paiements__montant",
                filter=Q(paiements__statut_validation="approved"),
            ),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
        nombre_payeurs_value=Count(
            "paiements__personne_id",
            filter=Q(paiements__statut_validation="approved"),
            distinct=True,
        ),
        paiements_pending_value=Count(
            "paiements__id",
            filter=Q(paiements__statut_validation="pending"),
            distinct=True,
        ),
    )


def _payment_base_qs():
    return Paiement.objects.select_related(
        "personne",
        "personne__famille",
        "personne__famille__village",
        "cotisation",
        "cotisation__village",
        "cotisation__famille",
        "cotisation__famille__village",
        "compte_paiement",
        "enregistre_par",
        "valide_par",
    )


def _visible_person_qs(user):
    return filter_person_queryset_for_user(
        Person.objects.filter(deleted__isnull=True, est_vivant=True).select_related(
            "famille",
            "famille__village",
        ),
        user,
    )


def _visible_cotisations_for_user(queryset, user):
    visible_persons = _visible_person_qs(user)
    family_ids = visible_persons.values_list("famille_id", flat=True)
    village_ids = visible_persons.values_list("famille__village_id", flat=True)
    return queryset.filter(
        Q(est_generale=True)
        | Q(famille_id__in=family_ids)
        | Q(famille__isnull=True, village_id__in=village_ids)
    ).distinct()


def _visible_payments_for_user(queryset, user):
    return queryset.filter(personne__in=_visible_person_qs(user))


def _payment_breakdown(payment_list):
    approved = [item for item in payment_list if item.statut_validation == "approved"]
    pending = [item for item in payment_list if item.statut_validation == "pending"]
    rejected = [item for item in payment_list if item.statut_validation == "rejected"]
    approved_total = sum((item.montant for item in approved), Decimal("0.00"))
    return approved, pending, rejected, approved_total


def _build_cotisation_person_rows(cotisation: Cotisation, user):
    visible_persons = list(
        _visible_person_qs(user)
        .filter(id__in=cotisation.personnes_cibles.values("id"))
        .order_by("prenom", "nom")
    )
    trackings = {
        str(tracking.personne_id): tracking
        for tracking in CotisationPersonne.objects.filter(
            cotisation=cotisation,
            personne__in=visible_persons,
        ).select_related(
            "personne",
            "personne__famille",
            "personne__famille__village",
        )
    }
    payments = list(
        _visible_payments_for_user(
            _payment_base_qs().filter(
                cotisation=cotisation,
                personne__in=visible_persons,
            ),
            user,
        ).order_by("-date_paiement", "-date_creation")
    )

    grouped = {}
    for payment in payments:
        grouped.setdefault(str(payment.personne_id), []).append(payment)

    rows = []
    total_expected = Decimal("0.00")
    total_remaining = Decimal("0.00")
    defined_amount_count = 0

    for person in visible_persons:
        tracking = trackings.get(str(person.id))
        payment_list = grouped.get(str(person.id), [])
        approved, pending, rejected, approved_total = _payment_breakdown(payment_list)
        expected_amount = (
            tracking.montant_attendu
            if tracking and tracking.montant_attendu is not None
            else None
        )
        remaining_amount = compute_remaining_amount(expected_amount, approved_total)
        status_key = resolve_person_tracking_status(
            expected_amount,
            approved_total,
            pending_count=len(pending),
            rejected_count=len(rejected),
        )

        if expected_amount is not None:
            defined_amount_count += 1
            total_expected += expected_amount
            total_remaining += remaining_amount or Decimal("0.00")

        rows.append(
            {
                "person": person,
                "tracking": tracking,
                "payments": payment_list,
                "payment_count": len(payment_list),
                "approved_count": len(approved),
                "pending_count": len(pending),
                "rejected_count": len(rejected),
                "approved_total": approved_total,
                "expected_amount": expected_amount,
                "remaining_amount": remaining_amount,
                "status_key": status_key,
                "status_meta": tracking_status_meta(status_key),
                "last_payment": payment_list[0] if payment_list else None,
            }
        )

    return {
        "rows": rows,
        "visible_persons": visible_persons,
        "total_expected": total_expected,
        "total_remaining": total_remaining,
        "defined_amount_count": defined_amount_count,
    }


def _build_person_cotisation_rows(person: Person, limit: int = 8):
    cotisations = list(
        Cotisation.objects.filter(
            Q(est_generale=True)
            | Q(famille_id=person.famille_id)
            | Q(famille__isnull=True, village_id=person.famille.village_id)
        )
        .select_related("village", "famille", "famille__village")
        .order_by("-annee", "-mois", "-date_creation")[:limit]
    )
    if not cotisations:
        return []

    payments = list(
        _payment_base_qs()
        .filter(personne=person, cotisation__in=cotisations)
        .order_by("-date_paiement", "-date_creation")
    )
    trackings = {
        str(tracking.cotisation_id): tracking
        for tracking in CotisationPersonne.objects.filter(
            personne=person,
            cotisation__in=cotisations,
        ).select_related("cotisation")
    }

    grouped = {}
    for payment in payments:
        grouped.setdefault(str(payment.cotisation_id), []).append(payment)

    rows = []
    for cotisation in cotisations:
        tracking = trackings.get(str(cotisation.id))
        payment_list = grouped.get(str(cotisation.id), [])
        approved, pending, rejected, total_paid = _payment_breakdown(payment_list)
        expected_amount = (
            tracking.montant_attendu
            if tracking and tracking.montant_attendu is not None
            else None
        )
        remaining_amount = compute_remaining_amount(expected_amount, total_paid)
        status_key = resolve_person_tracking_status(
            expected_amount,
            total_paid,
            pending_count=len(pending),
            rejected_count=len(rejected),
        )
        state = tracking_status_meta(status_key)

        rows.append(
            {
                "cotisation": cotisation,
                "state": state,
                "status_key": status_key,
                "payment_count": len(payment_list),
                "total_paid": total_paid,
                "expected_amount": expected_amount,
                "remaining_amount": remaining_amount,
                "tracking": tracking,
                "last_payment": payment_list[0] if payment_list else None,
                "payments": payment_list[:3],
            }
        )
    return rows


def get_person_cotisation_summary(person_id: str, limit: int = 8):
    try:
        person = Person.objects.select_related("famille", "famille__village").get(
            id=person_id,
            deleted__isnull=True,
        )
    except Person.DoesNotExist:
        return {
            "rows": [],
            "total_paid": Decimal("0.00"),
            "pending_count": 0,
            "unpaid_count": 0,
        }

    rows = _build_person_cotisation_rows(person, limit=limit)
    total_paid = sum((row["total_paid"] for row in rows), Decimal("0.00"))
    pending_count = sum(1 for row in rows if row["status_key"] == "pending")
    unpaid_count = sum(
        1 for row in rows if row["status_key"] in {"unpaid", "partiel", "retry"}
    )
    return {
        "rows": rows,
        "total_paid": total_paid,
        "pending_count": pending_count,
        "unpaid_count": unpaid_count,
    }


@method_decorator(login_required, name="dispatch")
class CotisationManagementMixin(View):
    def dispatch(self, request, *args, **kwargs):
        ensure_registry_management(request.user)
        return super().dispatch(request, *args, **kwargs)


class CotisationListView(CotisationManagementMixin):
    template_name = "cotisations/liste.html"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        statut = request.GET.get("statut", "").strip()
        village_id = request.GET.get("village", "").strip()
        famille_id = request.GET.get("famille", "").strip()
        annee = request.GET.get("annee", "").strip()
        page = _safe_positive_int(request.GET.get("page", 1), 1)
        par_page = _safe_positive_int(request.GET.get("par_page", 12), 12)

        base_qs = _cotisation_base_qs().order_by("-annee", "-mois", "famille__nom_famille")
        base_qs = _visible_cotisations_for_user(base_qs, request.user)
        filtered_qs = base_qs

        if q:
            filtered_qs = filtered_qs.filter(
                Q(description__icontains=q)
                | Q(village__nom__icontains=q)
                | Q(famille__nom_famille__icontains=q)
            )
        if statut in {"ouverte", "fermee"}:
            filtered_qs = filtered_qs.filter(statut=statut)
        if village_id:
            filtered_qs = filtered_qs.filter(village_id=village_id)
        if famille_id:
            filtered_qs = filtered_qs.filter(famille_id=famille_id)
        if annee:
            try:
                filtered_qs = filtered_qs.filter(annee=int(annee))
            except ValueError:
                annee = ""

        paginator = Paginator(filtered_qs, par_page)
        page_obj = paginator.get_page(page)
        current_page = page_obj.number
        total = paginator.count
        display_start = ((current_page - 1) * par_page) + 1 if total else 0
        display_end = min(current_page * par_page, total) if total else 0
        visible_persons = list(_visible_person_qs(request.user))
        family_counts = Counter(str(person.famille_id) for person in visible_persons)
        village_counts = Counter(str(person.famille.village_id) for person in visible_persons)
        visible_person_total = len(visible_persons)
        payment_stats = {
            str(item["cotisation_id"]): item
            for item in _visible_payments_for_user(Paiement.objects.all(), request.user)
            .values("cotisation_id")
            .annotate(
                approved_total=Coalesce(
                    Sum("montant", filter=Q(statut_validation="approved")),
                    Value(Decimal("0.00")),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                payers=Count(
                    "personne_id",
                    filter=Q(statut_validation="approved"),
                    distinct=True,
                ),
                pending=Count("id", filter=Q(statut_validation="pending")),
            )
        }
        for cotisation in page_obj.object_list:
            stats_row = payment_stats.get(str(cotisation.id), {})
            if cotisation.est_generale:
                cotisation.visible_cibles_count = visible_person_total
            elif cotisation.famille_id:
                cotisation.visible_cibles_count = family_counts.get(str(cotisation.famille_id), 0)
            else:
                cotisation.visible_cibles_count = village_counts.get(str(cotisation.village_id), 0)
            cotisation.visible_nombre_payeurs = stats_row.get("payers", 0)
            cotisation.visible_total_collecte = stats_row.get("approved_total", Decimal("0.00"))
            cotisation.visible_pending_payments = stats_row.get("pending", 0)

        return render(
            request,
            self.template_name,
            {
                "cotisations": page_obj.object_list,
                "q": q,
                "statut": statut,
                "village_id": village_id,
                "famille_id": famille_id,
                "annee": annee,
                "villages": Village.objects.filter(deleted__isnull=True).order_by("nom"),
                "familles": Family.objects.filter(deleted__isnull=True).select_related("village").order_by("nom_famille"),
                "page": current_page,
                "nb_pages": paginator.num_pages,
                "page_range": _pagination_range(current_page, paginator.num_pages),
                "total": total,
                "par_page": par_page,
                "display_start": display_start,
                "display_end": display_end,
                "stats": {
                    "total_cotisations": base_qs.count(),
                    "ouvertes": base_qs.filter(statut="ouverte").count(),
                    "fermees": base_qs.filter(statut="fermee").count(),
                    "total_collecte": (
                        _visible_payments_for_user(Paiement.objects.all(), request.user)
                        .filter(statut_validation="approved")
                        .aggregate(total=Sum("montant"))["total"]
                        or Decimal("0.00")
                    ),
                    "paiements_pending": pending_payment_count(),
                },
            },
        )


class CotisationCreateView(CotisationManagementMixin):
    template_name = "cotisations/formulaire_cotisation.html"

    def get(self, request):
        initial = {}
        famille_id = request.GET.get("famille", "").strip()
        village_id = request.GET.get("village", "").strip()
        scope = request.GET.get("scope", "").strip()
        if famille_id:
            initial["famille"] = famille_id
        if village_id:
            initial["village"] = village_id
        if scope == "general":
            initial["est_generale"] = True
        form = CotisationForm(initial=initial)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "action": "create",
                "cancel_url": reverse("dashbord:cotisation-list"),
            },
        )

    def post(self, request):
        form = CotisationForm(request.POST)
        if form.is_valid():
            cotisation = form.save()
            messages.success(
                request,
                f"La cotisation {cotisation.periode_label} a ete creee avec succes.",
            )
            return redirect("dashbord:cotisation-detail", cotisation_id=cotisation.id)

        messages.error(request, "Impossible de creer cette cotisation.")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "action": "create",
                "cancel_url": reverse("dashbord:cotisation-list"),
            },
        )


class CotisationUpdateView(CotisationManagementMixin):
    template_name = "cotisations/formulaire_cotisation.html"

    def get_object(self, cotisation_id):
        return get_object_or_404(
            _visible_cotisations_for_user(_cotisation_base_qs(), self.request.user),
            id=cotisation_id,
        )

    def get(self, request, cotisation_id):
        cotisation = self.get_object(cotisation_id)
        form = CotisationForm(instance=cotisation)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "action": "update",
                "cotisation": cotisation,
                "cancel_url": reverse("dashbord:cotisation-detail", args=[cotisation.id]),
            },
        )

    def post(self, request, cotisation_id):
        cotisation = self.get_object(cotisation_id)
        form = CotisationForm(request.POST, instance=cotisation)
        if form.is_valid():
            cotisation = form.save()
            messages.success(request, "La cotisation a ete mise a jour.")
            return redirect("dashbord:cotisation-detail", cotisation_id=cotisation.id)

        messages.error(request, "Impossible d'enregistrer cette cotisation.")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "action": "update",
                "cotisation": cotisation,
                "cancel_url": reverse("dashbord:cotisation-detail", args=[cotisation.id]),
            },
        )


class CotisationDetailView(CotisationManagementMixin):
    template_name = "cotisations/detail.html"

    def get_object(self, request, cotisation_id):
        return get_object_or_404(
            _visible_cotisations_for_user(_cotisation_base_qs(), request.user),
            id=cotisation_id,
        )

    def _serialize_payment(self, payment):
        payment.receipt_url = _safe_media_url(payment.recu)
        payment.status_meta = payment_status_meta(payment.statut_validation)
        payment.mode_meta = payment_mode_meta(payment.mode_paiement)
        return payment

    def _context(self, request, cotisation):
        q = request.GET.get("q", "").strip()
        status = request.GET.get("payment_status", "").strip()
        mode = request.GET.get("mode", "").strip()
        tracking_status = request.GET.get("tracking_status", "").strip()

        payments = _visible_payments_for_user(
            _payment_base_qs().filter(cotisation=cotisation),
            request.user,
        ).order_by(
            "-date_paiement",
            "-date_creation",
        )
        if q:
            payments = payments.filter(
                Q(personne__nom__icontains=q)
                | Q(personne__prenom__icontains=q)
                | Q(reference_transaction__icontains=q)
                | Q(nom_soumetteur__icontains=q)
                | Q(telephone_soumetteur__icontains=q)
                | Q(email_soumetteur__icontains=q)
                | Q(notes__icontains=q)
        )
        if status in PAYMENT_STATUS_META:
            payments = payments.filter(statut_validation=status)
        if mode in PAYMENT_MODE_META:
            payments = payments.filter(mode_paiement=mode)
        payments = [self._serialize_payment(payment) for payment in payments]

        pending_review_payments = [
            self._serialize_payment(payment)
            for payment in _visible_payments_for_user(
                _payment_base_qs().filter(
                    cotisation=cotisation,
                    statut_validation="pending",
                ),
                request.user,
            ).order_by("-date_paiement", "-date_creation")
        ]

        tracking_summary = _build_cotisation_person_rows(cotisation, request.user)
        person_rows = tracking_summary["rows"]
        if q:
            q_lower = q.lower()
            person_rows = [
                row
                for row in person_rows
                if q_lower in (row["person"].nom or "").lower()
                or q_lower in (row["person"].prenom or "").lower()
                or q_lower in (row["person"].code or "").lower()
                or q_lower in (row["person"].famille.nom_famille or "").lower()
                or any(
                    q_lower in (payment.reference_transaction or "").lower()
                    or q_lower in (payment.notes or "").lower()
                    for payment in row["payments"]
                )
            ]
        if tracking_status in TRACKING_STATUS_META:
            person_rows = [
                row for row in person_rows if row["status_key"] == tracking_status
            ]

        visible_persons = tracking_summary["visible_persons"]
        follow_up_rows = [
            row
            for row in person_rows
            if row["status_key"] in {"unpaid", "partiel", "pending", "retry"}
        ]
        visible_payments = _visible_payments_for_user(
            Paiement.objects.filter(cotisation=cotisation),
            request.user,
        )
        return {
            "cotisation": cotisation,
            "payments": payments,
            "pending_review_payments": pending_review_payments,
            "person_rows": person_rows,
            "q": q,
            "payment_status": status,
            "mode": mode,
            "tracking_status": tracking_status,
            "status_meta": PAYMENT_STATUS_META,
            "mode_meta": PAYMENT_MODE_META,
            "tracking_meta": TRACKING_STATUS_META,
            "cotisation_meta": cotisation_status_meta(cotisation.statut),
            "pending_rows": follow_up_rows[:12],
            "active_accounts": ComptePaiement.objects.filter(est_actif=True).order_by(
                "ordre_affichage",
                "mode",
            ),
            "stats": {
                "total_collecte": visible_payments.filter(
                    statut_validation="approved"
                ).aggregate(total=Sum("montant"))["total"] or Decimal("0.00"),
                "payeurs": visible_payments.filter(
                    statut_validation="approved"
                ).values("personne_id").distinct().count(),
                "cibles": len(visible_persons),
                "sans_paiement": sum(
                    1 for row in person_rows if row["status_key"] == "unpaid"
                ),
                "montants_definis": tracking_summary["defined_amount_count"],
                "total_attendu": tracking_summary["total_expected"],
                "reste_estime": tracking_summary["total_remaining"],
                "pending_payments": visible_payments.filter(
                    statut_validation="pending"
                ).count(),
            },
        }

    def get(self, request, cotisation_id):
        cotisation = self.get_object(request, cotisation_id)
        return render(
            request,
            self.template_name,
            self._context(request, cotisation),
        )

    def post(self, request, cotisation_id):
        cotisation = self.get_object(request, cotisation_id)
        payment_id = request.POST.get("payment_id", "").strip()
        submit_action = request.POST.get("submit_action", "").strip()

        if submit_action != "approve-payment" or not payment_id:
            messages.error(
                request,
                "Impossible de traiter cette demande de paiement.",
            )
            return redirect("dashbord:cotisation-detail", cotisation_id=cotisation.id)

        paiement = get_object_or_404(
            _visible_payments_for_user(
                _payment_base_qs().filter(cotisation=cotisation),
                request.user,
            ),
            id=payment_id,
        )
        if paiement.statut_validation == "approved":
            messages.info(
                request,
                "Ce paiement est deja valide.",
            )
            return redirect("dashbord:cotisation-detail", cotisation_id=cotisation.id)

        if paiement.statut_validation != "pending":
            messages.error(
                request,
                "Seules les demandes en attente peuvent etre validees ici.",
            )
            return redirect("dashbord:cotisation-detail", cotisation_id=cotisation.id)

        paiement.statut_validation = "approved"
        paiement.valide_par = request.user
        paiement.save()
        messages.success(
            request,
            f"La demande de paiement de {paiement.personne.nom_complet} a ete validee.",
        )
        return redirect("dashbord:cotisation-detail", cotisation_id=cotisation.id)


class CotisationPersonneUpdateView(CotisationManagementMixin):
    template_name = "cotisations/formulaire_suivi_personne.html"

    def get_cotisation(self, cotisation_id):
        return get_object_or_404(
            _visible_cotisations_for_user(_cotisation_base_qs(), self.request.user),
            id=cotisation_id,
        )

    def get_person(self, cotisation, person_id):
        return get_object_or_404(
            _visible_person_qs(self.request.user).filter(
                id__in=cotisation.personnes_cibles.values("id")
            ),
            id=person_id,
        )

    def get_tracking(self, cotisation, person):
        return CotisationPersonne.objects.filter(
            cotisation=cotisation,
            personne=person,
        ).first()

    def _summary_context(self, cotisation, person, tracking):
        payment_list = list(
            _visible_payments_for_user(
                _payment_base_qs().filter(
                    cotisation=cotisation,
                    personne=person,
                ),
                self.request.user,
            ).order_by("-date_paiement", "-date_creation")
        )
        approved, pending, rejected, approved_total = _payment_breakdown(payment_list)
        expected_amount = (
            tracking.montant_attendu
            if tracking and tracking.montant_attendu is not None
            else None
        )
        remaining_amount = compute_remaining_amount(expected_amount, approved_total)
        status_key = resolve_person_tracking_status(
            expected_amount,
            approved_total,
            pending_count=len(pending),
            rejected_count=len(rejected),
        )
        return {
            "payments": payment_list[:5],
            "approved_total": approved_total,
            "expected_amount": expected_amount,
            "remaining_amount": remaining_amount,
            "payment_count": len(payment_list),
            "pending_count": len(pending),
            "status_meta": tracking_status_meta(status_key),
        }

    def get(self, request, cotisation_id, person_id):
        cotisation = self.get_cotisation(cotisation_id)
        person = self.get_person(cotisation, person_id)
        tracking = self.get_tracking(cotisation, person)
        context = self._summary_context(cotisation, person, tracking)
        return render(
            request,
            self.template_name,
            {
                "form": CotisationPersonneForm(instance=tracking),
                "cotisation": cotisation,
                "person": person,
                "tracking": tracking,
                "cancel_url": reverse("dashbord:cotisation-detail", args=[cotisation.id]),
                **context,
            },
        )

    def post(self, request, cotisation_id, person_id):
        cotisation = self.get_cotisation(cotisation_id)
        person = self.get_person(cotisation, person_id)
        tracking = self.get_tracking(cotisation, person)
        form = CotisationPersonneForm(request.POST, instance=tracking)
        if form.is_valid():
            tracking = form.save(commit=False)
            tracking.cotisation = cotisation
            tracking.personne = person
            tracking.save()
            messages.success(
                request,
                f"Le suivi de {person.nom_complet} a ete mis a jour.",
            )
            return redirect("dashbord:cotisation-detail", cotisation_id=cotisation.id)

        messages.error(request, "Impossible d'enregistrer ce suivi individuel.")
        context = self._summary_context(cotisation, person, tracking)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "cotisation": cotisation,
                "person": person,
                "tracking": tracking,
                "cancel_url": reverse("dashbord:cotisation-detail", args=[cotisation.id]),
                **context,
            },
        )


class PaiementCreateView(CotisationManagementMixin):
    template_name = "cotisations/formulaire_paiement.html"

    def get(self, request):
        initial = {}
        cotisation_id = request.GET.get("cotisation", "").strip()
        person_id = request.GET.get("personne", "").strip()
        if cotisation_id:
            initial["cotisation"] = cotisation_id
        if person_id:
            initial["personne"] = person_id
        form = PaiementForm(initial=initial, user=request.user)
        cancel_url = reverse("dashbord:cotisation-list")
        if cotisation_id:
            cancel_url = reverse("dashbord:cotisation-detail", args=[cotisation_id])
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "action": "create",
                "cancel_url": cancel_url,
            },
        )

    def post(self, request):
        form = PaiementForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.enregistre_par = request.user
            if paiement.statut_validation == "approved":
                paiement.valide_par = request.user
            paiement.save()
            messages.success(request, "Le paiement a ete enregistre avec succes.")
            return redirect("dashbord:cotisation-detail", cotisation_id=paiement.cotisation_id)

        messages.error(request, "Impossible d'enregistrer ce paiement.")
        cancel_url = reverse("dashbord:cotisation-list")
        cotisation_id = request.POST.get("cotisation", "").strip()
        if cotisation_id:
            cancel_url = reverse("dashbord:cotisation-detail", args=[cotisation_id])
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "action": "create",
                "cancel_url": cancel_url,
            },
        )


class PaiementUpdateView(CotisationManagementMixin):
    template_name = "cotisations/formulaire_paiement.html"

    def get_object(self, paiement_id):
        return get_object_or_404(
            _visible_payments_for_user(_payment_base_qs(), self.request.user),
            id=paiement_id,
        )

    def get(self, request, paiement_id):
        paiement = self.get_object(paiement_id)
        form = PaiementForm(instance=paiement, user=request.user)
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "action": "update",
                "paiement": paiement,
                "cancel_url": reverse("dashbord:cotisation-detail", args=[paiement.cotisation_id]),
            },
        )

    def post(self, request, paiement_id):
        paiement = self.get_object(paiement_id)
        form = PaiementForm(request.POST, request.FILES, instance=paiement, user=request.user)
        if form.is_valid():
            paiement = form.save(commit=False)
            if paiement.statut_validation == "approved":
                paiement.valide_par = request.user
            paiement.save()
            messages.success(request, "Le paiement a ete mis a jour.")
            return redirect("dashbord:cotisation-detail", cotisation_id=paiement.cotisation_id)

        messages.error(request, "Impossible d'enregistrer ce paiement.")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "action": "update",
                "paiement": paiement,
                "cancel_url": reverse("dashbord:cotisation-detail", args=[paiement.cotisation_id]),
            },
        )


class ComptePaiementListView(CotisationManagementMixin):
    template_name = "cotisations/comptes.html"

    def get(self, request):
        mode = request.GET.get("mode", "").strip()
        status = request.GET.get("status", "").strip()
        accounts = ComptePaiement.objects.annotate(
            paiements_count=Count("paiements")
        ).order_by("ordre_affichage", "mode", "nom_titulaire")

        if mode in PAYMENT_MODE_META:
            accounts = accounts.filter(mode=mode)
        if status == "active":
            accounts = accounts.filter(est_actif=True)
        elif status == "inactive":
            accounts = accounts.filter(est_actif=False)

        return render(
            request,
            self.template_name,
            {
                "accounts": accounts,
                "mode": mode,
                "status": status,
                "mode_meta": PAYMENT_MODE_META,
                "stats": {
                    "total": ComptePaiement.objects.count(),
                    "actifs": ComptePaiement.objects.filter(est_actif=True).count(),
                    "inactifs": ComptePaiement.objects.filter(est_actif=False).count(),
                },
            },
        )


class ComptePaiementCreateView(CotisationManagementMixin):
    template_name = "cotisations/formulaire_compte.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "form": ComptePaiementForm(),
                "action": "create",
                "cancel_url": reverse("dashbord:compte-paiement-list"),
            },
        )

    def post(self, request):
        form = ComptePaiementForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Le compte de paiement a ete ajoute.")
            return redirect("dashbord:compte-paiement-list")

        messages.error(request, "Impossible d'enregistrer ce compte.")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "action": "create",
                "cancel_url": reverse("dashbord:compte-paiement-list"),
            },
        )


class ComptePaiementUpdateView(CotisationManagementMixin):
    template_name = "cotisations/formulaire_compte.html"

    def get_object(self, account_id):
        return get_object_or_404(ComptePaiement, id=account_id)

    def get(self, request, account_id):
        account = self.get_object(account_id)
        return render(
            request,
            self.template_name,
            {
                "form": ComptePaiementForm(instance=account),
                "action": "update",
                "account": account,
                "cancel_url": reverse("dashbord:compte-paiement-list"),
            },
        )

    def post(self, request, account_id):
        account = self.get_object(account_id)
        form = ComptePaiementForm(request.POST, request.FILES, instance=account)
        if form.is_valid():
            form.save()
            messages.success(request, "Le compte de paiement a ete mis a jour.")
            return redirect("dashbord:compte-paiement-list")

        messages.error(request, "Impossible d'enregistrer ce compte.")
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "action": "update",
                "account": account,
                "cancel_url": reverse("dashbord:compte-paiement-list"),
            },
        )
