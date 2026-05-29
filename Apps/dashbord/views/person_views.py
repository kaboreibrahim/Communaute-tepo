# dashboard/views/famille_views.py
# ============================================================
#  Vues dashboard — Familles & Personnes
#  Aucun import direct de Model Django ici
#  Tout passe par les use cases
# ============================================================

import json
from types import SimpleNamespace
from django.db                      import IntegrityError
from django.db.models               import Q
from django.shortcuts                import render, redirect, get_object_or_404
from django.contrib                  import messages
from django.contrib.auth.decorators  import login_required
from django.urls                     import reverse
from django.utils                    import timezone
from django.utils.decorators         import method_decorator
from django.http                     import JsonResponse
from django.views                    import View

from Apps.families.repositories.django_family_repo import (
    DjangoFamilyRepository,
    
)
from Apps.person.repositories.django_person_repo import (
    DjangoPersonRepository,
)

from Apps.person.use_cases.create_person import (
    ChefFamilleDejaDefiniError as CreatePersonChefFamilleDejaDefiniError,
    CreatePersonUseCase,
    ConjointIndisponibleError as CreatePersonConjointIndisponibleError,
    FamilleObligatoireError,
    FamilyIntrouvableError,
    PersonGenreInvalideError as CreatePersonGenreInvalideError,
)
from Apps.person.use_cases.delete_person import (
    DeletePersonUseCase,
    PersonIntrouvableError as DeletePersonIntrouvableError,
)
from Apps.person.use_cases.get_person import GetPersonUseCase
from Apps.person.use_cases.list_persons import ListPersonsUseCase
from Apps.person.use_cases.search_person import SearchPersonUseCase
from Apps.person.use_cases.update_person import (
    ChefFamilleDejaDefiniError as UpdatePersonChefFamilleDejaDefiniError,
    ConjointIndisponibleError as UpdatePersonConjointIndisponibleError,
    FamilleObligatoireError as UpdatePersonFamilleObligatoireError,
    FamilyIntrouvableError as UpdatePersonFamilyIntrouvableError,
    UpdatePersonUseCase,
    PersonIntrouvableError as UpdatePersonIntrouvableError,
    PersonGenreInvalideError as UpdatePersonGenreInvalideError,
)

from Apps.person.dtos.person_dto import (
    CreatePersonDTO, UpdatePersonDTO,
)
from Apps.person.models import Person
from Apps.website.models import PublicPersonSubmission
from Apps.dashbord.security import (
    ensure_person_access,
    ensure_registry_delete,
    ensure_registry_management,
    filter_person_queryset_for_user,
    visible_person_creator_id,
)
from Apps.dashbord.views.cotisation_views import get_person_cotisation_summary
# ── Helpers ───────────────────────────────────────────────────

def family_repo():
    return DjangoFamilyRepository()

def person_repo():
    return DjangoPersonRepository()

def _date_or_none(value: str):
    from datetime import date
    try:
        return date.fromisoformat(value) if value else None
    except (ValueError, TypeError):
        return None

def _get_villages():
    from Apps.villages.models import Village
    return Village.objects.filter(
        deleted__isnull=True
    ).order_by('nom')

def _get_familles(village_id: str = ''):
    from Apps.families.models import Family
    qs = Family.objects.filter(
        deleted__isnull=True
    ).select_related('village').order_by('nom_famille')
    if village_id:
        qs = qs.filter(village_id=village_id)
    return qs


def _get_personnes(genre: str = '', exclude_id: str = ''):
    qs = Person.objects.filter(
        deleted__isnull=True
    ).select_related('famille__village').order_by('prenom', 'nom')
    if genre:
        qs = qs.filter(genre=genre)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs


def _get_personnes_for_user(user, genre: str = '', exclude_id: str = ''):
    qs = filter_person_queryset_for_user(
        Person.objects.filter(
            deleted__isnull=True
        ).select_related('famille__village').order_by('prenom', 'nom'),
        user,
    )
    if genre:
        qs = qs.filter(genre=genre)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    return qs


def _get_conjoints_disponibles(
    user,
    person_id: str = '',
    conjoint_id: str = '',
):
    qs = Person.objects.filter(
        deleted__isnull=True
    ).select_related('famille__village').order_by('prenom', 'nom')
    qs = filter_person_queryset_for_user(qs, user)

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


