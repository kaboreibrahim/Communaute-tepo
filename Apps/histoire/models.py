import uuid

from django.conf import settings
from django.db import models


class ActionHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='action_histories',
        verbose_name="Utilisateur",
    )
    user_name = models.CharField(max_length=255, blank=True, verbose_name="Nom utilisateur")
    user_role = models.CharField(max_length=64, blank=True, verbose_name="Fonction utilisateur")
    fonction = models.CharField(max_length=255, verbose_name="Fonction")
    action = models.CharField(max_length=120, verbose_name="Action")
    methode = models.CharField(max_length=16, blank=True, verbose_name="Méthode HTTP")
    chemin = models.CharField(max_length=500, blank=True, verbose_name="Chemin")
    statut_code = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Code statut",
    )
    adresse_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        unpack_ipv4=True,
        verbose_name="Adresse IP",
    )
    pays = models.CharField(max_length=120, default="Inconnu", blank=True)
    ville = models.CharField(max_length=120, default="Inconnu", blank=True)
    date_action = models.DateTimeField(auto_now_add=True, verbose_name="Date")

    class Meta:
        verbose_name = "Historique d'action"
        verbose_name_plural = "Historiques d'actions"
        ordering = ['-date_action']
        indexes = [
            models.Index(fields=['-date_action'], name='hist_action_date_idx'),
            models.Index(fields=['action'], name='hist_action_label_idx'),
            models.Index(fields=['fonction'], name='hist_action_view_idx'),
        ]

    def __str__(self):
        return f"{self.user_name or 'Anonyme'} - {self.action} ({self.date_action:%d/%m/%Y %H:%M})"
