from django import forms
from .models import CategorieMedia, Media

IMAGES_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml']
VIDEO_TYPES = ['video/mp4', 'video/avi', 'video/quicktime', 'video/x-matroska', 'video/webm']
ALLOWED_TYPES = IMAGES_TYPES + VIDEO_TYPES

MAX_IMAGE_SIZE = 20 * 1024 * 1024   # 20 Mo
MAX_VIDEO_SIZE = 500 * 1024 * 1024  # 500 Mo


class MediaUploadForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['titre', 'type_media', 'fichier', 'miniature',
                  'categorie', 'description', 'duree']
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
                'placeholder': 'Titre du média',
            }),
            'type_media': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
            }),
            'fichier': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'fichier-input',
            }),
            'miniature': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'miniature-input',
                'accept': 'image/*',
            }),
            'categorie': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
                'rows': 3,
                'placeholder': 'Description (optionnel)',
            }),
            'duree': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
                'placeholder': 'Durée en secondes (pour les vidéos)',
                'min': 0,
            }),
        }

    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')
        if not fichier:
            raise forms.ValidationError("Veuillez sélectionner un fichier.")
        content_type = getattr(fichier, 'content_type', '')
        if content_type and content_type not in ALLOWED_TYPES:
            raise forms.ValidationError(
                f"Type de fichier non supporté : {content_type}. "
                "Utilisez JPEG, PNG, GIF, WebP, SVG, MP4, AVI, MOV, MKV ou WebM."
            )
        type_media = self.data.get('type_media', '')
        if type_media == Media.TYPE_IMAGE and fichier.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError(
                f"L'image est trop volumineuse (max {MAX_IMAGE_SIZE // (1024**2)} Mo)."
            )
        if type_media == Media.TYPE_VIDEO and fichier.size > MAX_VIDEO_SIZE:
            raise forms.ValidationError(
                f"La vidéo est trop volumineuse (max {MAX_VIDEO_SIZE // (1024**2)} Mo)."
            )
        return fichier


class MediaUpdateForm(forms.ModelForm):
    class Meta:
        model = Media
        fields = ['titre', 'categorie', 'description', 'miniature', 'duree']
        widgets = {
            'titre': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
            }),
            'categorie': forms.Select(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
                'rows': 4,
            }),
            'miniature': forms.FileInput(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm',
                'accept': 'image/*',
            }),
            'duree': forms.NumberInput(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
                'min': 0,
            }),
        }


class CategorieMediaForm(forms.ModelForm):
    class Meta:
        model = CategorieMedia
        fields = ['nom', 'description']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
                'placeholder': 'Nom de la catégorie',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full rounded-xl border border-slate-200 px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary/30 focus:border-primary outline-none',
                'rows': 3,
                'placeholder': 'Description (optionnel)',
            }),
        }
