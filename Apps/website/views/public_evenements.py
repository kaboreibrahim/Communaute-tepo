from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import DetailView, ListView

from Apps.events.models import Event, TypeEvenement
from Apps.villages.models import Village

EVENT_THEMES = {
    "naissance": {
        "badge": "bg-emerald-500 text-white",
        "surface": "bg-emerald-50",
        "icon": "text-emerald-600",
        "border": "border-emerald-200",
        "date_text": "text-emerald-700",
    },
    "deces": {
        "badge": "bg-slate-800 text-white",
        "surface": "bg-slate-100",
        "icon": "text-slate-500",
        "border": "border-slate-300",
        "date_text": "text-slate-700",
    },
    "mariage": {
        "badge": "bg-orange-500 text-white",
        "surface": "bg-orange-50",
        "icon": "text-orange-600",
        "border": "border-orange-200",
        "date_text": "text-orange-700",
    },
    "bapteme": {
        "badge": "bg-amber-500 text-white",
        "surface": "bg-amber-50",
        "icon": "text-amber-600",
        "border": "border-amber-200",
        "date_text": "text-amber-700",
    },
    "diplome": {
        "badge": "bg-sky-600 text-white",
        "surface": "bg-sky-50",
        "icon": "text-sky-600",
        "border": "border-sky-200",
        "date_text": "text-sky-700",
    },
    "deuil": {
        "badge": "bg-slate-900 text-white",
        "surface": "bg-slate-100",
        "icon": "text-slate-600",
        "border": "border-slate-400",
        "date_text": "text-slate-800",
    },
    "fete": {
        "badge": "bg-pink-500 text-white",
        "surface": "bg-pink-50",
        "icon": "text-pink-600",
        "border": "border-pink-200",
        "date_text": "text-pink-700",
    },
    "communaute": {
        "badge": "bg-primary text-white",
        "surface": "bg-primary/5",
        "icon": "text-primary",
        "border": "border-primary/20",
        "date_text": "text-primary",
    },
}

DEFAULT_THEME = {
    "badge": "bg-slate-500 text-white",
    "surface": "bg-slate-50",
    "icon": "text-slate-500",
    "border": "border-slate-200",
    "date_text": "text-slate-600",
}

MONTH_FR = ["", "jan", "fév", "mar", "avr", "mai", "jun", "jul", "aoû", "sep", "oct", "nov", "déc"]


def _qs_publies():
    return Event.objects.filter(
        est_public=True,
        statut_validation="approved",
    ).select_related("type", "village", "personne")


def _with_theme(qs):
    events = list(qs)
    for ev in events:
        slug = ev.type.slug if ev.type_id else ""
        ev.theme = EVENT_THEMES.get(slug, DEFAULT_THEME)
    return events


class EvenementListView(ListView):
    model = Event
    template_name = "evenements/evenement_list.html"
    context_object_name = "evenements"
    paginate_by = 12

    def get_queryset(self):
        qs = _qs_publies().order_by("-date_evenement", "-date_creation")
        type_slug = self.request.GET.get("type", "")
        village_id = self.request.GET.get("village", "")
        q = self.request.GET.get("q", "").strip()
        periode = self.request.GET.get("periode", "")
        today = timezone.now().date()

        if type_slug:
            qs = qs.filter(type__slug=type_slug)
        if village_id:
            qs = qs.filter(village__id=village_id)
        if q:
            qs = qs.filter(
                Q(titre__icontains=q)
                | Q(resume__icontains=q)
                | Q(description__icontains=q)
                | Q(lieu__icontains=q)
            )
        if periode == "avenir":
            qs = qs.filter(date_evenement__gte=today).order_by("date_evenement")
        elif periode == "passe":
            qs = qs.filter(date_evenement__lt=today).order_by("-date_evenement")

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.now().date()

        # Enrich with themes
        ctx["evenements"] = _with_theme(ctx["evenements"])

        ctx["types"] = TypeEvenement.objects.annotate(
            nb=Count(
                "evenements",
                filter=Q(evenements__est_public=True, evenements__statut_validation="approved"),
            )
        ).order_by("ordre", "nom")

        ctx["villages"] = (
            Village.objects.filter(deleted__isnull=True)
            .annotate(
                nb=Count(
                    "evenements",
                    filter=Q(evenements__est_public=True, evenements__statut_validation="approved"),
                )
            )
            .filter(nb__gt=0)
            .order_by("nom")
        )

        ctx["a_venir"] = _qs_publies().filter(date_evenement__gte=today).count()
        ctx["total"] = _qs_publies().count()

        ctx["prochains"] = _with_theme(
            _qs_publies()
            .filter(date_evenement__gte=today)
            .order_by("date_evenement")[:6]
        )

        ctx["filtre_type"] = self.request.GET.get("type", "")
        ctx["filtre_village"] = self.request.GET.get("village", "")
        ctx["filtre_periode"] = self.request.GET.get("periode", "")
        ctx["q"] = self.request.GET.get("q", "")
        ctx["titre_filtre"] = self._get_titre_filtre(ctx)
        ctx["event_themes"] = EVENT_THEMES
        ctx["month_fr"] = MONTH_FR
        return ctx

    def _get_titre_filtre(self, ctx):
        type_slug = ctx["filtre_type"]
        if type_slug:
            try:
                t = TypeEvenement.objects.get(slug=type_slug)
                return f"Type : {t.nom}"
            except TypeEvenement.DoesNotExist:
                pass
        if ctx["q"]:
            return f"Recherche : « {ctx['q']} »"
        return ""


class EvenementDetailView(DetailView):
    model = Event
    template_name = "evenements/evenement_detail.html"
    context_object_name = "evenement"

    def get_object(self, queryset=None):
        obj = get_object_or_404(
            Event,
            pk=self.kwargs["pk"],
            est_public=True,
            statut_validation="approved",
        )
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ev = self.object
        slug = ev.type.slug if ev.type_id else ""
        ctx["theme"] = EVENT_THEMES.get(slug, DEFAULT_THEME)
        ctx["month_fr"] = MONTH_FR

        # Related events (same type, last 6)
        similaires_qs = (
            _qs_publies()
            .exclude(pk=ev.pk)
            .order_by("-date_evenement")
        )
        if ev.type_id:
            similaires_qs = similaires_qs.filter(type=ev.type)[:6]
        else:
            similaires_qs = similaires_qs[:6]
        ctx["similaires"] = _with_theme(similaires_qs)

        # Upcoming events
        today = timezone.now().date()
        ctx["prochains"] = _with_theme(
            _qs_publies()
            .filter(date_evenement__gte=today)
            .exclude(pk=ev.pk)
            .order_by("date_evenement")[:5]
        )
        ctx["types"] = TypeEvenement.objects.annotate(
            nb=Count(
                "evenements",
                filter=Q(evenements__est_public=True, evenements__statut_validation="approved"),
            )
        ).order_by("ordre", "nom")
        return ctx


class EvenementByTypeView(EvenementListView):
    template_name = "evenements/evenement_list.html"

    def get_queryset(self):
        self.type_obj = get_object_or_404(TypeEvenement, slug=self.kwargs["type_slug"])
        return (
            _qs_publies()
            .filter(type=self.type_obj)
            .order_by("-date_evenement", "-date_creation")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["type_courant"] = self.type_obj
        ctx["titre_filtre"] = f"Type : {self.type_obj.nom}"
        ctx["filtre_type"] = self.type_obj.slug
        return ctx
