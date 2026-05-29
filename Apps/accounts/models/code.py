from django.db import models
from safedelete.models import SafeDeleteModel, SOFT_DELETE_CASCADE
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import uuid
import random
import string
from django_lifecycle import LifecycleModel
from .Utilisateur import Utilisateur

class CodeVerification(SafeDeleteModel, LifecycleModel):
    """Modèle pour les codes de vérification d'email"""
    _safedelete_policy = SOFT_DELETE_CASCADE
    
    TYPE_CHOICES = [
        ('activation', 'Activation de compte'),
        ('otp', 'Code de vérification'),
        ('password_reset', 'Réinitialisation mot de passe'),
        ('email_change', 'Changement d\'email'),
    ]
    
    id = models.UUIDField(
        "Unique Identifier", 
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='codes_verification')
    code = models.CharField(max_length=6)
    type_code = models.CharField(max_length=20, choices=TYPE_CHOICES)
    email = models.EmailField()
    is_used = models.BooleanField(default=False)
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Code de vérification"
        verbose_name_plural = "Codes de vérification"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.code} ({self.type_code})"
    
    @classmethod
    def generate_code(cls):
        """Génère un code à 6 caractères, composé de lettres et de chiffres"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    @classmethod
    def create_verification_code(cls, user, type_code, email=None, validity_seconds=180):
        """Crée un nouveau code de vérification"""
        # Invalider les anciens codes non utilisés du même type
        cls.objects.filter(
            user=user,
            type_code=type_code,
            is_used=False
        ).update(is_used=True)
        
        # Créer le nouveau code
        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(seconds=validity_seconds)
        
        return cls.objects.create(
            user=user,
            code=code,
            type_code=type_code,
            email=email or user.email,
            expires_at=expires_at
        )
    
    def is_expired(self):
        """Vérifie si le code a expiré"""
        return self.expires_at is not None and timezone.now() > self.expires_at
    
    def is_valid(self):
        """Vérifie si le code est encore valide"""
        return (
            not self.is_used and 
            not self.is_expired() and 
            self.attempts < self.max_attempts
        )

    
    def mark_as_used(self):
        """Marque le code comme utilisé"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()
    
    def increment_attempts(self):
        """Incrémente le nombre de tentatives"""
        self.attempts += 1
        self.save()
        return self.attempts >= self.max_attempts
