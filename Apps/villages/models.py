from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
import uuid
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE


class Village(SafeDeleteModel):

    """Modèle pour les villages"""
    _safedelete_policy = SOFT_DELETE_CASCADE
    

    id = models.UUIDField(
        "Identifiant unique",
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    nom              = models.CharField(max_length=100, unique=True)
    slug             = models.SlugField(max_length=120, unique=True, blank=True)
    description      = models.TextField(blank=True)
    latitude         = models.FloatField(null=True, blank=True)
    longitude        = models.FloatField(null=True, blank=True)
    chef_village     = models.CharField(max_length=200, blank=True)
    created_by       = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='villages_created',
        verbose_name="Créé par",
    )
    date_creation    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nom']
        verbose_name = 'Village'
        verbose_name_plural = 'Villages'

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nom)
            slug = base
            counter = 1
            while Village.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("villages:village-detail", kwargs={"slug": self.slug})

    def __str__(self):
        return self.nom

    def _get_familles_manager(self):
        manager = getattr(self, 'familles', None)
        if manager is not None:
            return manager

        for relation in self._meta.related_objects:
            related_model = getattr(relation, 'related_model', None)
            if related_model and related_model._meta.app_label == 'families':
                accessor_name = relation.get_accessor_name()
                if accessor_name and hasattr(self, accessor_name):
                    return getattr(self, accessor_name)
        return None
	
    @property
    def nombre_familles(self):
        familles = self._get_familles_manager()
        return familles.count() if familles is not None else 0

    @property
    def nombre_habitants(self):
        from Apps.person.models import Person
        return Person.objects.filter(
            famille__village=self,
            famille__deleted__isnull=True,
            deleted__isnull=True,
        ).count()
    
    @property
    def nombre_ecoles(self):
        """Retourne le nombre d'écoles dans le village"""
        return self.infrastructures.filter(type_infrastructure='ecole').count()
    
    @property
    def nombre_hopitaux(self):
        """Retourne le nombre d'hôpitaux dans le village"""
        return self.infrastructures.filter(type_infrastructure='hopital').count()
    
    @property
    def nombre_dispensaires(self):
        """Retourne le nombre de dispensaires dans le village"""
        return self.infrastructures.filter(type_infrastructure='dispensaire').count()
    
    @property
    def nombre_centres_sante(self):
        """Retourne le nombre de centres de santé dans le village"""
        return self.infrastructures.filter(type_infrastructure='centre_sante').count()
    
    @property
    def nombre_total_infrastructures(self):
        """Retourne le nombre total d'infrastructures dans le village"""
        return self.infrastructures.count()
    
    def get_infrastructures_by_type(self):
        """Retourne un dictionnaire avec le dénombrement des infrastructures par type"""
        result = {}
        for type_code, type_label in Infrastructure.TYPES_INFRASTRUCTURE:
            count = self.infrastructures.filter(type_infrastructure=type_code).count()
            if count > 0:
                result[type_label] = count
        return result


class TypeInfrastructure(models.Model):
    """Types d'infrastructures disponibles"""
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icone = models.CharField(max_length=50, blank=True, help_text="Nom de l'icône (ex: school, hospital)")
    
    class Meta:
        verbose_name = "Type d'infrastructure"
        verbose_name_plural = "Types d'infrastructures"
    
    def __str__(self):
        return self.nom


class Infrastructure(SafeDeleteModel):
    """Infrastructures présentes dans les villages"""
    _safedelete_policy = SOFT_DELETE_CASCADE
    
    TYPES_INFRASTRUCTURE = [
        ('ecole', 'École'),
        ('hopital', 'Hôpital'),
        ('dispensaire', 'Dispensaire'),
        ('marche', 'Marché'),
        ('centre_sante', 'Centre de santé'),
        ('ecole_maternelle', 'École maternelle'),
        ('lycee', 'Lycée'),
        ('universite', 'Université'),
        ('poste_police', 'Poste de police'),
        ('mairie', 'Mairie'),
        ('place_publique', 'Place publique'),
        ('centre_communautaire', 'Centre communautaire'),
        ('puit', 'Puits'),
        ('forage', 'Forage'),
        ('electricite', 'Électricité'),
        ('telephone', 'Téléphonie'),
        ('internet', 'Internet'),
        ('autre', 'Autre'),
    ]
    
    id = models.UUIDField(
        "Identifiant unique",
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    village = models.ForeignKey(
        Village, 
        on_delete=models.CASCADE, 
        related_name='infrastructures'
    )
    
    type_infrastructure = models.CharField(
        max_length=50, 
        choices=TYPES_INFRASTRUCTURE,
        verbose_name="Type d'infrastructure"
    )
    
    nom = models.CharField(
        max_length=200, 
        verbose_name="Nom de l'infrastructure"
    )
    
    description = models.TextField(blank=True)
    
    capacite = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        help_text="Capacité d'accueil (élèves, patients, etc.)"
    )
    
    date_construction = models.DateField(
        null=True, 
        blank=True,
        verbose_name="Date de construction"
    )
    
    etat = models.CharField(
        max_length=20,
        choices=[
            ('bon', 'Bon état'),
            ('moyen', 'État moyen'),
            ('mauvais', 'Mauvais état'),
            ('en_construction', 'En construction'),
            ('abandonne', 'Abandonné'),
        ],
        default='bon',
        verbose_name="État de l'infrastructure"
    )
    
    responsable = models.CharField(
        max_length=200, 
        blank=True,
        verbose_name="Responsable"
    )
    
    contact_responsable = models.CharField(
        max_length=20, 
        blank=True,
        verbose_name="Contact du responsable"
    )
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Infrastructure"
        verbose_name_plural = "Infrastructures"
        ordering = ['village', 'type_infrastructure', 'nom']
    
    def __str__(self):
        return f"{self.get_type_infrastructure_display()} - {self.nom} ({self.village.nom})"
