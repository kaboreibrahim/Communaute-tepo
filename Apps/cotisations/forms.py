from django import forms
from django.db.models import Q

from Apps.cotisations.models import (
    ComptePaiement,
    Cotisation,
    CotisationPersonne,
    Paiement,
)
from Apps.families.models import Family
from Apps.person.models import Person
from Apps.villages.models import Village


FIELD_CLASSES = (
    "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm "
    "text-slate-700 shadow-sm transition focus:border-primary focus:outline-none "
    "focus:ring-2 focus:ring-primary/15"
)

TEXTAREA_CLASSES = FIELD_CLASSES + " min-h-[110px]"


class DashboardModelForm(forms.ModelForm):
    def _apply_field_classes(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "h-4 w-4 rounded border-slate-300 text-primary"
                continue

            current_classes = widget.attrs.get("class", "")
            widget.attrs["class"] = (
                f"{current_classes} "
                f"{TEXTAREA_CLASSES if isinstance(widget, forms.Textarea) else FIELD_CLASSES}"
            ).strip()


class CotisationForm(DashboardModelForm):
    class Meta:
        model = Cotisation
        fields = [
            "mois",
            "annee",
            "est_generale",
            "village",
            "famille",
            "description",
            "statut",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["village"].queryset = Village.objects.filter(
            deleted__isnull=True
        ).order_by("nom")
        self.fields["famille"].queryset = Family.objects.filter(
            deleted__isnull=True
        ).select_related("village").order_by("nom_famille")
        selected_village_id = (
            self.data.get("village")
            or getattr(self.instance, "village_id", None)
        )
        if selected_village_id:
            self.fields["famille"].queryset = self.fields["famille"].queryset.filter(
                village_id=selected_village_id
            )
        self.fields["annee"].widget = forms.NumberInput(
            attrs={"min": 2000, "max": 2100}
        )
        self.fields["est_generale"].help_text = (
            "Si cette option est cochee, la cotisation s'applique a toutes les personnes "
            "du mois selectionne et les champs village/famille sont ignores."
        )
        self._apply_field_classes()

    def clean(self):
        cleaned_data = super().clean()
        est_generale = cleaned_data.get("est_generale")
        famille = cleaned_data.get("famille")
        village = cleaned_data.get("village")
        if est_generale:
            cleaned_data["village"] = None
            cleaned_data["famille"] = None
        elif famille and not village:
            cleaned_data["village"] = famille.village
        return cleaned_data


class PaiementForm(DashboardModelForm):
    class Meta:
        model = Paiement
        fields = [
            "personne",
            "cotisation",
            "montant",
            "mode_paiement",
            "compte_paiement",
            "reference_transaction",
            "nom_soumetteur",
            "telephone_soumetteur",
            "email_soumetteur",
            "recu",
            "statut_validation",
            "date_paiement",
            "notes",
        ]
        widgets = {
            "date_paiement": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        person_qs = Person.objects.filter(
            deleted__isnull=True,
            est_vivant=True,
        ).select_related("famille", "famille__village").order_by("prenom", "nom")
        if user is not None and getattr(user, "est_agent_saisie_limite", False):
            person_qs = person_qs.filter(created_by=user)
        self.fields["personne"].queryset = person_qs
        cotisation_qs = Cotisation.objects.select_related(
            "village", "famille", "famille__village"
        ).order_by("-annee", "-mois")
        if user is not None and getattr(user, "est_agent_saisie_limite", False):
            family_ids = person_qs.values_list("famille_id", flat=True)
            village_ids = person_qs.values_list("famille__village_id", flat=True)
            cotisation_qs = cotisation_qs.filter(
                Q(est_generale=True)
                | Q(famille_id__in=family_ids)
                | Q(famille__isnull=True, village_id__in=village_ids)
            ).distinct()
        selected_cotisation_id = (
            self.data.get("cotisation")
            or self.initial.get("cotisation")
            or getattr(self.instance, "cotisation_id", None)
        )
        if selected_cotisation_id:
            try:
                selected_cotisation = cotisation_qs.get(id=selected_cotisation_id)
            except (Cotisation.DoesNotExist, ValueError, TypeError):
                selected_cotisation = None
            if selected_cotisation is not None:
                person_qs = person_qs.filter(
                    id__in=selected_cotisation.personnes_cibles.values("id")
                )
        self.fields["cotisation"].queryset = cotisation_qs
        self.fields["personne"].queryset = person_qs
        self.fields["compte_paiement"].queryset = ComptePaiement.objects.filter(
            est_actif=True
        ).order_by("ordre_affichage", "mode")
        self.fields["montant"].widget.attrs.update({"min": "0", "step": "0.01"})
        self.fields["nom_soumetteur"].required = False
        self.fields["telephone_soumetteur"].required = False
        self.fields["email_soumetteur"].required = False
        self._apply_field_classes()


class ComptePaiementForm(DashboardModelForm):
    class Meta:
        model = ComptePaiement
        fields = [
            "mode",
            "numero",
            "nom_titulaire",
            "qr_code",
            "instructions",
            "est_actif",
            "ordre_affichage",
        ]
        widgets = {
            "instructions": forms.Textarea(attrs={"rows": 4}),
            "ordre_affichage": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()


class CotisationPersonneForm(DashboardModelForm):
    class Meta:
        model = CotisationPersonne
        fields = [
            "montant_attendu",
            "notes",
        ]
        widgets = {
            "montant_attendu": forms.NumberInput(
                attrs={"min": "0", "step": "0.01"}
            ),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_field_classes()
