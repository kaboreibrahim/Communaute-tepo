from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class TypeEvenement(models.Model):
    slug = models.SlugField(
        max_length=30,
        unique=True,
        help_text="Identifiant unique (ex: naissance, deces, mariage…)",
    )
    nom = models.CharField(max_length=100)
    icone = models.CharField(
        max_length=60,
        default="event_note",
        help_text="Nom de l'icone Material Icons",
    )
    couleur_fond = models.CharField(
        max_length=10,
        default="#F8FAFC",
        help_text="Couleur de fond du badge (hex)",
    )
    couleur_texte = models.CharField(
        max_length=10,
        default="#334155",
        help_text="Couleur du texte du badge (hex)",
    )
    est_communautaire = models.BooleanField(
        default=False,
        help_text="Cocher si ce type concerne la communaute (fete, reunion…)",
    )
    ordre = models.PositiveSmallIntegerField(
        default=0,
        help_text="Ordre d'affichage dans les listes et formulaires",
    )

    class Meta:
        ordering = ["ordre", "nom"]
        verbose_name = "Type d'evenement"
        verbose_name_plural = "Types d'evenement"

    def __str__(self):
        return self.nom


class Event(models.Model):
    VALIDATION_CHOICES = [
        ("pending", "En attente"),
        ("approved", "Approuve"),
        ("rejected", "Refuse"),
    ]

    type = models.ForeignKey(
        TypeEvenement,
        on_delete=models.PROTECT,
        related_name="evenements",
        verbose_name="Type d'evenement",
        null=True,
        blank=True,
    )
    titre = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    resume = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)
    date_evenement = models.DateField()
    lieu = models.CharField(max_length=200, blank=True)
    village = models.ForeignKey(
        "villages.Village",
        on_delete=models.SET_NULL,
        related_name="evenements",
        null=True,
        blank=True,
    )

    # Optionnel: certains evenements concernent une personne,
    # d'autres sont purement communautaires.
    personne = models.ForeignKey(
        "person.Person",
        on_delete=models.SET_NULL,
        related_name="evenements",
        null=True,
        blank=True,
    )

    # Informations utiles quand une annonce est soumise publiquement
    # depuis le portail citoyen sans compte admin.
    nom_contact = models.CharField(max_length=160, blank=True)
    telephone_contact = models.CharField(max_length=40, blank=True)
    email_contact = models.EmailField(blank=True)

    est_public = models.BooleanField(
        default=True,
        help_text="Visible sur la page d'accueil apres validation admin.",
    )
    statut_validation = models.CharField(
        max_length=20,
        choices=VALIDATION_CHOICES,
        default="pending",
        db_index=True,
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="evenements_valides",
        null=True,
        blank=True,
    )
    date_validation = models.DateTimeField(null=True, blank=True)

    photo = models.ImageField(
        upload_to="events/%Y/%m/",
        blank=True,
        null=True,
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_evenement", "-date_creation"]
        verbose_name = "Evenement"
        verbose_name_plural = "Evenements"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titre)
            slug = base
            counter = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("website:evenement-detail", kwargs={"pk": self.pk})

    def __str__(self):
        sujet = self.personne or self.titre
        type_label = self.type.nom if self.type_id else "Evenement"
        return f"{type_label} - {sujet} ({self.date_evenement})"

    @property
    def est_valide(self):
        return self.statut_validation == "approved"

    @property
    def publie_sur_accueil(self):
        return self.est_public and self.est_valide

    @property
    def est_evenement_communautaire(self):
        return self.type.est_communautaire if self.type_id else False

    @property
    def est_soumission_publique(self):
        return bool(
            self.nom_contact
            or self.telephone_contact
            or self.email_contact
        )

    @property
    def icone(self):
        return self.type.icone if self.type_id else "event_note"

    @property
    def lieu_affichage(self):
        if self.lieu:
            return self.lieu
        if self.village_id:
            return self.village.nom
        if self.personne_id and self.personne.famille_id:
            return self.personne.famille.village.nom
        return "Olodio"

    @property
    def resume_affichage(self):
        if self.resume:
            return self.resume
        if self.description:
            return self.description[:250]
        type_label = self.type.nom if self.type_id else "Evenement"
        if self.personne_id:
            return (
                f"{type_label} concernant {self.personne.nom_complet} "
                f"dans la communaute d'Olodio."
            )
        return f"{type_label} annonce pour la communaute d'Olodio."


class Notification(models.Model):
    evenement = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    destinataire = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications_evenements",
    )
    est_lue = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date_envoi"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return f"Notif -> {self.destinataire} : {self.evenement}"
