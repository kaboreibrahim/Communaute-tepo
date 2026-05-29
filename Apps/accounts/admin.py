from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html, format_html_join

from .models.Utilisateur import Utilisateur
from .models.code import CodeVerification


class CodeVerificationInline(admin.TabularInline):
    model = CodeVerification
    extra = 0
    show_change_link = True
    can_delete = False
    max_num = 10
    fields = (
        "type_code",
        "code",
        "email",
        "is_used",
        "attempts",
        "max_attempts",
        "expires_at",
        "created_at",
    )
    readonly_fields = (
        "type_code",
        "code",
        "email",
        "is_used",
        "attempts",
        "max_attempts",
        "expires_at",
        "created_at",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            deleted__isnull=True
        ).order_by("-created_at")


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = (
        "avatar_display",
        "username",
        "get_full_name",
        "email",
        "role_badge",
        "village",
        "statut_display",
        "is_active",
        "date_joined",
    )
    list_display_links = ("username", "get_full_name")
    list_filter = (
        "role",
        "is_active",
        "is_verified",
        "is_online",
        "is_staff",
        "village",
        "date_joined",
    )
    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "telephone",
        "village__nom",
    )
    ordering = ("-date_joined",)
    list_per_page = 30
    readonly_fields = (
        "date_joined",
        "last_login",
        "created_at",
        "updated_at",
        "is_online",
        "avatar_display",
        "statut_display",
        "historique_connexions",
    )
    inlines = [CodeVerificationInline]

    fieldsets = (
        (
            "Identite",
            {
                "fields": (
                    ("avatar_display", "photo_profil"),
                    ("username", "email"),
                    ("first_name", "last_name"),
                    "telephone",
                )
            },
        ),
        (
            "Role et village",
            {
                "fields": (
                    ("role", "village"),
                )
            },
        ),
        (
            "Statut du compte",
            {
                "fields": (
                    ("is_active", "is_staff", "is_superuser"),
                    ("is_verified", "is_online"),
                    "statut_display",
                )
            },
        ),
        (
            "Mot de passe",
            {
                "fields": ("password",),
                "classes": ("collapse",),
            },
        ),
        (
            "Permissions",
            {
                "fields": ("groups", "user_permissions"),
                "classes": ("collapse",),
            },
        ),
        (
            "Historique",
            {
                "fields": (
                    "date_joined",
                    "last_login",
                    "created_at",
                    "updated_at",
                    "historique_connexions",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = (
        (
            "Compte",
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    ("first_name", "last_name"),
                    "telephone",
                    ("password1", "password2"),
                ),
            },
        ),
        (
            "Role et village",
            {
                "fields": (
                    ("role", "village"),
                ),
            },
        ),
    )

    ROLE_COLORS = {
        "admin": ("#534AB7", "#EEEDFE"),
        "chef_village": ("#0F6E56", "#E1F5EE"),
        "saisie": ("#185FA5", "#E6F1FB"),
        "diaspora": ("#854F0B", "#FAEEDA"),
        "visiteur": ("#5F5E5A", "#F1EFE8"),
    }

    @admin.display(description="Photo")
    def avatar_display(self, obj):
        if not obj:
            return "-"
        if obj.photo_profil:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;'
                'border-radius:50%;object-fit:cover;'
                'border:2px solid #E2E8F0;">',
                obj.photo_profil.url,
            )
        bg = self.ROLE_COLORS.get(obj.role, ("#5F5E5A", "#F1EFE8"))[0]
        initiales = ""
        if obj.first_name:
            initiales += obj.first_name[0].upper()
        if obj.last_name:
            initiales += obj.last_name[0].upper()
        if not initiales:
            initiales = obj.username[0].upper()
        return format_html(
            '<div style="width:40px;height:40px;border-radius:50%;'
            'background:{};color:#fff;display:flex;align-items:center;'
            'justify-content:center;font-weight:600;font-size:14px;">'
            "{}</div>",
            bg,
            initiales,
        )

    @admin.display(description="Role")
    def role_badge(self, obj):
        bg, color = self.ROLE_COLORS.get(obj.role, ("#F1EFE8", "#2C2C2A"))
        return format_html(
            '<span style="display:inline-block;padding:2px 10px;'
            'border-radius:10px;font-size:11px;font-weight:500;'
            'background:{};color:{};">{}</span>',
            bg,
            color,
            obj.get_role_display(),
        )

    @admin.display(description="Statut")
    def statut_display(self, obj):
        badges = []
        if obj.is_online:
            badges.append(("#E1F5EE", "#0F6E56", "En ligne"))
        else:
            badges.append(("#F1EFE8", "#5F5E5A", "Hors ligne"))
        if obj.is_verified:
            badges.append(("#EAF3DE", "#27500A", "Verifie"))
        else:
            badges.append(("#FAECE7", "#712B13", "Non verifie"))
        return format_html(
            '<div style="display:flex;gap:4px;flex-wrap:wrap;">{}</div>',
            format_html_join(
                "",
                '<span style="display:inline-block;padding:2px 8px;'
                'border-radius:10px;font-size:11px;background:{};color:{};">{}</span>',
                ((bg, color, label) for bg, color, label in badges),
            ),
        )

    @admin.display(description="Historique connexions")
    def historique_connexions(self, obj):
        if not obj:
            return "Aucun historique disponible"
        historique = obj.history.all().order_by("-history_date")[:5]
        if not historique:
            return "Aucun historique disponible"
        lignes = format_html_join(
            "",
            '<li style="font-size:12px;padding:2px 0;">{} - {} - {}</li>',
            (
                (
                    h.history_date.strftime("%d/%m/%Y %H:%M"),
                    h.history_type,
                    h.history_user or "systeme",
                )
                for h in historique
            ),
        )
        return format_html(
            '<ul style="margin:0;padding-left:16px;">{}</ul>',
            lignes,
        )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            deleted__isnull=True
        ).select_related("village")

    actions = [
        "activer_comptes",
        "desactiver_comptes",
        "marquer_verifies",
        "exporter_csv",
    ]

    @admin.action(description="Activer les comptes selectionnes")
    def activer_comptes(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} compte(s) active(s).")

    @admin.action(description="Desactiver les comptes selectionnes")
    def desactiver_comptes(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(
            request,
            f"{n} compte(s) desactive(s).",
            level="warning",
        )

    @admin.action(description="Marquer comme verifies")
    def marquer_verifies(self, request, queryset):
        n = queryset.update(is_verified=True)
        self.message_user(request, f"{n} compte(s) marque(s) comme verifies.")

    @admin.action(description="Exporter en CSV")
    def exporter_csv(self, request, queryset):
        import csv

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="utilisateurs_olodio.csv"'
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow(
            [
                "Username",
                "Nom complet",
                "Email",
                "Role",
                "Village",
                "Telephone",
                "Verifie",
                "Actif",
                "En ligne",
                "Date inscription",
            ]
        )
        for user in queryset.select_related("village"):
            writer.writerow(
                [
                    user.username,
                    user.get_full_name() or "-",
                    user.email or "-",
                    user.get_role_display(),
                    user.village.nom if user.village else "-",
                    user.telephone or "-",
                    "Oui" if user.is_verified else "Non",
                    "Oui" if user.is_active else "Non",
                    "Oui" if user.is_online else "Non",
                    user.date_joined.strftime("%d/%m/%Y"),
                ]
            )
        return response


@admin.register(CodeVerification)
class CodeVerificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "type_badge",
        "code",
        "email",
        "statut_display",
        "tentatives_display",
        "expiration_display",
        "created_at",
    )
    list_filter = (
        "type_code",
        "is_used",
        "created_at",
    )
    search_fields = (
        "user__username",
        "user__email",
        "code",
        "email",
    )
    ordering = ("-created_at",)
    list_per_page = 40
    date_hierarchy = "created_at"
    readonly_fields = (
        "id",
        "user",
        "code",
        "type_code",
        "email",
        "attempts",
        "is_used",
        "expires_at",
        "created_at",
        "used_at",
        "statut_display",
        "tentatives_display",
        "expiration_display",
    )

    def has_add_permission(self, request):
        return False

    fieldsets = (
        (
            "Code",
            {
                "fields": (
                    "id",
                    ("user", "email"),
                    ("type_code", "code"),
                )
            },
        ),
        (
            "Statut",
            {
                "fields": (
                    "statut_display",
                    ("is_used", "used_at"),
                    "tentatives_display",
                    "expiration_display",
                    "expires_at",
                )
            },
        ),
        (
            "Meta",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    TYPE_COLORS = {
        "activation": ("#E1F5EE", "#0F6E56"),
        "otp": ("#E6F1FB", "#0C447C"),
        "password_reset": ("#FAECE7", "#712B13"),
        "email_change": ("#FAEEDA", "#633806"),
    }

    @admin.display(description="Type")
    def type_badge(self, obj):
        bg, color = self.TYPE_COLORS.get(obj.type_code, ("#F1EFE8", "#2C2C2A"))
        return format_html(
            '<span style="display:inline-block;padding:2px 9px;'
            'border-radius:10px;font-size:11px;font-weight:500;'
            'background:{};color:{};">{}</span>',
            bg,
            color,
            obj.get_type_code_display(),
        )

    @admin.display(description="Statut")
    def statut_display(self, obj):
        if obj.is_used:
            return format_html(
                '<span style="display:inline-block;padding:2px 9px;'
                'border-radius:10px;font-size:11px;font-weight:500;'
                'background:#F1EFE8;color:#444441;">{}</span>',
                "Utilise",
            )
        if obj.is_expired():
            return format_html(
                '<span style="display:inline-block;padding:2px 9px;'
                'border-radius:10px;font-size:11px;font-weight:500;'
                'background:#FAECE7;color:#712B13;">{}</span>',
                "Expire",
            )
        if obj.attempts >= obj.max_attempts:
            return format_html(
                '<span style="display:inline-block;padding:2px 9px;'
                'border-radius:10px;font-size:11px;font-weight:500;'
                'background:#FAEEDA;color:#633806;">{}</span>',
                "Bloque",
            )
        return format_html(
            '<span style="display:inline-block;padding:2px 9px;'
            'border-radius:10px;font-size:11px;font-weight:500;'
            'background:#E1F5EE;color:#0F6E56;">{}</span>',
            "Valide",
        )

    @admin.display(description="Tentatives")
    def tentatives_display(self, obj):
        ratio = obj.attempts / obj.max_attempts if obj.max_attempts else 0
        color = "#712B13" if ratio >= 1 else "#633806" if ratio >= 0.6 else "#0F6E56"
        return format_html(
            '<span style="color:{};font-weight:500;">{} / {}</span>',
            color,
            obj.attempts,
            obj.max_attempts,
        )

    @admin.display(description="Expiration")
    def expiration_display(self, obj):
        if not obj.expires_at:
            return "-"
        now = timezone.now()
        delta = obj.expires_at - now
        if delta.total_seconds() <= 0:
            return format_html(
                '<span style="color:#712B13;font-size:12px;">{}</span>',
                "Expire",
            )
        minutes = int(delta.total_seconds() // 60)
        seconds = int(delta.total_seconds() % 60)
        color = "#0F6E56" if minutes >= 2 else "#633806"
        return format_html(
            '<span style="color:{};font-size:12px;">'
            "Expire dans {}m {}s</span>",
            color,
            minutes,
            seconds,
        )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(
            deleted__isnull=True
        ).select_related("user")

    actions = ["invalider_codes", "purger_expires"]

    @admin.action(description="Invalider les codes selectionnes")
    def invalider_codes(self, request, queryset):
        n = queryset.filter(is_used=False).update(is_used=True)
        self.message_user(
            request,
            f"{n} code(s) invalide(s).",
            level="warning",
        )

    @admin.action(description="Purger les codes expires")
    def purger_expires(self, request, queryset):
        n = queryset.filter(expires_at__lt=timezone.now()).update(is_used=True)
        self.message_user(request, f"{n} code(s) expire(s) purge(s).")
