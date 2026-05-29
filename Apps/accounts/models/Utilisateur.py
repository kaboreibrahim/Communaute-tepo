from django.db import models
from django.contrib.auth.models import AbstractUser
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from django.utils import timezone
import uuid
from simple_history.models import HistoricalRecords
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
 

def upload_to_utilisateur_profile(instance, filename):
    """Génère le chemin d'upload pour les photos de profil des utilisateurs"""
    ext = filename.split('.')[-1]
    filename = f"{instance.id}.{ext}"
    return f"utilisateurs/{instance.username}/profil/{filename}"


class Utilisateur(AbstractUser ,SafeDeleteModel):

    """
    Model utilisateur personaliser inheriting from Django's AbstractUser.
    - `id`: User's unique identifier.
    - `role`: User's role with predefined choices (Administrateur, Chef de village, Agent de saisie, Membre diaspora, Visiteur).
    - `telephone`: User's phone number.
    - `photo_profil`: User's profile photo.
    - `village`: User's village.
    - `created_at`: Timestamp when the user was created.
    - `updated_at`: Timestamp when the user was last updated.
    - `is_verified`: Boolean field to track if the user's email is verified.
    - `is_online`: Boolean field to track if the user is online.
    - `groups`: Many-to-many relationship with Django's Group model.
    - `user_permissions`: Many-to-many relationship with Django's Permission model.
    """
    
    TYPES_USER=[
        ('admin',        'Administrateur'),
        ('chef_village', 'Chef de village'),
        ('saisie',       'Agent de saisie'),
        ('diaspora',     'Membre diaspora'),
        ('visiteur',     'Visiteur'),
    ]

    upload_to_utilisateur_profile = upload_to_utilisateur_profile

    id = models.UUIDField(
        "Identifiant unique",
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    role = models.CharField(max_length=20, choices=TYPES_USER, default='visiteur')

    telephone = models.CharField(max_length=20, blank=True)

    photo_profil = models.ImageField(upload_to=upload_to_utilisateur_profile, blank=True)

    village     = models.ForeignKey('villages.Village', null=True, blank=True, on_delete=models.SET_NULL,related_name='utilisateur')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    _safedelete_policy = SOFT_DELETE_CASCADE

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='utilisateur_set',
        related_query_name='utilisateur',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='utilisateur_set',
        related_query_name='utilisateur',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    is_verified = models.BooleanField(default=False)

    is_online = models.BooleanField(default=False)

    history = HistoricalRecords(table_name='Utilisateur_history', history_id_field=models.UUIDField(default=uuid.uuid4))
 

    @receiver(user_logged_out)
    def user_logged_out_handler(sender, request, user, **kwargs):
        user.is_online = False
        user.save()
    
    @receiver(user_logged_in)
    def user_logged_in_handler(sender, request, user, **kwargs):
        user.is_online = True
        user.last_login = timezone.now()  # Met à jour le champ last_login
        user.save()

 
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    @property
    def est_admin(self):
        return self.role == 'admin' or self.is_superuser

    @property
    def est_agent_saisie(self):
        return self.role in ('admin', 'chef_village', 'saisie') or self.is_superuser

    @property
    def est_agent_saisie_limite(self):
        return self.role == 'saisie' and not self.est_admin

    @property
    def peut_supprimer_registre(self):
        return self.est_admin or self.role == 'chef_village'

    