def _safe_public_submission_photo_url(submission):
    if not submission or not submission.photo:
        return None
    try:
        return submission.photo.url
    except Exception:
        return None


def _build_public_submission_stats():
    qs = PublicPersonSubmission.objects.all()
    return {
        "total": qs.count(),
        "pending": qs.filter(statut_validation="pending").count(),
        "approved": qs.filter(statut_validation="approved").count(),
        "rejected": qs.filter(statut_validation="rejected").count(),
    }


def _build_public_submission_state(submission, source=None):
    source = source or submission.as_form_source()
    return SimpleNamespace(
        id=str(submission.id),
        photo=_safe_public_submission_photo_url(submission),
        nom=source.get("nom", submission.nom),
        prenom=source.get("prenom", submission.prenom),
        surnom=source.get("surnom", submission.surnom),
        genre=source.get("genre", submission.genre),
        date_naissance=source.get("date_naissance", ""),
        lieu_naissance=source.get("lieu_naissance", submission.lieu_naissance),
        nationalite=source.get("nationalite", submission.nationalite or "Ivoirienne"),
        numero_cni=source.get("numero_cni", submission.numero_cni),
        profession=source.get("profession", submission.profession),
        situation_matrimoniale=source.get(
            "situation_matrimoniale",
            submission.situation_matrimoniale,
        ),
        est_vivant=source.get("est_vivant") == "on",
        date_deces=source.get("date_deces", ""),
        telephone=source.get("telephone", submission.telephone),
        email=source.get("email", submission.email),
        type_residence=source.get("type_residence", submission.type_residence),
        lieu_residence=source.get("lieu_residence", submission.lieu_residence),
        famille_id=source.get(
            "famille_id",
            str(submission.famille_id) if submission.famille_id else "",
        ),
        est_chef_famille=source.get("est_chef_famille") == "on",
        pere_id=source.get("pere_id") or (
            str(submission.pere_id) if submission.pere_id else None
        ),
        pere_nom_libre=source.get("pere_nom_libre", submission.pere_nom_libre),
        mere_id=source.get("mere_id") or (
            str(submission.mere_id) if submission.mere_id else None
        ),
        mere_nom_libre=source.get("mere_nom_libre", submission.mere_nom_libre),
        conjoint_id=source.get("conjoint_id") or (
            str(submission.conjoint_id) if submission.conjoint_id else None
        ),
        conjoint_nom_libre=source.get(
            "conjoint_nom_libre",
            submission.conjoint_nom_libre,
        ),
        notes=source.get("notes", submission.notes),
    )


def _build_public_submission_context(user, submission, source=None):
    source = source or submission.as_form_source()
    conjoint_id = source.get("conjoint_id", "") or ""

    return {
        "titre": f"Verifier la pre-inscription - {submission.nom_complet}",
        "action": "create",
        "review_mode": True,
        "cancel_url": reverse("dashbord:public-person-submission-list"),
        "submission": submission,
        "personne": _build_public_submission_state(submission, source=source),
        "form_data": source,
        "villages": _get_villages(),
        "familles": _get_familles(),
        "personnes": _get_conjoints_disponibles(user, conjoint_id=conjoint_id),
        "peres_disponibles": _get_personnes_for_user(user, genre="M"),
        "meres_disponibles": _get_personnes_for_user(user, genre="F"),
    }


def _build_person_list_stats(request, q: str, famille_id: str, genre: str, village_id: str):
    qs = filter_person_queryset_for_user(
        Person.objects.filter(
            deleted__isnull=True
        ).select_related('famille__village'),
        request.user,
    )

    if q:
        qs = qs.filter(
            Q(code__icontains=q)
            | Q(nom__icontains=q)
            | Q(prenom__icontains=q)
            | Q(profession__icontains=q)
            | Q(pere_nom_libre__icontains=q)
            | Q(mere_nom_libre__icontains=q)
            | Q(conjoint_nom_libre__icontains=q)
        )
    if famille_id:
        qs = qs.filter(famille_id=famille_id)
    if genre:
        qs = qs.filter(genre=genre)
    if village_id:
        qs = qs.filter(famille__village_id=village_id)

    return {
        'total_personnes': qs.count(),
        'total_vivants': qs.filter(est_vivant=True).count(),
        'total_diaspora': qs.filter(type_residence='diaspora').count(),
        'total_familles': qs.values('famille_id').distinct().count(),
    }


