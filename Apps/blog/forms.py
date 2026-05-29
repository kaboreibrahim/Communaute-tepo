from django import forms
from django.utils import timezone

from .models import Article, Categorie, Commentaire, Newsletter, Tag

_INPUT = (
    "w-full rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm "
    "text-slate-800 outline-none transition focus:border-primary focus:ring-2 "
    "focus:ring-primary/10 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100"
)
_TEXTAREA = _INPUT + " resize-none"
_SELECT = _INPUT


class ArticleForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Tags",
    )

    class Meta:
        model = Article
        fields = [
            "titre",
            "extrait",
            "contenu",
            "categorie",
            "tags",
            "image_couverture",
            "statut",
            "date_publication",
            "featured",
            "meta_title",
            "meta_description",
            "og_image",
        ]
        widgets = {
            "titre": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Titre de l'article"}),
            "extrait": forms.Textarea(attrs={"class": _TEXTAREA, "rows": 3, "placeholder": "Résumé court (laissez vide pour génération automatique)"}),
            "contenu": forms.Textarea(attrs={"id": "contenu-editor", "class": _TEXTAREA, "rows": 20}),
            "categorie": forms.Select(attrs={"class": _SELECT}),
            "statut": forms.Select(attrs={"class": _SELECT}),
            "date_publication": forms.DateTimeInput(
                attrs={"class": _INPUT, "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "meta_title": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Meta titre SEO (max 70 car.)"}),
            "meta_description": forms.Textarea(attrs={"class": _TEXTAREA, "rows": 2, "placeholder": "Meta description SEO (max 160 car.)"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.date_publication:
            self.initial["date_publication"] = self.instance.date_publication.strftime("%Y-%m-%dT%H:%M")
        self.fields["categorie"].empty_label = "— Aucune catégorie —"
        self.fields["image_couverture"].required = False
        self.fields["og_image"].required = False


class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ["nom", "description", "couleur", "ordre"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Nom de la catégorie"}),
            "description": forms.Textarea(attrs={"class": _TEXTAREA, "rows": 3}),
            "couleur": forms.TextInput(attrs={"class": _INPUT, "type": "color"}),
            "ordre": forms.NumberInput(attrs={"class": _INPUT, "min": 0}),
        }


class TagForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["nom"]
        widgets = {
            "nom": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Nom du tag"}),
        }


class CommentaireForm(forms.ModelForm):
    class Meta:
        model = Commentaire
        fields = ["auteur_nom", "auteur_email", "contenu"]
        widgets = {
            "auteur_nom": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Votre nom *"}),
            "auteur_email": forms.EmailInput(attrs={"class": _INPUT, "placeholder": "Votre email (non publié)"}),
            "contenu": forms.Textarea(attrs={"class": _TEXTAREA, "rows": 4, "placeholder": "Votre commentaire..."}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields["auteur_nom"].required = False
            self.fields["auteur_nom"].widget = forms.HiddenInput()
            self.fields["auteur_email"].required = False
            self.fields["auteur_email"].widget = forms.HiddenInput()
        else:
            self.fields["auteur_nom"].required = True


class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = ["email", "nom"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": _INPUT, "placeholder": "Votre adresse email"}),
            "nom": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Votre prénom (optionnel)"}),
        }


class RechercheForm(forms.Form):
    q = forms.CharField(
        label="Recherche",
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": _INPUT, "placeholder": "Rechercher un article..."}),
    )
