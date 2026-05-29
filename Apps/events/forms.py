from django import forms
from django.utils import timezone

from Apps.person.models import Person
from Apps.villages.models import Village

from .models import Event


class DashboardEventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "titre",
            "type",
            "date_evenement",
            "resume",
            "description",
            "personne",
            "village",
            "lieu",
            "est_public",
            "photo",
        ]
        widgets = {
            "titre": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
                    "placeholder": "Ex : Reunion annuelle des chefs de village",
                }
            ),
            "type": forms.Select(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
                }
            ),
            "date_evenement": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
                }
            ),
            "resume": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": 250,
                    "class": "w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
                    "placeholder": "Resume bref pour la page d'accueil...",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 12,
                    "class": "w-full resize-none rounded-xl border border-slate-200 bg-transparent p-0 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-0 dark:border-slate-700 dark:text-slate-100",
                    "placeholder": "Renseignez le detail de l'annonce ici...",
                }
            ),
            "personne": forms.Select(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
                }
            ),
            "village": forms.Select(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
                }
            ),
            "lieu": forms.TextInput(
                attrs={
                    "class": "w-full rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100",
                    "placeholder": "Ex : Sous-prefecture d'Olodio",
                }
            ),
            "photo": forms.ClearableFileInput(
                attrs={
                    "class": "hidden",
                    "accept": "image/*",
                }
            ),
        }
        labels = {
            "titre": "Titre",
            "type": "Categorie",
            "date_evenement": "Date",
            "resume": "Resume court",
            "description": "Contenu complet",
            "personne": "Personne concernee",
            "village": "Village rattache",
            "lieu": "Lieu",
            "est_public": "Public",
            "photo": "Image de couverture",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["resume"].required = False
        self.fields["description"].required = False
        self.fields["personne"].required = False
        self.fields["village"].required = False
        self.fields["lieu"].required = False
        self.fields["photo"].required = False
        self.fields["est_public"].required = False
        self.fields["est_public"].initial = True
        self.fields["village"].empty_label = "Tous les villages"
        self.fields["personne"].empty_label = "Aucune personne specifique"
        self.fields["village"].queryset = Village.objects.filter(
            deleted__isnull=True
        ).order_by("nom")
        self.fields["personne"].queryset = (
            Person.objects.filter(
                deleted__isnull=True,
                famille__deleted__isnull=True,
                famille__village__deleted__isnull=True,
            )
            .select_related("famille__village")
            .order_by("prenom", "nom")
        )

    def clean_date_evenement(self):
        date_evenement = self.cleaned_data["date_evenement"]
        if date_evenement.year < 2000:
            raise forms.ValidationError("Choisissez une date plus recente.")
        return date_evenement

    def clean_resume(self):
        return (self.cleaned_data.get("resume") or "").strip()

    def clean_description(self):
        return (self.cleaned_data.get("description") or "").strip()

    def clean_titre(self):
        titre = (self.cleaned_data.get("titre") or "").strip()
        if not titre:
            raise forms.ValidationError("Le titre est obligatoire.")
        return titre

    def clean(self):
        cleaned_data = super().clean()
        resume = cleaned_data.get("resume", "")
        description = cleaned_data.get("description", "")

        if not resume and not description:
            raise forms.ValidationError(
                "Ajoutez au minimum un resume court ou une description detaillee."
            )
        return cleaned_data

    def save(self, commit=True, validator=None, publish=True):
        event = super().save(commit=False)
        if not event.resume:
            event.resume = event.resume_affichage[:250]
        if not event.village_id and event.personne_id and event.personne.famille_id:
            event.village = event.personne.famille.village

        if publish:
            event.statut_validation = "approved"
            event.valide_par = validator
            event.date_validation = timezone.now() if validator else None
        else:
            event.statut_validation = "pending"
            event.valide_par = None
            event.date_validation = None

        if commit:
            event.save()
            self.save_m2m()
        return event


class PublicEventSubmissionForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "nom_contact",
            "telephone_contact",
            "email_contact",
            "village",
            "type",
            "titre",
            "date_evenement",
            "lieu",
            "resume",
            "description",
            "photo",
        ]
        widgets = {
            "nom_contact": forms.TextInput(
                attrs={
                    "class": "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                    "placeholder": "Votre nom complet",
                }
            ),
            "telephone_contact": forms.TextInput(
                attrs={
                    "class": "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                    "placeholder": "+225 07 00 00 00 00",
                }
            ),
            "email_contact": forms.EmailInput(
                attrs={
                    "class": "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                    "placeholder": "nom@exemple.ci",
                }
            ),
            "village": forms.Select(
                attrs={
                    "class": "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                }
            ),
            "type": forms.Select(
                attrs={
                    "class": "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                }
            ),
            "titre": forms.TextInput(
                attrs={
                    "class": "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                    "placeholder": "Ex : Mariage de la famille Konan",
                }
            ),
            "date_evenement": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                }
            ),
            "lieu": forms.TextInput(
                attrs={
                    "class": "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                    "placeholder": "Place publique, cour familiale, eglise...",
                }
            ),
            "resume": forms.Textarea(
                attrs={
                    "rows": 3,
                    "maxlength": 250,
                    "class": "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                    "placeholder": "Resume bref qui pourra apparaitre dans le fil d'actualites...",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 7,
                    "class": "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                    "placeholder": "Donnez les details utiles de votre annonce pour l'administration.",
                }
            ),
            "photo": forms.ClearableFileInput(
                attrs={
                    "class": "hidden",
                    "accept": "image/*",
                }
            ),
        }
        labels = {
            "nom_contact": "Votre nom",
            "telephone_contact": "Telephone",
            "email_contact": "Email",
            "village": "Village",
            "type": "Categorie",
            "titre": "Titre de l'annonce",
            "date_evenement": "Date de l'evenement",
            "lieu": "Lieu",
            "resume": "Resume court",
            "description": "Description detaillee",
            "photo": "Photo ou affiche",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["village"].required = True
        self.fields["email_contact"].required = False
        self.fields["lieu"].required = False
        self.fields["resume"].required = False
        self.fields["description"].required = False
        self.fields["photo"].required = False
        self.fields["village"].queryset = Village.objects.filter(
            deleted__isnull=True
        ).order_by("nom")
        self.fields["village"].empty_label = "Choisissez votre village"

    def clean_nom_contact(self):
        nom_contact = (self.cleaned_data.get("nom_contact") or "").strip()
        if not nom_contact:
            raise forms.ValidationError("Votre nom est obligatoire.")
        return nom_contact

    def clean_telephone_contact(self):
        telephone = (self.cleaned_data.get("telephone_contact") or "").strip()
        if not telephone:
            raise forms.ValidationError("Le telephone de contact est obligatoire.")
        return telephone

    def clean_titre(self):
        titre = (self.cleaned_data.get("titre") or "").strip()
        if not titre:
            raise forms.ValidationError("Le titre de l'annonce est obligatoire.")
        return titre

    def clean_resume(self):
        return (self.cleaned_data.get("resume") or "").strip()

    def clean_description(self):
        return (self.cleaned_data.get("description") or "").strip()

    def clean(self):
        cleaned_data = super().clean()
        resume = cleaned_data.get("resume", "")
        description = cleaned_data.get("description", "")

        if not resume and not description:
            raise forms.ValidationError(
                "Ajoutez au minimum un resume court ou une description detaillee."
            )
        return cleaned_data

    def save(self, commit=True):
        event = super().save(commit=False)
        if not event.resume:
            event.resume = (event.description or "")[:250]
        event.est_public = True
        event.statut_validation = "pending"
        event.valide_par = None
        event.date_validation = None

        if commit:
            event.save()
            self.save_m2m()
        return event