def _history_actor_name(history_user):
    if not history_user:
        return 'Système'
    full_name = ''
    if hasattr(history_user, 'get_full_name'):
        full_name = (history_user.get_full_name() or '').strip()
    if full_name:
        return full_name
    return getattr(history_user, 'username', '') or getattr(
        history_user, 'email', 'Utilisateur'
    )


def _get_person_activity(person_id: str, limit: int = 5):
    from Apps.person.models import Person

    try:
        personne = Person.all_objects.select_related(
            'famille__village'
        ).get(id=person_id)
    except Exception:
        return []

    history_qs = personne.history.select_related('history_user').order_by(
        '-history_date'
    )[:limit]

    type_map = {
        '+': ('Fiche créée', 'add_circle', 'text-emerald-600'),
        '~': ('Fiche mise à jour', 'edit_note', 'text-amber-600'),
        '-': ('Fiche archivée', 'delete', 'text-slate-500'),
    }

    items = []
    for entry in history_qs:
        title, icon, color = type_map.get(
            entry.history_type,
            ('Action enregistrée', 'history', 'text-slate-500'),
        )
        items.append({
            'title': title,
            'icon': icon,
            'icon_color': color,
            'date': entry.history_date,
            'actor': _history_actor_name(entry.history_user),
        })

    if items:
        return items

    return [
        {
            'title': 'Fiche créée',
            'icon': 'add_circle',
            'icon_color': 'text-emerald-600',
            'date': personne.date_creation,
            'actor': 'Système',
        },
        {
            'title': 'Dernière mise à jour',
            'icon': 'history',
            'icon_color': 'text-amber-600',
            'date': personne.date_maj,
            'actor': 'Système',
        },
    ]


# ══════════════════════════════════════════════════════════════
# VUES — PERSONNES
# ══════════════════════════════════════════════════════════════

@method_decorator(login_required, name='dispatch')
class PersonListView(View):
    template_name = 'person/liste_personnes.html'

    def get(self, request):
        q          = request.GET.get('q', '').strip()
        famille_id = request.GET.get('famille', '').strip()
        genre      = request.GET.get('genre', '').strip()
        village_id = request.GET.get('village', '').strip()
        page       = int(request.GET.get('page', 1))
        par_page   = int(request.GET.get('par_page', 20))

        result = ListPersonsUseCase(person_repo()).execute(
            q=q, famille_id=famille_id, genre=genre,
            village_id=village_id,
            created_by_id=visible_person_creator_id(request.user),
            page=page,
            par_page=par_page,
        )

        return render(request, self.template_name, {
            **result,
            'q':          q,
            'famille_id': famille_id,
            'genre':      genre,
            'village_id': village_id,
            'villages':   _get_villages(),
            'familles':   _get_familles(village_id),
            'public_submission_stats': _build_public_submission_stats(),
            'pending_public_submissions': PublicPersonSubmission.objects.filter(
                statut_validation='pending'
            ).count(),
            'stats':      _build_person_list_stats(
                request,
                q=q,
                famille_id=famille_id,
                genre=genre,
                village_id=village_id,
            ),
        })


@method_decorator(login_required, name='dispatch')
class PublicPersonSubmissionListView(View):
    template_name = 'person/public_submissions_list.html'

    def get(self, request):
        ensure_registry_management(request.user)
        q = request.GET.get('q', '').strip()
        statut = request.GET.get('statut', '').strip()
        village_id = request.GET.get('village', '').strip()

        submissions = PublicPersonSubmission.objects.select_related(
            'famille__village',
            'valide_par',
            'personne_creee',
        ).order_by('-date_creation')

        if q:
            submissions = submissions.filter(
                Q(nom__icontains=q)
                | Q(prenom__icontains=q)
                | Q(surnom__icontains=q)
                | Q(telephone__icontains=q)
                | Q(email__icontains=q)
                | Q(numero_cni__icontains=q)
                | Q(famille__nom_famille__icontains=q)
                | Q(famille__village__nom__icontains=q)
            )

        valid_statuses = {'pending', 'approved', 'rejected'}
        if statut in valid_statuses:
            submissions = submissions.filter(statut_validation=statut)

        if village_id:
            submissions = submissions.filter(famille__village_id=village_id)

        return render(
            request,
            self.template_name,
            {
                'submissions': submissions,
                'q': q,
                'statut': statut,
                'village_id': village_id,
                'villages': _get_villages(),
                'stats': _build_public_submission_stats(),
            },
        )


