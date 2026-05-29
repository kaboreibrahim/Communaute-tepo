from types import SimpleNamespace

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, render
from django.views import View

from Apps.families.repositories.django_family_repo import DjangoFamilyRepository
from Apps.website.models import PublicPersonSubmission


def family_repo():
    return DjangoFamilyRepository()


def _date_or_none(value: str):
    from datetime import date

    try:
        return date.fromisoformat(value) if value else None
    except (ValueError, TypeError):
        return None


def _get_villages():
    from Apps.villages.models import Village

    return Village.objects.filter(
        deleted__isnull=True,
    ).order_by("nom")


def _get_familles(village_id: str = ""):
    from Apps.families.models import Family

    qs = Family.objects.filter(
        deleted__isnull=True,
    ).select_related("village").order_by("nom_famille")
    if village_id:
        qs = qs.filter(village_id=village_id)
    return qs


def _get_personnes(genre: str = "", exclude_id: str = ""):
    from Apps.person.models import Person

    qs = Person.objects.filter(
        deleted__isnull=True,
    ).select_related("famille__village").order_by("prenom", "nom")
    if genre:
        qs = qs.filter(genre=genre)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs


def _get_conjoints_disponibles(person_id: str = "", conjoint_id: str = ""):
    from Apps.person.models import Person

    qs = Person.objects.filter(
        deleted__isnull=True,
    ).select_related("famille__village").order_by("prenom", "nom")

    if person_id:
        qs = qs.exclude(id=person_id)
        disponibilite = (
            (Q(conjoint__isnull=True) | Q(conjoint_id=person_id))
            & (Q(conjoint_de__isnull=True) | Q(conjoint_de__id=person_id))
        )
    else:
        disponibilite = Q(conjoint__isnull=True) & Q(conjoint_de__isnull=True)

    if conjoint_id:
        qs = qs.filter(disponibilite | Q(id=conjoint_id)).distinct()
    else:
        qs = qs.filter(disponibilite)

    return qs


def _build_public_person_state(source=None, famille_id: str = ""):
    source = source or {}
    est_vivant_value = source.get("est_vivant") if source else "on"
    return SimpleNamespace(
        id="",
        photo=None,
        nom=source.get("nom", ""),
        prenom=source.get("prenom", ""),
        surnom=source.get("surnom", ""),
        genre=source.get("genre", ""),
        date_naissance=source.get("date_naissance", ""),
        lieu_naissance=source.get("lieu_naissance", ""),
        nationalite=source.get("nationalite", "Ivoirienne"),
        numero_cni=source.get("numero_cni", ""),
        profession=source.get("profession", ""),
        situation_matrimoniale=source.get("situation_matrimoniale", "celibataire"),
        est_vivant=est_vivant_value == "on",
        date_deces=source.get("date_deces", ""),
        telephone=source.get("telephone", ""),
        email=source.get("email", ""),
        type_residence=source.get("type_residence", "village"),
        lieu_residence=source.get("lieu_residence", ""),
        famille_id=source.get("famille_id", famille_id),
        pere_id=source.get("pere_id") or None,
        pere_nom_libre=source.get("pere_nom_libre", ""),
        mere_id=source.get("mere_id") or None,
        mere_nom_libre=source.get("mere_nom_libre", ""),
        conjoint_id=source.get("conjoint_id") or None,
        conjoint_nom_libre=source.get("conjoint_nom_libre", ""),
        notes=source.get("notes", ""),
    )


def _build_registration_context(source=None, famille_id: str = ""):
    personne = _build_public_person_state(source=source, famille_id=famille_id)
    conjoint_id = (source.get("conjoint_id") if source else "") or ""

    return {
        "titre": "Pre-inscription citoyenne",
        "action": "create",
        "personne": personne,
        "form_data": source or {},
        "familles": _get_familles(),
        "villages": _get_villages(),
        "personnes": _get_conjoints_disponibles(conjoint_id=conjoint_id),
        "peres_disponibles": _get_personnes(genre="M"),
        "meres_disponibles": _get_personnes(genre="F"),
    }


class PublicPersonRegistrationView(View):
    template_name = "person_register.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            _build_registration_context(
                famille_id=request.GET.get("famille", "").strip(),
            ),
        )

    def post(self, request):
        famille_id = request.POST.get("famille_id", "").strip()
        genre = request.POST.get("genre", "").strip()

        if not famille_id:
            messages.error(
                request,
                "La famille d'appartenance est obligatoire avant de soumettre la demande.",
            )
        elif not family_repo().get_by_id(famille_id):
            messages.error(
                request,
                "La famille selectionnee est introuvable. Veuillez la choisir de nouveau.",
            )
        elif genre not in {"M", "F"}:
            messages.error(
                request,
                "Veuillez selectionner le genre de la personne avant validation.",
            )
        else:
            submission = PublicPersonSubmission()
            submission.apply_form_data(request.POST, request.FILES)
            submission.save()
            messages.success(
                request,
                (
                    f"La demande pour {submission.nom_complet} a bien ete envoyee. "
                    "Elle sera analysee par l'administration ou un agent de saisie "
                    "avant l'enregistrement definitif."
                ),
            )
            return redirect("website:person-register")

        return render(
            request,
            self.template_name,
            _build_registration_context(source=request.POST),
        )
