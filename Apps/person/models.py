 
from django.conf            import settings
from django.db              import models
from django.db.models       import Q
from django.utils           import timezone
from django.utils.text      import slugify
from safedelete.models      import SafeDeleteModel, SOFT_DELETE_CASCADE
from simple_history.models  import HistoricalRecords
from datetime               import date
import uuid
from Apps.families.models import Family
# ============================================================
# MODÈLE : Person
# ============================================================
 
def upload_photo_personne(instance, filename):
    """Chemin d'upload pour les photos de profil."""
    ext      = filename.split('.')[-1]
    filename = f"{instance.id}.{ext}"
    return f"familles/personnes/{instance.famille.village.nom}/{filename}"
 
 
class Person(SafeDeleteModel):
    """
    Personne recensée appartenant à une famille d'Olodio.
    Supporte les liens généalogiques (père, mère, conjoint)
    via des FK auto-référentielles.
    """
    _safedelete_policy = SOFT_DELETE_CASCADE
 
    # ── Choix ────────────────────────────────────────────────
 
    GENRE_CHOICES = [
        ('M', 'Masculin'),
        ('F', 'Féminin'),
    ]
 
    SITUATION_CHOICES = [
        ('celibataire', 'Célibataire'),
        ('marie',       'Marié(e)'),
        ('divorce',     'Divorcé(e)'),
        ('veuf',        'Veuf / Veuve'),
    ]
 
    RESIDENCE_CHOICES = [
        ('village',  'Réside au village'),
        ('ci',       "Côte d'Ivoire (hors village)"),
        ('diaspora', 'Diaspora (hors CI)'),
        ('inconnu',  'Inconnu'),
    ]
 
    # ── Clé primaire ─────────────────────────────────────────
 
    id = models.UUIDField(
        "Identifiant unique",
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    code = models.CharField(
        "Code",
        max_length=32,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
 
    # ── Identité ─────────────────────────────────────────────
 
    nom = models.CharField(
        "Nom",
        max_length=100,
    )
    prenom = models.CharField(
        "Prénom",
        max_length=100,
    )
    surnom = models.CharField(
        "Surnom",
        max_length=100,
        blank=True,
        default='',
    )
    genre = models.CharField(
        "Genre",
        max_length=1,
        choices=GENRE_CHOICES,
    )
    date_naissance = models.DateField(
        "Date de naissance",
        null=True,
        blank=True,
    )
    lieu_naissance = models.CharField(
        "Lieu de naissance",
        max_length=200,
        blank=True,
        default='',
    )
    nationalite = models.CharField(
        "Nationalité",
        max_length=100,
        default='Ivoirienne',
    )
    numero_cni = models.CharField(
        "Numéro CNI",
        max_length=50,
        blank=True,
        default='',
    )
    profession = models.CharField(
        "Profession",
        max_length=150,
        blank=True,
        default='',
    )
    photo = models.ImageField(
        "Photo",
        upload_to=upload_photo_personne,
        blank=True,
        null=True,
    )
 
    # ── Situation ────────────────────────────────────────────
 
    situation_matrimoniale = models.CharField(
        "Situation matrimoniale",
        max_length=20,
        choices=SITUATION_CHOICES,
        default='celibataire',
    )
    est_vivant = models.BooleanField(
        "Est vivant(e)",
        default=True,
    )
    date_deces = models.DateField(
        "Date de décès",
        null=True,
        blank=True,
    )
 
    # ── Contact & Résidence ──────────────────────────────────
 
    telephone = models.CharField(
        "Téléphone",
        max_length=20,
        blank=True,
        default='',
    )
    email = models.EmailField(
        "Email",
        blank=True,
        default='',
    )
    type_residence = models.CharField(
        "Type de résidence",
        max_length=20,
        choices=RESIDENCE_CHOICES,
        default='village',
    )
    lieu_residence = models.CharField(
        "Lieu de résidence actuel",
        max_length=200,
        blank=True,
        default='',
    )
 
    # ── Appartenance familiale ────────────────────────────────
 
    famille = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name='membres',
        verbose_name="Famille",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='persons_created',
        verbose_name="Enregistré(e) par",
    )
    est_chef_famille = models.BooleanField(
        "Chef de famille",
        default=False,
    )
 
    # ── Liens généalogiques (FK auto-référentiels) ────────────
 
    pere = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enfants_pere',
        verbose_name="Père",
        limit_choices_to={'genre': 'M'},   # Seulement les hommes
    )
    mere = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='enfants_mere',
        verbose_name="Mère",
        limit_choices_to={'genre': 'F'},   # Seulement les femmes
    )
    pere_nom_libre = models.CharField(
        "Nom libre du pÃ¨re",
        max_length=200,
        blank=True,
        default='',
    )
    mere_nom_libre = models.CharField(
        "Nom libre de la mère",
        max_length=200,
        blank=True,
        default='',
    )
    conjoint = models.OneToOneField(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='conjoint_de',
        verbose_name="Conjoint(e)",
    )
    conjoint_nom_libre = models.CharField(
        "Nom libre du conjoint",
        max_length=200,
        blank=True,
        default='',
    )
 
    # ── Notes & Méta ─────────────────────────────────────────
 
    notes = models.TextField(
        "Notes",
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
        table_name='families_person_history',
        history_id_field=models.UUIDField(default=uuid.uuid4),
    )
 
    # ── Meta Django ───────────────────────────────────────────
 
    class Meta:
        verbose_name        = 'Personne'
        verbose_name_plural = 'Personnes'
        ordering            = ['nom', 'prenom']
        constraints = [
            models.UniqueConstraint(
                fields=['famille'],
                condition=Q(
                    deleted__isnull=True,
                    est_chef_famille=True,
                ),
                name='uq_person_chef_famille_actif',
            ),
        ]
        indexes = [
            # Accélère la recherche autocomplétion père/mère
            models.Index(fields=['nom'],      name='idx_person_nom'),
            models.Index(fields=['prenom'],   name='idx_person_prenom'),
            # Accélère le chargement des membres d'une famille
            models.Index(fields=['famille'],  name='idx_person_famille'),
            # Accélère la navigation dans l'arbre généalogique
            models.Index(fields=['pere'],     name='idx_person_pere'),
            models.Index(fields=['mere'],     name='idx_person_mere'),
            # Filtres fréquents dans les listes
            models.Index(fields=['est_vivant'],     name='idx_person_vivant'),
            models.Index(fields=['type_residence'], name='idx_person_residence'),
            models.Index(fields=['genre'],          name='idx_person_genre'),
            # Recherche combinée nom + prénom
            models.Index(
                fields=['nom', 'prenom'],
                name='idx_person_nom_prenom',
            ),
        ]
 
    # ── Représentation ───────────────────────────────────────

    def _build_code_prefix(self):
        nom_famille = ''
        if self.famille_id:
            nom_famille = self.famille.nom_famille

        prefix = slugify(nom_famille).replace('-', '').upper()[:8]
        return prefix or 'PERS'

    def _generate_unique_code(self):
        prefix = self._build_code_prefix()
        manager = getattr(self.__class__, 'all_objects', self.__class__._base_manager)
        existing_codes = set(
            manager.filter(code__startswith=f"{prefix}-")
            .exclude(pk=self.pk)
            .values_list('code', flat=True)
        )

        compteur = 1
        candidate = f"{prefix}-{compteur:04d}"
        while candidate in existing_codes:
            compteur += 1
            candidate = f"{prefix}-{compteur:04d}"
        return candidate

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_unique_code()
        super().save(*args, **kwargs)
 
    def __str__(self):
        return self.nom_complet
 
    # ── Properties ───────────────────────────────────────────
 
    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"
 
    @property
    def nom_complet_avec_surnom(self):
        if self.surnom:
            return f"{self.prenom} « {self.surnom} » {self.nom}"
        return self.nom_complet
 
    @property
    def age(self):
        """Calcule l'âge en années. Retourne None si date inconnue."""
        if not self.date_naissance:
            return None
        aujourd_hui = date.today()
        d = self.date_naissance
        return (
            aujourd_hui.year - d.year
            - ((aujourd_hui.month, aujourd_hui.day) < (d.month, d.day))
        )
 
    @property
    def enfants(self):
        """
        Retourne tous les enfants (ceux qui ont cette personne
        comme père OU comme mère).
        """
        return Person.objects.filter(
            Q(pere=self) | Q(mere=self),
            deleted__isnull=True,
        ).order_by('date_naissance')
 
    @property
    def freres_soeurs(self):
        """
        Retourne les frères et sœurs (même père ou même mère),
        sans doublons.
        """
        qs = Person.objects.none()
        if self.pere_id:
            qs |= Person.objects.filter(
                pere_id=self.pere_id,
                deleted__isnull=True,
            ).exclude(id=self.id)
        if self.mere_id:
            qs |= Person.objects.filter(
                mere_id=self.mere_id,
                deleted__isnull=True,
            ).exclude(id=self.id)
        return qs.distinct().order_by('date_naissance')
 
    @property
    def _est_chef_famille_inferre(self):
        """
        True si cette personne est le chef de sa famille
        (homme sans père ni mère connu).
        """
        return (
            self.genre == 'M'
            and self.pere_id is None
            and self.mere_id is None
            and not self.pere_nom_libre
            and not self.mere_nom_libre
        )
 
    @property
    def est_en_diaspora(self):
        return self.type_residence == 'diaspora'
 
    @property
    def a_profil_diaspora(self):
        """True si un profil DiasporaMember est lié à cette personne."""
        return hasattr(self, 'profil_diaspora')
 
    @property
    def generation(self):
        """
        Retourne le numéro de génération en remontant vers la racine.
        0 = pas de parents connus (chef / ancêtre).
        """
        niveau  = 0
        courant = self
        visites = set()
        while (courant.pere_id or courant.mere_id) and courant.id not in visites:
            visites.add(courant.id)
            niveau += 1
            courant = courant.pere or courant.mere
            if not courant:
                break
        return niveau
 