@method_decorator(login_required, name='dispatch')
class PublicPersonSubmissionReviewView(View):
    template_name = 'person/person_form.html'

    def _get_submission(self, submission_id):
        return get_object_or_404(
            PublicPersonSubmission.objects.select_related(
                'famille__village',
                'pere',
                'mere',
                'conjoint',
                'valide_par',
                'personne_creee',
            ),
            id=submission_id,
        )

    def get(self, request, submission_id):
        ensure_registry_management(request.user)
        submission = self._get_submission(submission_id)

        if submission.statut_validation == 'approved' and submission.personne_creee_id:
            messages.warning(
                request,
                "Cette pre-inscription a deja ete validee et enregistree dans le registre.",
            )
            return redirect(
                'dashbord:person-detail',
                person_id=submission.personne_creee_id,
            )

        return render(
            request,
            self.template_name,
            _build_public_submission_context(request.user, submission),
        )

    def post(self, request, submission_id):
        ensure_registry_management(request.user)
        submission = self._get_submission(submission_id)

        if submission.statut_validation == 'approved' and submission.personne_creee_id:
            messages.warning(
                request,
                "Cette pre-inscription a deja ete traitee auparavant.",
            )
            return redirect(
                'dashbord:person-detail',
                person_id=submission.personne_creee_id,
            )

        submit_action = request.POST.get('submit_action', 'approve')
        submission.apply_form_data(request.POST, request.FILES)

        if submit_action == 'reject':
            submission.statut_validation = 'rejected'
            submission.valide_par = request.user
            submission.date_validation = timezone.now()
            submission.personne_creee = None
            submission.save()
            messages.warning(
                request,
                f"La pre-inscription de {submission.nom_complet} a ete marquee comme refusee.",
            )
            return redirect('dashbord:public-person-submission-list')

        data = CreatePersonDTO(
            nom=request.POST.get('nom', '').strip(),
            prenom=request.POST.get('prenom', '').strip(),
            surnom=request.POST.get('surnom', '').strip(),
            genre=request.POST.get('genre', '').strip(),
            famille_id=request.POST.get('famille_id', '').strip(),
            date_naissance=_date_or_none(request.POST.get('date_naissance')),
            lieu_naissance=request.POST.get('lieu_naissance', '').strip(),
            nationalite=request.POST.get('nationalite', 'Ivoirienne').strip(),
            numero_cni=request.POST.get('numero_cni', '').strip(),
            profession=request.POST.get('profession', '').strip(),
            situation_matrimoniale=request.POST.get(
                'situation_matrimoniale',
                'celibataire',
            ),
            est_vivant=request.POST.get('est_vivant') == 'on',
            date_deces=_date_or_none(request.POST.get('date_deces')),
            telephone=request.POST.get('telephone', '').strip(),
            email=request.POST.get('email', '').strip(),
            type_residence=request.POST.get('type_residence', 'village'),
            lieu_residence=request.POST.get('lieu_residence', '').strip(),
            est_chef_famille=request.POST.get('est_chef_famille') == 'on',
            pere_id=request.POST.get('pere_id') or None,
            pere_nom_libre=request.POST.get('pere_nom_libre', '').strip(),
            mere_id=request.POST.get('mere_id') or None,
            mere_nom_libre=request.POST.get('mere_nom_libre', '').strip(),
            conjoint_id=request.POST.get('conjoint_id') or None,
            conjoint_nom_libre=request.POST.get('conjoint_nom_libre', '').strip(),
            notes=request.POST.get('notes', '').strip(),
            photo=request.FILES.get('photo') or submission.photo,
            created_by_id=str(request.user.id),
        )

        try:
            personne = CreatePersonUseCase(
                person_repo(), family_repo()
            ).execute(data)
            submission.statut_validation = 'approved'
            submission.valide_par = request.user
            submission.date_validation = timezone.now()
            submission.personne_creee_id = personne.id
            submission.save()
            messages.success(
                request,
                f"La pre-inscription de {submission.nom_complet} a ete verifiee et enregistree definitivement.",
            )
            return redirect('dashbord:person-detail', person_id=personne.id)
        except (
            FamilleObligatoireError, FamilyIntrouvableError,
            CreatePersonChefFamilleDejaDefiniError,
            CreatePersonGenreInvalideError,
            CreatePersonConjointIndisponibleError,
            ValueError,
        ) as e:
            messages.error(request, str(e))
        except IntegrityError:
            messages.error(
                request,
                "Impossible d'enregistrer ce conjoint. Cette personne est deja liee a un autre conjoint.",
            )

        return render(
            request,
            self.template_name,
            _build_public_submission_context(
                request.user,
                submission,
                source=request.POST,
            ),
        )


