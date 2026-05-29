from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Event, Notification, TypeEvenement


@admin.register(TypeEvenement)
class TypeEvenementAdmin(admin.ModelAdmin):
    list_display = ("nom", "slug", "badge_apercu", "icone", "est_communautaire", "ordre")
    list_editable = ("ordre", "est_communautaire")
    search_fields = ("nom", "slug")
    prepopulated_fields = {"slug": ("nom",)}

    @admin.display(description="Badge")
    def badge_apercu(self, obj):
        return format_html(
            '<span style="display:inline-block;padding:2px 10px;border-radius:10px;'
            'font-size:11px;font-weight:600;background:{};color:{};">{}</span>',
            obj.couleur_fond,
            obj.couleur_texte,
            obj.nom,
        )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "titre",
        "type_badge",
        "personne",
        "village",
        "nom_contact",
        "date_evenement",
        "lieu_affichage",
        "public_badge",
        "validation_badge",
        "validation_info",
    )
    list_filter = (
        "type",
        "statut_validation",
        "est_public",
        "date_evenement",
        "date_creation",
    )
    search_fields = (
        "titre",
        "description",
        "lieu",
        "resume",
        "nom_contact",
        "telephone_contact",
        "email_contact",
        "personne__nom",
        "personne__prenom",
        "personne__famille__nom_famille",
        "personne__famille__village__nom",
        "village__nom",
    )
    ordering = ("-date_evenement", "-date_creation")
    list_per_page = 30
    date_hierarchy = "date_evenement"
    autocomplete_fields = ("personne",)
    readonly_fields = (
        "date_creation",
        "date_validation",
        "valide_par",
        "photo_preview",
        "validation_info",
    )
    actions = (
        "approuver_evenements",
        "refuser_evenements",
        "rendre_publics",
        "retirer_de_l_accueil",
    )

    fieldsets = (
        (
            "Evenement",
            {
                "fields": (
                    ("type", "titre"),
                    "resume",
                    "description",
                    ("date_evenement", "lieu"),
                    ("personne", "village"),
                )
            },
        ),
        (
            "Publication",
            {
                "fields": (
                    ("est_public", "statut_validation"),
                    ("valide_par", "date_validation"),
                    "validation_info",
                )
            },
        ),
        (
            "Soumission publique",
            {
                "fields": (
                    ("nom_contact", "telephone_contact"),
                    "email_contact",
                )
            },
        ),
        (
            "Media",
            {
                "fields": (
                    "photo",
                    "photo_preview",
                )
            },
        ),
        (
            "Meta",
            {
                "fields": ("date_creation",),
                "classes": ("collapse",),
            },
        ),
    )

    VALIDATION_COLORS = {
        "pending": ("#FAEEDA", "#633806", "En attente"),
        "approved": ("#E1F5EE", "#0F6E56", "Approuve"),
        "rejected": ("#FAECE7", "#712B13", "Refuse"),
    }

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "type",
            "personne",
            "personne__famille",
            "personne__famille__village",
            "village",
            "valide_par",
        )

    def save_model(self, request, obj, form, change):
        if not obj.resume and obj.description:
            obj.resume = obj.description[:250]
        if not obj.village_id and obj.personne_id and obj.personne.famille_id:
            obj.village = obj.personne.famille.village
        if obj.statut_validation == "pending":
            obj.valide_par = None
            obj.date_validation = None
        elif obj.statut_validation in {"approved", "rejected"}:
            obj.valide_par = request.user
            obj.date_validation = timezone.now()
        super().save_model(request, obj, form, change)

    def _badge(self, label, bg, color):
        return format_html(
            '<span style="display:inline-block;padding:2px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;'
            'background:{};color:{};">{}</span>',
            bg,
            color,
            label,
        )

    @admin.display(description="Type", ordering="type__nom")
    def type_badge(self, obj):
        if not obj.type_id:
            return self._badge("—", "#F8FAFC", "#334155")
        return self._badge(obj.type.nom, obj.type.couleur_fond, obj.type.couleur_texte)

    @admin.display(description="Lieu")
    def lieu_affichage(self, obj):
        return obj.lieu_affichage

    @admin.display(description="Accueil", ordering="est_public")
    def public_badge(self, obj):
        if obj.est_public:
            return self._badge("Public", "#E1F5EE", "#0F6E56")
        return self._badge("Prive", "#F1EFE8", "#444441")

    @admin.display(description="Validation", ordering="statut_validation")
    def validation_badge(self, obj):
        bg, color, label = self.VALIDATION_COLORS.get(
            obj.statut_validation,
            ("#F8FAFC", "#334155", obj.statut_validation),
        )
        return self._badge(label, bg, color)

    @admin.display(description="Validation admin")
    def validation_info(self, obj):
        if not obj or not getattr(obj, "pk", None):
            return format_html(
                '<span style="color:#633806;font-size:12px;">{}</span>',
                "En attente de moderation",
            )
        if obj.statut_validation == "pending":
            return format_html(
                '<span style="color:#633806;font-size:12px;">{}</span>',
                "En attente de moderation",
            )
        if not obj.valide_par_id or not obj.date_validation:
            return format_html(
                '<span style="color:#64748B;font-size:12px;">{}</span>',
                "Aucune trace de validation",
            )
        return format_html(
            '<span style="font-size:12px;">{} le {}</span>',
            obj.valide_par,
            timezone.localtime(obj.date_validation).strftime("%d/%m/%Y a %H:%M"),
        )

    @admin.display(description="Photo")
    def photo_preview(self, obj):
        if not obj or not obj.photo:
            return "Aucune photo"
        try:
            return format_html(
                '<img src="{}" alt="{}" style="max-height:140px;border-radius:12px;" />',
                obj.photo.url,
                obj.titre,
            )
        except Exception:
            return "Fichier indisponible"

    @admin.action(description="Approuver les evenements selectionnes")
    def approuver_evenements(self, request, queryset):
        total = queryset.update(
            statut_validation="approved",
            valide_par=request.user,
            date_validation=timezone.now(),
        )
        self.message_user(request, f"{total} evenement(s) approuve(s).")

    @admin.action(description="Refuser les evenements selectionnes")
    def refuser_evenements(self, request, queryset):
        total = queryset.update(
            statut_validation="rejected",
            valide_par=request.user,
            date_validation=timezone.now(),
        )
        self.message_user(request, f"{total} evenement(s) refuse(s).")

    @admin.action(description="Rendre publics les evenements selectionnes")
    def rendre_publics(self, request, queryset):
        total = queryset.update(est_public=True)
        self.message_user(request, f"{total} evenement(s) rendu(s) publics.")

    @admin.action(description="Retirer de l'accueil")
    def retirer_de_l_accueil(self, request, queryset):
        total = queryset.update(est_public=False)
        self.message_user(request, f"{total} evenement(s) retire(s) de l'accueil.")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "evenement",
        "destinataire",
        "est_lue",
        "date_envoi",
        "date_lecture",
    )
    list_filter = ("est_lue", "date_envoi")
    search_fields = (
        "evenement__titre",
        "destinataire__username",
        "destinataire__email",
    )
    ordering = ("-date_envoi",)
    readonly_fields = ("date_envoi",)
