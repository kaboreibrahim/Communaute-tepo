from django.conf            import settings
from django.core.exceptions import ValidationError
from django.db              import models
from django.db.models       import Q
from django.utils           import timezone
from safedelete.models      import SafeDeleteModel, SOFT_DELETE_CASCADE
from simple_history.models  import HistoricalRecords
from datetime               import date
import uuid

# ============================================================
# MODÈLE : Family
# ============================================================
 
class Family(SafeDeleteModel):
    """
    Famille recensée dans un village d'Olodio.
    Une famille regroupe un chef (père), ses épouses et ses enfants.
    """
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    id = models.UUIDField(
        "Identifiant unique",
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    nom_famille = models.CharField(
        "Nom de famille",
        max_length=100,
    )
    village = models.ForeignKey(
        'villages.Village',
        on_delete=models.CASCADE,
        related_name='familles',
        verbose_name="Village",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='families_created',
        verbose_name="Enregistrée par",
    )
    description = models.TextField(
        "Description",
        blank=True,
        default='',
    )
    date_creation = models.DateTimeField(
        "Date de création",
        auto_now_add=True,
    )
    date_maj = models.DateTimeField(
        "Dernière modification",
        auto_now=True,
    )
 
    history = HistoricalRecords(
        table_name='families_family_history',
        history_id_field=models.UUIDField(default=uuid.uuid4),
    )
 
    class Meta:
        verbose_name        = 'Famille'
        verbose_name_plural = 'Familles'
        ordering            = ['nom_famille']
        # Pas deux familles du même nom dans le même village
        constraints = [
            models.UniqueConstraint(
                fields=['nom_famille', 'village'],
                condition=models.Q(deleted__isnull=True),
                name='uq_famille_village_actif',
            )
        ]
 
    def __str__(self):
        return f"Famille {self.nom_famille} — {self.village}"

    def clean(self):
        if Family.objects.filter(
            nom_famille=self.nom_famille,
            village=self.village,
            deleted__isnull=True,
        ).exclude(pk=self.pk).exists():
            raise ValidationError({
                'nom_famille': "Une famille avec ce nom existe déjà dans ce village."
            })

    # ── Properties ───────────────────────────────────────────
 
    @property
    def chef(self):
        """
        Chef de famille = membre masculin sans père ni mère connu.
        En cas de plusieurs, retourne le plus âgé.
        """
        return self.membres.filter(
            est_chef_famille=True,
            deleted__isnull=True,
        ).order_by('date_creation', 'nom', 'prenom').first()
 
    @property
    def nombre_membres(self):
        return self.membres.filter(deleted__isnull=True).count()
 
    @property
    def nombre_vivants(self):
        return self.membres.filter(
            deleted__isnull=True,
            est_vivant=True,
        ).count()
 
    @property
    def nombre_hommes(self):
        return self.membres.filter(
            deleted__isnull=True,
            genre='M',
        ).count()
 
    @property
    def nombre_femmes(self):
        return self.membres.filter(
            deleted__isnull=True,
            genre='F',
        ).count()
 
    @property
    def nombre_diaspora(self):
        return self.membres.filter(
            deleted__isnull=True,
            type_residence='diaspora',
        ).count()
 