@method_decorator(login_required, name='dispatch')
class PublicPersonSubmissionRejectView(View):
    def post(self, request, submission_id):
        ensure_registry_management(request.user)
        submission = get_object_or_404(PublicPersonSubmission, id=submission_id)

        if submission.statut_validation == 'approved' and submission.personne_creee_id:
            messages.warning(
                request,
                "Cette pre-inscription a deja ete validee et ne peut plus etre refusee.",
            )
            return redirect(
                'dashbord:person-detail',
                person_id=submission.personne_creee_id,
            )

        submission.statut_validation = 'rejected'
        submission.valide_par = request.user
        submission.date_validation = timezone.now()
        submission.personne_creee = None
        submission.save(update_fields=[
            'statut_validation',
            'valide_par',
            'date_validation',
            'personne_creee',
        ])
        messages.warning(
            request,
            f"La pre-inscription de {submission.nom_complet} a ete marquee comme refusee.",
        )
        return redirect('dashbord:public-person-submission-list')


@method_decorator(login_required, name='dispatch')
class PersonDetailView(View):
    template_name = 'person/detail.html'

    def get(self, request, person_id):
        ensure_person_access(request.user, person_id)
        personne = GetPersonUseCase(person_repo()).execute(
            str(person_id),
            created_by_id=visible_person_creator_id(request.user),
        )
        if not personne:
            messages.error(request, "Personne introuvable.")
            return redirect('dashbord:person-list')
        return render(request, self.template_name, {
            'personne': personne,
            'activity_items': _get_person_activity(str(person_id)),
            'cotisation_summary': get_person_cotisation_summary(str(person_id)),
        })


