import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def upload_to_public_person_submission(instance, filename):
    ext = filename.split('.')[-1]
    token = uuid.uuid4().hex
    return f"website/person_submissions/{token}.{ext}"


def upload_to_accueil_image(instance, filename):
    ext = filename.split('.')[-1]
    token = uuid.uuid4().hex
    return f"website/accueil/{instance.section}/{token}.{ext}"


class AccueilImage(models.Model):
    SECTION_CHOICES = [
        ("hero", "Hero"),
        ("about", "A propos"),
    ]

    section = models.CharField(
        max_length=20,
        choices=SECTION_CHOICES,
        default="hero",
        db_index=True,
    )
    titre = models.CharField(max_length=200, blank=True, default="")
    sous_titre = models.CharField(max_length=255, blank=True, default="")
    texte_alt = models.CharField(max_length=255, blank=True, default="")
    image = models.ImageField(
        upload_to=upload_to_accueil_image,
        blank=True,
        null=True,
    )
    image_url = models.URLField(blank=True, default="")
    ordre = models.PositiveIntegerField(default=0, db_index=True)
    est_active = models.BooleanField(default=True, db_index=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["section", "ordre", "-date_creation"]
        verbose_name = "Image d'accueil"
        verbose_name_plural = "Images d'accueil"

    def __str__(self):
        label = self.titre or self.texte_alt or "Image"
        return f"{self.get_section_display()} - {label}"

    def clean(self):
        super().clean()
        if not self.image and not self.image_url:
            raise ValidationError(
                "Ajoutez un fichier image ou renseignez une URL d'image."
            )

    @property
    def source_url(self):
        if self.image:
            try:
                return self.image.url
            except Exception:
                pass
        return self.image_url


class PublicPersonSubmission(models.Model):
    VALIDATION_CHOICES = [
        ("pending", "En attente"),
        ("approved", "Approuvee"),
        ("rejected", "Refusee"),
    ]

    GENRE_CHOICES = [
        ("M", "Masculin"),
        ("F", "Feminin"),
    ]

    SITUATION_CHOICES = [
        ("celibataire", "Celibataire"),
        ("marie", "Marie(e)"),
        ("divorce", "Divorce(e)"),
        ("veuf", "Veuf / Veuve"),
    ]

    RESIDENCE_CHOICES = [
        ("village", "Reside au village"),
        ("ci", "Cote d'Ivoire (hors village)"),
        ("diaspora", "Diaspora (hors CI)"),
        ("inconnu", "Inconnu"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    surnom = models.CharField(max_length=100, blank=True, default="")
    genre = models.CharField(max_length=1, choices=GENRE_CHOICES)
    date_naissance = models.DateField(null=True, blank=True)
    lieu_naissance = models.CharField(max_length=200, blank=True, default="")
    nationalite = models.CharField(max_length=100, default="Ivoirienne")
    numero_cni = models.CharField(max_length=50, blank=True, default="")
    profession = models.CharField(max_length=150, blank=True, default="")
    photo = models.ImageField(
        upload_to=upload_to_public_person_submission,
        blank=True,
        null=True,
    )

    situation_matrimoniale = models.CharField(
        max_length=20,
        choices=SITUATION_CHOICES,
        default="celibataire",
    )
    est_vivant = models.BooleanField(default=True)
    date_deces = models.DateField(null=True, blank=True)

    telephone = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    type_residence = models.CharField(
        max_length=20,
        choices=RESIDENCE_CHOICES,
        default="village",
    )
    lieu_residence = models.CharField(max_length=200, blank=True, default="")

    famille = models.ForeignKey(
        "families.Family",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="public_person_submissions",
    )
    pere = models.ForeignKey(
        "person.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="public_submissions_as_father",
        limit_choices_to={"genre": "M"},
    )
    mere = models.ForeignKey(
        "person.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="public_submissions_as_mother",
        limit_choices_to={"genre": "F"},
    )
    conjoint = models.ForeignKey(
        "person.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="public_submissions_as_spouse",
    )
    pere_nom_libre = models.CharField(max_length=200, blank=True, default="")
    mere_nom_libre = models.CharField(max_length=200, blank=True, default="")
    conjoint_nom_libre = models.CharField(max_length=200, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    statut_validation = models.CharField(
        max_length=20,
        choices=VALIDATION_CHOICES,
        default="pending",
        db_index=True,
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="public_person_submissions_validated",
        null=True,
        blank=True,
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    personne_creee = models.ForeignKey(
        "person.Person",
        on_delete=models.SET_NULL,
        related_name="public_submission_sources",
        null=True,
        blank=True,
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_creation"]
        verbose_name = "Pre-inscription publique"
        verbose_name_plural = "Pre-inscriptions publiques"

    def __str__(self):
        return f"{self.nom_complet} ({self.get_statut_validation_display()})"

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}".strip()

    @property
    def village_nom(self):
        if self.famille_id and self.famille and self.famille.village_id:
            return self.famille.village.nom
        return "Non rattache"

    def as_form_source(self):
        return {
            "nom": self.nom,
            "prenom": self.prenom,
            "surnom": self.surnom,
            "genre": self.genre,
            "date_naissance": self.date_naissance.isoformat() if self.date_naissance else "",
            "lieu_naissance": self.lieu_naissance,
            "nationalite": self.nationalite,
            "numero_cni": self.numero_cni,
            "profession": self.profession,
            "situation_matrimoniale": self.situation_matrimoniale,
            "est_vivant": "on" if self.est_vivant else "",
            "date_deces": self.date_deces.isoformat() if self.date_deces else "",
            "telephone": self.telephone,
            "email": self.email,
            "type_residence": self.type_residence,
            "lieu_residence": self.lieu_residence,
            "famille_id": str(self.famille_id) if self.famille_id else "",
            "pere_id": str(self.pere_id) if self.pere_id else "",
            "pere_nom_libre": self.pere_nom_libre,
            "mere_id": str(self.mere_id) if self.mere_id else "",
            "mere_nom_libre": self.mere_nom_libre,
            "conjoint_id": str(self.conjoint_id) if self.conjoint_id else "",
            "conjoint_nom_libre": self.conjoint_nom_libre,
            "notes": self.notes,
        }

    def apply_form_data(self, data, files=None):
        from datetime import date

        def date_or_none(value):
            try:
                return date.fromisoformat(value) if value else None
            except (ValueError, TypeError):
                return None

        self.nom = data.get("nom", "").strip()
        self.prenom = data.get("prenom", "").strip()
        self.surnom = data.get("surnom", "").strip()
        self.genre = data.get("genre", "").strip()
        self.date_naissance = date_or_none(data.get("date_naissance"))
        self.lieu_naissance = data.get("lieu_naissance", "").strip()
        self.nationalite = data.get("nationalite", "Ivoirienne").strip()
        self.numero_cni = data.get("numero_cni", "").strip()
        self.profession = data.get("profession", "").strip()
        self.situation_matrimoniale = data.get(
            "situation_matrimoniale",
            "celibataire",
        )
        self.est_vivant = data.get("est_vivant") == "on"
        self.date_deces = date_or_none(data.get("date_deces"))
        self.telephone = data.get("telephone", "").strip()
        self.email = data.get("email", "").strip()
        self.type_residence = data.get("type_residence", "village")
        self.lieu_residence = data.get("lieu_residence", "").strip()
        self.famille_id = data.get("famille_id") or None
        self.pere_id = data.get("pere_id") or None
        self.pere_nom_libre = data.get("pere_nom_libre", "").strip()
        self.mere_id = data.get("mere_id") or None
        self.mere_nom_libre = data.get("mere_nom_libre", "").strip()
        self.conjoint_id = data.get("conjoint_id") or None
        self.conjoint_nom_libre = data.get("conjoint_nom_libre", "").strip()
        self.notes = data.get("notes", "").strip()

        if files and files.get("photo"):
            self.photo = files.get("photo")
