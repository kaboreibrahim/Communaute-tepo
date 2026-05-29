from django import forms
from django.db.models import Q
from django.utils import timezone

from Apps.cotisations.models import ComptePaiement, Cotisation, Paiement
from Apps.person.models import Person


FIELD_CLASSES = (
    "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm "
    "text-slate-800 outline-none transition focus:border-primary focus:ring-2 "
    "focus:ring-primary/10"
)


class PublicCotisationPaymentForm(forms.ModelForm):
    class Meta:
        model = Paiement
        fields = [
            "telephone_soumetteur",
            "personne",
            "cotisation",
            "montant",
            "date_paiement",
            "mode_paiement",
            "compte_paiement",
            "reference_transaction",
            "recu",
            "notes",
        ]
        widgets = {
            "telephone_soumetteur": forms.TextInput(
                attrs={
                    "class": FIELD_CLASSES,
                    "placeholder": "Numero ayant servi pour la transaction",
                    "inputmode": "tel",
                    "autocomplete": "tel",
                }
            ),
            "personne": forms.Select(attrs={"class": FIELD_CLASSES}),
            "cotisation": forms.Select(attrs={"class": FIELD_CLASSES}),
            "montant": forms.NumberInput(
                attrs={
                    "class": FIELD_CLASSES,
                    "min": "0",
                    "step": "0.01",
                    "placeholder": "Montant verse",
                }
            ),
            "date_paiement": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": FIELD_CLASSES,
                }
            ),
            "mode_paiement": forms.Select(attrs={"class": FIELD_CLASSES}),
            "compte_paiement": forms.Select(attrs={"class": FIELD_CLASSES}),
            "reference_transaction": forms.TextInput(
                attrs={
                    "class": FIELD_CLASSES,
                    "placeholder": "Numero de transaction ou reference du depot",
                }
            ),
            "recu": forms.ClearableFileInput(
                attrs={
                    "class": "hidden",
                    "accept": "image/*",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": FIELD_CLASSES,
                    "rows": 5,
                    "placeholder": "Informations utiles pour l'administration...",
                }
            ),
        }
        labels = {
            "telephone_soumetteur": "Numero utilise pour la transaction",
            "personne": "Personne concernee",
            "cotisation": "Cotisation a regler",
            "montant": "Montant verse",
            "date_paiement": "Date du paiement",
            "mode_paiement": "Mode de paiement",
            "compte_paiement": "Numero / compte utilise",
            "reference_transaction": "Reference du depot",
            "recu": "Capture ou recu",
            "notes": "Commentaire",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        person_qs = (
            Person.objects.filter(
                deleted__isnull=True,
                est_vivant=True,
            )
            .select_related("famille", "famille__village")
            .order_by("prenom", "nom")
        )
        cotisation_qs = Cotisation.objects.filter(
            statut="ouverte"
        ).select_related(
            "village",
            "famille",
            "famille__village",
        ).order_by("-annee", "-mois", "-date_creation")
        selected_person_id = (
            self.data.get("personne")
            or self.initial.get("personne")
            or getattr(self.instance, "personne_id", None)
        )
        selected_person = None
        if selected_person_id:
            try:
                selected_person = person_qs.get(id=selected_person_id)
            except (Person.DoesNotExist, ValueError, TypeError):
                selected_person = None

        if selected_person is not None:
            cotisation_qs = cotisation_qs.filter(
                Q(est_generale=True)
                | Q(famille_id=selected_person.famille_id)
                | Q(famille__isnull=True, village_id=selected_person.famille.village_id)
            ).distinct()

        self.fields["personne"].queryset = person_qs
        self.fields["cotisation"].queryset = cotisation_qs
        self.fields["cotisation"].empty_label = "Choisissez une cotisation ouverte"
        self.fields["personne"].empty_label = "Choisissez la personne concernee"
        self.fields["compte_paiement"].queryset = ComptePaiement.objects.filter(
            est_actif=True
        ).order_by("ordre_affichage", "mode", "nom_titulaire")
        self.fields["compte_paiement"].required = False
        self.fields["notes"].required = False
        self.fields["reference_transaction"].required = False
        self.fields["recu"].required = False
        self.fields["date_paiement"].initial = timezone.localdate()

    def clean_telephone_soumetteur(self):
        value = (self.cleaned_data.get("telephone_soumetteur") or "").strip()
        if not value:
            raise forms.ValidationError(
                "Le numero utilise pour la transaction est obligatoire."
            )
        return value

    def clean_reference_transaction(self):
        return (self.cleaned_data.get("reference_transaction") or "").strip()

    def clean_notes(self):
        return (self.cleaned_data.get("notes") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        mode = cleaned_data.get("mode_paiement")
        compte = cleaned_data.get("compte_paiement")
        reference = cleaned_data.get("reference_transaction")
        recu = cleaned_data.get("recu")

        if mode and mode != "espece" and not compte:
            self.add_error(
                "compte_paiement",
                "Choisissez le numero ou compte utilise pour votre depot.",
            )
        if mode in {"wave", "orange_money", "moov", "mtn", "virement"} and not (
            reference or recu
        ):
            raise forms.ValidationError(
                "Ajoutez au minimum une reference de transaction ou un recu pour faciliter la verification."
            )
        return cleaned_data

    def save(self, commit=True):
        paiement = super().save(commit=False)
        if paiement.mode_paiement == "espece":
            paiement.compte_paiement = None
        paiement.nom_soumetteur = paiement.personne.nom_complet
        paiement.email_soumetteur = (paiement.personne.email or "").strip()
        paiement.est_soumission_publique = True
        paiement.statut_validation = "pending"
        paiement.enregistre_par = None
        paiement.valide_par = None
        paiement.date_validation = None

        if commit:
            paiement.save()
            self.save_m2m()
        return paiement