@method_decorator(login_required, name='dispatch')
class PersonCreateView(View):
    template_name = 'person/person_form.html'

    def get(self, request):
        ensure_registry_management(request.user)
        famille_id = request.GET.get('famille', '')
        # Create a dummy personne object with default values for create mode
        personne = type('Personne', (), {
            'id': '',
            'photo': None,
            'nom': '',
            'prenom': '',
            'surnom': '',
            'genre': '',
            'date_naissance': '',
            'lieu_naissance': '',
            'nationalite': 'Ivoirienne',
            'numero_cni': '',
            'profession': '',
            'situation_matrimoniale': 'celibataire',
            'est_vivant': True,
            'date_deces': '',
            'telephone': '',
            'email': '',
            'type_residence': 'village',
            'lieu_residence': '',
            'famille_id': famille_id,
            'est_chef_famille': False,
            'pere_id': None,
            'pere_nom_libre': '',
            'mere_id': None,
            'mere_nom_libre': '',
            'conjoint_id': None,
            'conjoint_nom_libre': '',
            'notes': '',
        })()
        return render(request, self.template_name, {
            'titre':       'Enregistrer une personne',
            'action':      'create',
            'personne':    personne,
            'villages':    _get_villages(),
            'famille_id':  famille_id,
            'familles':    _get_familles(),
            'personnes':   _get_conjoints_disponibles(request.user),
            'peres_disponibles': _get_personnes_for_user(
                request.user, genre='M'
            ),
            'meres_disponibles': _get_personnes_for_user(
                request.user, genre='F'
            ),
        })

    def post(self, request):
        ensure_registry_management(request.user)
        data = CreatePersonDTO(
            nom=request.POST.get('nom', '').strip(),
            prenom=request.POST.get('prenom', '').strip(),
            surnom=request.POST.get('surnom', '').strip(),
            genre=request.POST.get('genre', '').strip(),
            famille_id=request.POST.get('famille_id', '').strip(),
            date_naissance=_date_or_none(request.POST.get('date_naissance')),
            lieu_naissance=request.POST.get('lieu_naissance', '').strip(),
            nationalite=request.POST.get('nationalite', 'Ivoirienne').strip(),
            numero_cni=request.POST.get('numero_cni', '').strip(),
            profession=request.POST.get('profession', '').strip(),
            situation_matrimoniale=request.POST.get('situation_matrimoniale', 'celibataire'),
            est_vivant=request.POST.get('est_vivant') == 'on',
            date_deces=_date_or_none(request.POST.get('date_deces')),
            telephone=request.POST.get('telephone', '').strip(),
            email=request.POST.get('email', '').strip(),
            type_residence=request.POST.get('type_residence', 'village'),
            lieu_residence=request.POST.get('lieu_residence', '').strip(),
            est_chef_famille=request.POST.get('est_chef_famille') == 'on',
            pere_id=request.POST.get('pere_id') or None,
            pere_nom_libre=request.POST.get('pere_nom_libre', '').strip(),
            mere_id=request.POST.get('mere_id') or None,
            mere_nom_libre=request.POST.get('mere_nom_libre', '').strip(),
            conjoint_id=request.POST.get('conjoint_id') or None,
            conjoint_nom_libre=request.POST.get('conjoint_nom_libre', '').strip(),
            notes=request.POST.get('notes', '').strip(),
            photo=request.FILES.get('photo'),
            created_by_id=str(request.user.id),
        )
        try:
            p = CreatePersonUseCase(
                person_repo(), family_repo()
            ).execute(data)
            messages.success(
                request,
                f"« {p.nom_complet} » enregistré(e) avec succès."
            )
            return redirect('dashbord:person-detail', person_id=p.id)
        except (
            FamilleObligatoireError, FamilyIntrouvableError,
            CreatePersonChefFamilleDejaDefiniError,
            CreatePersonGenreInvalideError,
            CreatePersonConjointIndisponibleError,
            ValueError,
        ) as e:
            messages.error(request, str(e))
            # Create a dummy personne object with form data for error display
            personne = type('Personne', (), {
                'id': '',
                'photo': None,
                'nom': request.POST.get('nom', ''),
                'prenom': request.POST.get('prenom', ''),
                'surnom': request.POST.get('surnom', ''),
                'genre': request.POST.get('genre', ''),
                'date_naissance': request.POST.get('date_naissance', ''),
                'lieu_naissance': request.POST.get('lieu_naissance', ''),
                'nationalite': request.POST.get('nationalite', 'Ivoirienne'),
                'numero_cni': request.POST.get('numero_cni', ''),
                'profession': request.POST.get('profession', ''),
                'situation_matrimoniale': request.POST.get('situation_matrimoniale', 'celibataire'),
                'est_vivant': request.POST.get('est_vivant') == 'on',
                'date_deces': request.POST.get('date_deces', ''),
                'telephone': request.POST.get('telephone', ''),
                'email': request.POST.get('email', ''),
                'type_residence': request.POST.get('type_residence', 'village'),
                'lieu_residence': request.POST.get('lieu_residence', ''),
                'famille_id': request.POST.get('famille_id', ''),
                'est_chef_famille': request.POST.get('est_chef_famille') == 'on',
                'pere_id': request.POST.get('pere_id') or None,
                'pere_nom_libre': request.POST.get('pere_nom_libre', ''),
                'mere_id': request.POST.get('mere_id') or None,
                'mere_nom_libre': request.POST.get('mere_nom_libre', ''),
                'conjoint_id': request.POST.get('conjoint_id') or None,
                'conjoint_nom_libre': request.POST.get('conjoint_nom_libre', ''),
                'notes': request.POST.get('notes', ''),
            })()
            return render(request, self.template_name, {
                'titre':     'Enregistrer une personne',
                'action':    'create',
                'personne':  personne,
                'villages':  _get_villages(),
                'familles':  _get_familles(),
                'personnes': _get_conjoints_disponibles(
                    request.user,
                    conjoint_id=request.POST.get('conjoint_id', '')
                ),
                'peres_disponibles': _get_personnes_for_user(
                    request.user, genre='M'
                ),
                'meres_disponibles': _get_personnes_for_user(
                    request.user, genre='F'
                ),
                'form_data': request.POST,
            })
        except IntegrityError:
            messages.error(
                request,
                "Impossible d'enregistrer ce conjoint. Cette personne est déjà liée à un autre conjoint.",
            )
            personne = type('Personne', (), {
                'id': '',
                'photo': None,
                'nom': request.POST.get('nom', ''),
                'prenom': request.POST.get('prenom', ''),
                'surnom': request.POST.get('surnom', ''),
                'genre': request.POST.get('genre', ''),
                'date_naissance': request.POST.get('date_naissance', ''),
                'lieu_naissance': request.POST.get('lieu_naissance', ''),
                'nationalite': request.POST.get('nationalite', 'Ivoirienne'),
                'numero_cni': request.POST.get('numero_cni', ''),
                'profession': request.POST.get('profession', ''),
                'situation_matrimoniale': request.POST.get('situation_matrimoniale', 'celibataire'),
                'est_vivant': request.POST.get('est_vivant') == 'on',
                'date_deces': request.POST.get('date_deces', ''),
                'telephone': request.POST.get('telephone', ''),
                'email': request.POST.get('email', ''),
                'type_residence': request.POST.get('type_residence', 'village'),
                'lieu_residence': request.POST.get('lieu_residence', ''),
                'famille_id': request.POST.get('famille_id', ''),
                'est_chef_famille': request.POST.get('est_chef_famille') == 'on',
                'pere_id': request.POST.get('pere_id') or None,
                'pere_nom_libre': request.POST.get('pere_nom_libre', ''),
                'mere_id': request.POST.get('mere_id') or None,
                'mere_nom_libre': request.POST.get('mere_nom_libre', ''),
                'conjoint_id': request.POST.get('conjoint_id') or None,
                'conjoint_nom_libre': request.POST.get('conjoint_nom_libre', ''),
                'notes': request.POST.get('notes', ''),
            })()
            return render(request, self.template_name, {
                'titre':     'Enregistrer une personne',
                'action':    'create',
                'personne':  personne,
                'villages':  _get_villages(),
                'familles':  _get_familles(),
                'personnes': _get_conjoints_disponibles(
                    request.user,
                    conjoint_id=request.POST.get('conjoint_id', '')
                ),
                'peres_disponibles': _get_personnes_for_user(
                    request.user, genre='M'
                ),
                'meres_disponibles': _get_personnes_for_user(
                    request.user, genre='F'
                ),
                'form_data': request.POST,
            })


