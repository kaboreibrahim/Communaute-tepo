import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from Apps.families.models import Family
from Apps.person.models import Person
from Apps.villages.models import Village


MONTH_CHOICES = [
    (1, "Janvier"),
    (2, "Fevrier"),
    (3, "Mars"),
    (4, "Avril"),
    (5, "Mai"),
    (6, "Juin"),
    (7, "Juillet"),
    (8, "Aout"),
    (9, "Septembre"),
    (10, "Octobre"),
    (11, "Novembre"),
    (12, "Decembre"),
]

PAYMENT_MODE_CHOICES = [
    ("wave", "Wave"),
    ("orange_money", "Orange Money"),
    ("moov", "Moov"),
    ("mtn", "MTN"),
    ("virement", "Virement"),
    ("espece", "Espece"),
]

VALIDATION_CHOICES = [
    ("pending", "En attente"),
    ("approved", "Valide"),
    ("rejected", "Refuse"),
]

COTISATION_STATUS_CHOICES = [
    ("ouverte", "Ouverte"),
    ("fermee", "Fermee"),
]

PERSON_TRACKING_STATUS_LABELS = {
    "unpaid": "Aucun paiement",
    "pending": "En attente",
    "retry": "A reprendre",
    "partiel": "Partiel",
    "solde": "Solde",
    "versement": "Versement enregistre",
}


def compute_remaining_amount(expected_amount, paid_amount):
    if expected_amount is None:
        return None
    paid_amount = paid_amount or Decimal("0.00")
    return max(expected_amount - paid_amount, Decimal("0.00"))


def resolve_person_tracking_status(
    expected_amount,
    paid_amount,
    pending_count=0,
    rejected_count=0,
):
    paid_amount = paid_amount or Decimal("0.00")
    if paid_amount > 0:
        if expected_amount is None:
            return "versement"
        if paid_amount >= expected_amount:
            return "solde"
        return "partiel"
    if pending_count:
        return "pending"
    if rejected_count:
        return "retry"
    return "unpaid"


def upload_receipt(instance, filename):
    ext = filename.split(".")[-1]
    payment_id = instance.id or uuid.uuid4()
    return (
        f"cotisations/paiements/{instance.cotisation.annee}/"
        f"{instance.cotisation.mois:02d}/{payment_id}.{ext}"
    )


def upload_qr_code(instance, filename):
    ext = filename.split(".")[-1]
    account_id = instance.id or uuid.uuid4()
    return f"cotisations/comptes/{account_id}.{ext}"


class ComptePaiement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mode = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES,
        verbose_name="Mode de paiement",
    )
    numero = models.CharField(max_length=100, verbose_name="Numero / reference")
    nom_titulaire = models.CharField(max_length=160, verbose_name="Nom du titulaire")
    qr_code = models.ImageField(
        upload_to=upload_qr_code,
        blank=True,
        null=True,
        verbose_name="QR code",
    )
    instructions = models.TextField(blank=True, default="", verbose_name="Instructions")
    est_actif = models.BooleanField(default=True, verbose_name="Compte actif")
    ordre_affichage = models.PositiveIntegerField(default=0, verbose_name="Ordre d'affichage")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ordre_affichage", "mode", "nom_titulaire"]
        verbose_name = "Compte de paiement"
        verbose_name_plural = "Comptes de paiement"

    def __str__(self):
        return f"{self.get_mode_display()} - {self.numero}"

    @property
    def label_court(self):
        return f"{self.get_mode_display()} - {self.nom_titulaire}"


