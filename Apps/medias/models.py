import os
import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from simple_history.models import HistoricalRecords


class CategorieMedia(models.Model):
    nom = models.CharField("Nom", max_length=100, unique=True)
    slug = models.SlugField("Slug", max_length=120, unique=True, blank=True)
    description = models.TextField("Description", blank=True)
    date_creation = models.DateTimeField("Date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Catégorie média"
        verbose_name_plural = "Catégories médias"
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    @property
    def nombre_medias(self):
        return self.medias.filter(deleted__isnull=True).count()


def _upload_to_media(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    folder = 'images' if instance.type_media == Media.TYPE_IMAGE else 'videos'
    return f"medias/{folder}/{instance.id}{ext}"


def _upload_to_miniature(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"medias/miniatures/{instance.id}{ext}"


class Media(SafeDeleteModel):
    TYPE_IMAGE = 'image'
    TYPE_VIDEO = 'video'
    TYPE_CHOICES = [
        (TYPE_IMAGE, 'Image'),
        (TYPE_VIDEO, 'Vidéo'),
    ]

    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(
        "Identifiant",
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    titre = models.CharField("Titre", max_length=200)
    type_media = models.CharField(
        "Type",
        max_length=10,
        choices=TYPE_CHOICES,
        db_index=True,
    )
    fichier = models.FileField("Fichier", upload_to=_upload_to_media)
    miniature = models.ImageField(
        "Miniature",
        upload_to=_upload_to_miniature,
        blank=True,
        help_text="Vignette pour les vidéos (optionnel)",
    )
    categorie = models.ForeignKey(
        CategorieMedia,
        verbose_name="Catégorie",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medias',
    )
    description = models.TextField("Description", blank=True)
    taille_fichier = models.BigIntegerField("Taille (octets)", default=0)
    largeur = models.IntegerField("Largeur (px)", null=True, blank=True)
    hauteur = models.IntegerField("Hauteur (px)", null=True, blank=True)
    duree = models.IntegerField("Durée (secondes)", null=True, blank=True)
    format_fichier = models.CharField("Format", max_length=20, blank=True)
    uploade_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Uploadé par",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medias_uploades',
    )
    date_creation = models.DateTimeField("Date d'ajout", auto_now_add=True)
    date_maj = models.DateTimeField("Dernière modification", auto_now=True)

    history = HistoricalRecords(
        table_name='medias_media_history',
        history_id_field=models.UUIDField(default=uuid.uuid4),
    )

    class Meta:
        verbose_name = "Média"
        verbose_name_plural = "Médias"
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.get_type_media_display()} – {self.titre}"

    def save(self, *args, **kwargs):
        if self.fichier and hasattr(self.fichier, 'size'):
            try:
                self.taille_fichier = self.fichier.size
            except Exception:
                pass
        if self.fichier and not self.format_fichier:
            ext = os.path.splitext(self.fichier.name)[1].lower().lstrip('.')
            self.format_fichier = ext.upper()
        super().save(*args, **kwargs)
        self._process_image()

    def _process_image(self):
        if self.type_media != self.TYPE_IMAGE or not self.fichier:
            return
        try:
            from PIL import Image as PILImage
            path = self.fichier.path
            with PILImage.open(path) as img:
                w, h = img.size
                max_w = 1920
                if w > max_w:
                    ratio = max_w / w
                    img = img.resize((max_w, int(h * ratio)), PILImage.LANCZOS)
                    fmt = img.format or 'JPEG'
                    img.save(path, format=fmt, quality=85, optimize=True)
                    w, h = img.size
                    size = os.path.getsize(path)
                    Media.objects.filter(pk=self.pk).update(
                        largeur=w, hauteur=h, taille_fichier=size,
                    )
                else:
                    Media.objects.filter(pk=self.pk).update(largeur=w, hauteur=h)
        except Exception:
            pass

    @property
    def est_image(self):
        return self.type_media == self.TYPE_IMAGE

    @property
    def est_video(self):
        return self.type_media == self.TYPE_VIDEO

    @property
    def taille_affichage(self):
        t = self.taille_fichier
        if t < 1024:
            return f"{t} o"
        if t < 1024 ** 2:
            return f"{t / 1024:.1f} Ko"
        if t < 1024 ** 3:
            return f"{t / 1024 ** 2:.1f} Mo"
        return f"{t / 1024 ** 3:.2f} Go"

    @property
    def dimensions_affichage(self):
        if self.largeur and self.hauteur:
            return f"{self.largeur} × {self.hauteur} px"
        return ""

    @property
    def duree_affichage(self):
        if not self.duree:
            return ""
        h = self.duree // 3600
        m = (self.duree % 3600) // 60
        s = self.duree % 60
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    @property
    def url_preview(self):
        if self.type_media == self.TYPE_IMAGE:
            return self.fichier.url if self.fichier else ''
        if self.miniature:
            return self.miniature.url
        return ''