@method_decorator(login_required, name='dispatch')
class PersonUpdateView(View):
    template_name = 'person/person_form.html'

    def get(self, request, person_id):
        ensure_registry_management(request.user)
        ensure_person_access(request.user, person_id)
        personne = GetPersonUseCase(person_repo()).execute(
            str(person_id),
            created_by_id=visible_person_creator_id(request.user),
        )
        if not personne:
            messages.error(request, "Personne introuvable.")
            return redirect('dashbord:person-list')
        return render(request, self.template_name, {
            'titre':    f'Modifier — {personne.nom_complet}',
            'action':   'update',
            'personne': personne,
            'villages': _get_villages(),
            'familles': _get_familles(),
            'personnes': _get_conjoints_disponibles(
                request.user,
                person_id=personne.id,
                conjoint_id=personne.conjoint_id or '',
            ),
            'peres_disponibles': _get_personnes_for_user(
                request.user,
                genre='M', exclude_id=personne.id
            ),
            'meres_disponibles': _get_personnes_for_user(
                request.user,
                genre='F', exclude_id=personne.id
            ),
        })

    def post(self, request, person_id):
        ensure_registry_management(request.user)
        ensure_person_access(request.user, person_id)
        data = UpdatePersonDTO(
            id=str(person_id),
            nom=request.POST.get('nom', '').strip(),
            prenom=request.POST.get('prenom', '').strip(),
            surnom=request.POST.get('surnom', '').strip(),
            genre=request.POST.get('genre', '').strip(),
            famille_id=request.POST.get('famille_id', '').strip(),
            date_naissance=_date_or_none(request.POST.get('date_naissance')),
            lieu_naissance=request.POST.get('lieu_naissance', '').strip(),
            nationalite=request.POST.get('nationalite', 'Ivoirienne').strip(),
            numero_cni=request.POST.get('numero_cni', '').strip(),
            profession=request.POST.get('profession', '').strip(),
            situation_matrimoniale=request.POST.get('situation_matrimoniale', 'celibataire'),
            est_vivant=request.POST.get('est_vivant') == 'on',
            date_deces=_date_or_none(request.POST.get('date_deces')),
            telephone=request.POST.get('telephone', '').strip(),
            email=request.POST.get('email', '').strip(),
            type_residence=request.POST.get('type_residence', 'village'),
            lieu_residence=request.POST.get('lieu_residence', '').strip(),
            est_chef_famille=request.POST.get('est_chef_famille') == 'on',
            pere_id=request.POST.get('pere_id') or None,
            pere_nom_libre=request.POST.get('pere_nom_libre', '').strip(),
            mere_id=request.POST.get('mere_id') or None,
            mere_nom_libre=request.POST.get('mere_nom_libre', '').strip(),
            conjoint_id=request.POST.get('conjoint_id') or None,
            conjoint_nom_libre=request.POST.get('conjoint_nom_libre', '').strip(),
            notes=request.POST.get('notes', '').strip(),
            photo=request.FILES.get('photo'),
        )
        try:
            p = UpdatePersonUseCase(
                person_repo(), family_repo()
            ).execute(data)
            messages.success(
                request, f"« {p.nom_complet} » modifié(e) avec succès."
            )
            return redirect('dashbord:person-detail', person_id=p.id)
        except UpdatePersonIntrouvableError as e:
            messages.error(request, str(e))
            return redirect('dashbord:person-list')
        except (
            UpdatePersonFamilleObligatoireError,
            UpdatePersonFamilyIntrouvableError,
            UpdatePersonChefFamilleDejaDefiniError,
            UpdatePersonGenreInvalideError,
            UpdatePersonConjointIndisponibleError,
            ValueError,
        ) as e:
            messages.error(request, str(e))
            return redirect('dashbord:person-update', person_id=person_id)
        except IntegrityError:
            messages.error(
                request,
                "Impossible d'enregistrer ce conjoint. Cette personne est déjà liée à un autre conjoint.",
            )
            return redirect('dashbord:person-update', person_id=person_id)