class Cotisation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mois = models.PositiveSmallIntegerField(choices=MONTH_CHOICES)
    annee = models.PositiveIntegerField(db_index=True)
    est_generale = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Cotisation generale",
    )
    village = models.ForeignKey(
        Village,
        on_delete=models.CASCADE,
        related_name="cotisations",
        null=True,
        blank=True,
    )
    famille = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name="cotisations",
        null=True,
        blank=True,
    )
    description = models.TextField(blank=True, default="")
    statut = models.CharField(
        max_length=20,
        choices=COTISATION_STATUS_CHOICES,
        default="ouverte",
        db_index=True,
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-annee", "-mois", "village__nom", "famille__nom_famille"]
        verbose_name = "Cotisation"
        verbose_name_plural = "Cotisations"
        indexes = [
            models.Index(fields=["annee", "mois"], name="idx_cotisation_periode"),
            models.Index(fields=["statut"], name="idx_cotisation_statut"),
            models.Index(fields=["est_generale"], name="idx_cotisation_general"),
        ]

    def __str__(self):
        return f"{self.periode_label} - {self.cible_label}"

    def clean(self):
        errors = {}

        if self.est_generale:
            self.village = None
            self.famille = None
        elif not self.village and not self.famille:
            errors["village"] = "Selectionnez au moins un village ou une famille."

        if self.famille:
            if self.village and self.famille.village_id != self.village_id:
                errors["famille"] = (
                    "La famille selectionnee doit appartenir au village choisi."
                )
            elif not self.village:
                self.village = self.famille.village

        qs = self.__class__.objects.filter(
            mois=self.mois,
            annee=self.annee,
            village_id=self.village_id,
            famille_id=self.famille_id,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            errors["mois"] = (
                "Une cotisation existe deja pour cette periode et cette cible."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def periode_label(self):
        return f"{self.get_mois_display()} {self.annee}"

    @property
    def cible_label(self):
        if self.est_generale:
            return "Cotisation generale - toutes les personnes"
        if self.famille_id:
            return f"Famille {self.famille.nom_famille} ({self.famille.village.nom})"
        if self.village_id:
            return f"Village {self.village.nom}"
        return "Communaute"

    @property
    def personnes_cibles(self):
        qs = Person.objects.filter(deleted__isnull=True, est_vivant=True)
        if self.famille_id:
            qs = qs.filter(famille_id=self.famille_id)
        elif self.village_id:
            qs = qs.filter(famille__village_id=self.village_id)
        return qs.select_related("famille", "famille__village").order_by("prenom", "nom")

    @property
    def nombre_personnes_cibles(self):
        return self.personnes_cibles.count()

    @property
    def paiements_valides(self):
        return self.paiements.filter(statut_validation="approved")

    @property
    def total_collecte(self):
        total = self.paiements_valides.aggregate(total=Sum("montant"))["total"]
        return total or Decimal("0.00")

    @property
    def total_attendu(self):
        total = self.suivis_personnes.aggregate(total=Sum("montant_attendu"))["total"]
        return total or Decimal("0.00")

    @property
    def reste_global(self):
        return compute_remaining_amount(self.total_attendu, self.total_collecte)

    @property
    def nombre_montants_attendus(self):
        return self.suivis_personnes.filter(montant_attendu__isnull=False).count()

    @property
    def nombre_payeurs(self):
        return (
            self.paiements_valides.values("personne_id").distinct().count()
        )

    @property
    def personnes_sans_paiement(self):
        paid_ids = self.paiements_valides.values_list("personne_id", flat=True)
        return self.personnes_cibles.exclude(id__in=paid_ids)

    @property
    def est_en_retard(self):
        today = timezone.localdate()
        if self.statut != "ouverte":
            return False
        return (self.annee, self.mois) < (today.year, today.month)


class CotisationPersonne(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cotisation = models.ForeignKey(
        Cotisation,
        on_delete=models.CASCADE,
        related_name="suivis_personnes",
        verbose_name="Cotisation",
    )
    personne = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="suivis_cotisation",
        verbose_name="Personne",
    )
    montant_attendu = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Montant attendu",
    )
    notes = models.TextField(blank=True, default="", verbose_name="Notes")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "-cotisation__annee",
            "-cotisation__mois",
            "personne__prenom",
            "personne__nom",
        ]
        verbose_name = "Suivi de cotisation par personne"
        verbose_name_plural = "Suivis de cotisation par personne"
        constraints = [
            models.UniqueConstraint(
                fields=["cotisation", "personne"],
                name="uq_cotisation_personne_suivi",
            ),
        ]
        indexes = [
            models.Index(fields=["cotisation", "personne"], name="idx_suivi_scope"),
            models.Index(fields=["personne"], name="idx_suivi_personne"),
        ]

    def __str__(self):
        return f"{self.personne.nom_complet} - {self.cotisation.periode_label}"

    def clean(self):
        errors = {}

        if self.montant_attendu is not None and self.montant_attendu <= 0:
            errors["montant_attendu"] = (
                "Le montant attendu doit etre strictement positif."
            )

        if self.personne_id and not self.personne.est_vivant:
            errors["personne"] = (
                "Impossible de suivre une cotisation pour une personne decedee."
            )

        if self.personne_id and self.cotisation_id:
            if self.cotisation.famille_id and self.personne.famille_id != self.cotisation.famille_id:
                errors["personne"] = (
                    "Cette personne n'appartient pas a la famille ciblee."
                )
            elif (
                self.cotisation.village_id
                and self.personne.famille.village_id != self.cotisation.village_id
            ):
                errors["personne"] = (
                    "Cette personne n'appartient pas au village cible."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def paiements_queryset(self):
        return self.cotisation.paiements.filter(personne=self.personne)

    @property
    def paiements_valides(self):
        return self.paiements_queryset.filter(statut_validation="approved")

    @property
    def total_paye(self):
        total = self.paiements_valides.aggregate(total=Sum("montant"))["total"]
        return total or Decimal("0.00")

    @property
    def reste_a_payer(self):
        return compute_remaining_amount(self.montant_attendu, self.total_paye)

    @property
    def statut_suivi(self):
        return resolve_person_tracking_status(
            self.montant_attendu,
            self.total_paye,
            pending_count=self.paiements_queryset.filter(
                statut_validation="pending"
            ).count(),
            rejected_count=self.paiements_queryset.filter(
                statut_validation="rejected"
            ).count(),
        )

    @property
    def statut_suivi_label(self):
        return PERSON_TRACKING_STATUS_LABELS[self.statut_suivi]


class Paiement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    personne = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="paiements_cotisation",
        verbose_name="Personne",
    )
    cotisation = models.ForeignKey(
        Cotisation,
        on_delete=models.CASCADE,
        related_name="paiements",
        verbose_name="Cotisation",
    )
    compte_paiement = models.ForeignKey(
        ComptePaiement,
        on_delete=models.SET_NULL,
        related_name="paiements",
        null=True,
        blank=True,
        verbose_name="Compte de destination",
    )
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    mode_paiement = models.CharField(
        max_length=20,
        choices=PAYMENT_MODE_CHOICES,
        verbose_name="Mode de paiement",
    )
    reference_transaction = models.CharField(
        max_length=120,
        blank=True,
        default="",
        verbose_name="Reference de transaction",
    )
    recu = models.ImageField(
        upload_to=upload_receipt,
        blank=True,
        null=True,
        verbose_name="Recu",
    )
    est_soumission_publique = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Soumission publique",
    )
    nom_soumetteur = models.CharField(
        max_length=160,
        blank=True,
        default="",
        verbose_name="Nom du soumetteur",
    )
    telephone_soumetteur = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Telephone du soumetteur",
    )
    email_soumetteur = models.EmailField(
        blank=True,
        default="",
        verbose_name="Email du soumetteur",
    )
    statut_validation = models.CharField(
        max_length=20,
        choices=VALIDATION_CHOICES,
        default="approved",
        db_index=True,
        verbose_name="Statut de validation",
    )
    date_paiement = models.DateField(default=timezone.localdate)
    notes = models.TextField(blank=True, default="")
    enregistre_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="paiements_enregistres",
        null=True,
        blank=True,
        verbose_name="Enregistre par",
    )
    valide_par = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="paiements_cotisation_valides",
        null=True,
        blank=True,
        verbose_name="Valide par",
    )
    date_validation = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_paiement", "-date_creation"]
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        indexes = [
            models.Index(fields=["personne", "cotisation"], name="idx_paiement_scope"),
            models.Index(fields=["statut_validation"], name="idx_paiement_validation"),
            models.Index(fields=["mode_paiement"], name="idx_paiement_mode"),
        ]

    def __str__(self):
        return (
            f"{self.personne.nom_complet} - {self.cotisation.periode_label} "
            f"- {self.montant}"
        )

    def clean(self):
        errors = {}

        if self.montant is None or self.montant <= 0:
            errors["montant"] = "Le montant doit etre strictement positif."

        if self.cotisation_id and self.personne_id:
            if not self.personne.est_vivant:
                errors["personne"] = "Impossible d'enregistrer un paiement pour une personne decedee."
            if self.cotisation.famille_id and self.personne.famille_id != self.cotisation.famille_id:
                errors["personne"] = (
                    "Cette personne n'appartient pas a la famille ciblee."
                )
            elif (
                self.cotisation.village_id
                and self.personne.famille.village_id != self.cotisation.village_id
            ):
                errors["personne"] = (
                    "Cette personne n'appartient pas au village cible."
                )

        if (
            self.compte_paiement_id
            and self.mode_paiement
            and self.compte_paiement.mode != self.mode_paiement
        ):
            errors["compte_paiement"] = (
                "Le compte de destination doit correspondre au mode selectionne."
            )
        if self.est_soumission_publique:
            if not self.nom_soumetteur.strip():
                errors["nom_soumetteur"] = (
                    "Le nom du soumetteur est obligatoire pour une demande publique."
                )
            if not self.telephone_soumetteur.strip():
                errors["telephone_soumetteur"] = (
                    "Le telephone du soumetteur est obligatoire pour une demande publique."
                )
            if self.mode_paiement != "espece" and not self.compte_paiement_id:
                errors["compte_paiement"] = (
                    "Choisissez le numero ou compte de destination utilise pour le depot."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.statut_validation == "approved" and not self.date_validation:
            self.date_validation = timezone.now()
        elif self.statut_validation != "approved":
            self.date_validation = None
            self.valide_par = None
        self.full_clean()
        super().save(*args, **kwargs)
        if self.cotisation_id and self.personne_id:
            CotisationPersonne.objects.get_or_create(
                cotisation=self.cotisation,
                personne=self.personne,
            )

    @property
    def est_valide(self):
        return self.statut_validation == "approved"

    @property
    def suivi_personne(self):
        if not self.cotisation_id or not self.personne_id:
            return None
        return CotisationPersonne.objects.filter(
            cotisation=self.cotisation,
            personne=self.personne,
        ).first()
