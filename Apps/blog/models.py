import math
import os
import re
import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from simple_history.models import HistoricalRecords


class Categorie(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField("Nom", max_length=100, unique=True)
    slug = models.SlugField("Slug", max_length=120, unique=True, blank=True)
    description = models.TextField("Description", blank=True)
    couleur = models.CharField("Couleur hex", max_length=7, default="#00613a")
    ordre = models.PositiveIntegerField("Ordre d'affichage", default=0)
    date_creation = models.DateTimeField("Date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Catégorie blog"
        verbose_name_plural = "Catégories blog"
        ordering = ["ordre", "nom"]

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    @property
    def nombre_articles(self):
        return self.articles.filter(deleted__isnull=True, statut=Article.STATUT_PUBLIE).count()


class Tag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField("Nom", max_length=50, unique=True)
    slug = models.SlugField("Slug", max_length=60, unique=True, blank=True)
    date_creation = models.DateTimeField("Date de création", auto_now_add=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["nom"]

    def __str__(self):
        return self.nom

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)

    @property
    def nombre_articles(self):
        return self.articles.filter(deleted__isnull=True, statut=Article.STATUT_PUBLIE).count()


def _upload_couverture(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"blog/couvertures/{instance.id}{ext}"


def _upload_og_image(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f"blog/og/{instance.id}_og{ext}"


class Article(SafeDeleteModel):
    STATUT_BROUILLON = "brouillon"
    STATUT_PUBLIE = "publie"
    STATUT_PLANIFIE = "planifie"
    STATUT_ARCHIVE = "archive"
    STATUT_CHOICES = [
        (STATUT_BROUILLON, "Brouillon"),
        (STATUT_PUBLIE, "Publié"),
        (STATUT_PLANIFIE, "Planifié"),
        (STATUT_ARCHIVE, "Archivé"),
    ]

    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    titre = models.CharField("Titre", max_length=255)
    slug = models.SlugField("Slug URL", max_length=280, unique=True, blank=True)
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Auteur",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles_blog",
    )
    categorie = models.ForeignKey(
        Categorie,
        verbose_name="Catégorie",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="articles",
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name="Tags",
        blank=True,
        related_name="articles",
    )
    image_couverture = models.ImageField(
        "Image de couverture",
        upload_to=_upload_couverture,
        blank=True,
        null=True,
    )
    extrait = models.TextField(
        "Extrait / Résumé",
        max_length=500,
        blank=True,
        help_text="Résumé court affiché dans la liste (max 500 caractères). Généré automatiquement si vide.",
    )
    contenu = models.TextField("Contenu de l'article")
    statut = models.CharField(
        "Statut",
        max_length=20,
        choices=STATUT_CHOICES,
        default=STATUT_BROUILLON,
        db_index=True,
    )
    date_publication = models.DateTimeField(
        "Date de publication",
        null=True,
        blank=True,
        db_index=True,
    )
    vues = models.PositiveIntegerField("Nombre de vues", default=0)
    featured = models.BooleanField("Article mis en avant", default=False)
    meta_title = models.CharField("Meta titre SEO", max_length=70, blank=True)
    meta_description = models.CharField("Meta description SEO", max_length=160, blank=True)
    og_image = models.ImageField(
        "Image Open Graph",
        upload_to=_upload_og_image,
        blank=True,
        null=True,
        help_text="Image pour le partage sur les réseaux sociaux (1200×630 recommandé)",
    )
    date_creation = models.DateTimeField("Date de création", auto_now_add=True)
    date_maj = models.DateTimeField("Dernière modification", auto_now=True)

    history = HistoricalRecords(
        table_name="blog_article_history",
        history_id_field=models.UUIDField(default=uuid.uuid4),
    )

    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"
        ordering = ["-date_publication", "-date_creation"]

    def __str__(self):
        return self.titre

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titre)
            slug = base
            counter = 1
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        if not self.extrait and self.contenu:
            text = re.sub(r"<[^>]+>", "", self.contenu)
            self.extrait = text[:400].strip()
        super().save(*args, **kwargs)
        self._process_image()

    def _process_image(self):
        if not self.image_couverture:
            return
        try:
            from PIL import Image as PILImage
            path = self.image_couverture.path
            with PILImage.open(path) as img:
                w, h = img.size
                max_w = 1200
                if w > max_w:
                    ratio = max_w / w
                    img = img.resize((max_w, int(h * ratio)), PILImage.LANCZOS)
                    fmt = img.format or "JPEG"
                    img.save(path, format=fmt, quality=85, optimize=True)
        except Exception:
            pass

    @property
    def est_publie(self):
        return self.statut == self.STATUT_PUBLIE

    @property
    def temps_lecture(self):
        text = re.sub(r"<[^>]+>", "", self.contenu or "")
        words = len(text.split())
        return max(1, math.ceil(words / 200))

    @property
    def nombre_commentaires(self):
        return self.commentaires.filter(approuve=True, deleted__isnull=True).count()

    @property
    def nombre_likes(self):
        return self.likes.count()

    def incrementer_vues(self):
        Article.objects.filter(pk=self.pk).update(vues=models.F("vues") + 1)

    @property
    def meta_title_effective(self):
        return self.meta_title or self.titre

    @property
    def meta_description_effective(self):
        return self.meta_description or self.extrait


class Commentaire(SafeDeleteModel):
    _safedelete_policy = SOFT_DELETE_CASCADE

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(
        Article,
        verbose_name="Article",
        on_delete=models.CASCADE,
        related_name="commentaires",
    )
    parent = models.ForeignKey(
        "self",
        verbose_name="Réponse à",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="reponses",
    )
    auteur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Auteur (membre)",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commentaires_blog",
    )
    auteur_nom = models.CharField("Nom (visiteur)", max_length=100, blank=True)
    auteur_email = models.EmailField("Email (visiteur)", blank=True)
    contenu = models.TextField("Commentaire")
    approuve = models.BooleanField("Approuvé", default=False)
    date_creation = models.DateTimeField("Date", auto_now_add=True)
    date_maj = models.DateTimeField("Modifié le", auto_now=True)

    class Meta:
        verbose_name = "Commentaire"
        verbose_name_plural = "Commentaires"
        ordering = ["date_creation"]

    def __str__(self):
        nom = self.auteur.get_full_name() if self.auteur else self.auteur_nom
        return f"Commentaire de {nom} sur «{self.article.titre}»"

    @property
    def nom_affiche(self):
        if self.auteur:
            return self.auteur.get_full_name() or self.auteur.username
        return self.auteur_nom or "Visiteur"

    @property
    def initiales(self):
        parts = self.nom_affiche.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.nom_affiche[:2].upper()


class Like(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    article = models.ForeignKey(
        Article,
        verbose_name="Article",
        on_delete=models.CASCADE,
        related_name="likes",
    )
    utilisateur = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Utilisateur",
        on_delete=models.CASCADE,
        related_name="likes_blog",
    )
    date_creation = models.DateTimeField("Date", auto_now_add=True)

    class Meta:
        verbose_name = "Like"
        verbose_name_plural = "Likes"
        unique_together = [("article", "utilisateur")]

    def __str__(self):
        return f"{self.utilisateur} → {self.article.titre}"


class Newsletter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("Email", unique=True)
    nom = models.CharField("Nom", max_length=100, blank=True)
    confirme = models.BooleanField("Confirmé", default=True)
    token = models.UUIDField("Token", default=uuid.uuid4, unique=True)
    date_inscription = models.DateTimeField("Date d'inscription", auto_now_add=True)
    actif = models.BooleanField("Actif", default=True)

    class Meta:
        verbose_name = "Abonné newsletter"
        verbose_name_plural = "Abonnés newsletter"
        ordering = ["-date_inscription"]

    def __str__(self):
        return self.email