@method_decorator(login_required, name='dispatch')
class PersonDeleteView(View):
    template_name = 'person/delete.html'

    def get(self, request, person_id):
        ensure_registry_delete(request.user)
        ensure_person_access(request.user, person_id)
        personne = GetPersonUseCase(person_repo()).execute(
            str(person_id),
            created_by_id=visible_person_creator_id(request.user),
        )
        if not personne:
            messages.error(request, "Personne introuvable.")
            return redirect('dashbord:person-list')
        return render(request, self.template_name, {
            'personne': personne,
        })

    def post(self, request, person_id):
        ensure_registry_delete(request.user)
        ensure_person_access(request.user, person_id)
        try:
            DeletePersonUseCase(person_repo()).execute(str(person_id))
            messages.success(request, "Personne supprimée avec succès.")
        except DeletePersonIntrouvableError as e:
            messages.error(request, str(e))
        return redirect('dashbord:person-list')


# ══════════════════════════════════════════════════════════════
# API AJAX — AUTOCOMPLÉTION PÈRE / MÈRE
# ══════════════════════════════════════════════════════════════

@login_required
def api_search_person(request):
    """
    GET /dashboard/api/personnes/recherche/
    Params : q, genre (M|F), village_id
    Retourne JSON pour l'autocomplétion père/mère.
    """
    ensure_registry_management(request.user)
    q          = request.GET.get('q', '').strip()
    genre      = request.GET.get('genre', '').strip()
    village_id = request.GET.get('village_id', '').strip()

    resultats = SearchPersonUseCase(person_repo()).execute(
        q=q,
        genre=genre,
        village_id=village_id,
        created_by_id=visible_person_creator_id(request.user),
    )

    return JsonResponse([
        {
            'id':          r.id,
            'code':        r.code,
            'nom_complet': r.nom_complet,
            'village':     r.village,
            'age':         r.age,
            'genre':       r.genre,
            'photo':       r.photo,
        }
        for r in resultats
    ], safe=False)


# ══════════════════════════════════════════════════════════════
# HELPER — Conversion TreeNodeDTO → dict JSON pour D3.js
# ══════════════════════════════════════════════════════════════

def _tree_to_dict(node) -> dict:
    if not node:
        return {}
    return {
        'id':         node.id,
        'nom_complet': node.nom_complet,
        'prenom':     node.prenom,
        'nom':        node.nom,
        'genre':      node.genre,
        'age':        node.age,
        'est_vivant': node.est_vivant,
        'photo':      node.photo,
        'conjoint':   node.conjoint,
        'generation': node.generation,
        'enfants':    [_tree_to_dict(e) for e in node.enfants],
    }
