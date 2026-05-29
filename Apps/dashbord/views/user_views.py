from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View

from Apps.accounts.forms import DashboardUserCreationForm
from Apps.villages.models import Village

User = get_user_model()


def _safe_positive_int(value, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _avatar_classes(role: str, is_superuser: bool) -> str:
    if is_superuser or role == "admin":
        return "bg-primary/10 text-primary"
    if role == "chef_village":
        return "bg-amber-100 text-amber-700"
    if role == "saisie":
        return "bg-sky-100 text-sky-700"
    if role == "diaspora":
        return "bg-indigo-100 text-indigo-700"
    return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300"


def _role_badge(role: str, is_superuser: bool) -> str:
    if is_superuser or role == "admin":
        return "bg-primary/10 text-primary"
    if role == "chef_village":
        return "bg-amber-100 text-amber-700"
    if role == "saisie":
        return "bg-sky-100 text-sky-700"
    if role == "diaspora":
        return "bg-indigo-100 text-indigo-700"
    return "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300"


def _status_meta(user) -> dict:
    recent_limit = timezone.now() - timedelta(days=7)

    if not user.is_active:
        return {
            "label": "Inactive",
            "dot_classes": "bg-slate-300",
            "text_classes": "text-slate-400",
        }
    if user.is_online:
        return {
            "label": "En ligne",
            "dot_classes": "bg-primary",
            "text_classes": "text-primary",
        }
    if user.last_login and user.last_login >= recent_limit:
        return {
            "label": "Actif recent",
            "dot_classes": "bg-emerald-500",
            "text_classes": "text-emerald-600",
        }
    return {
        "label": "Hors ligne",
        "dot_classes": "bg-slate-300",
        "text_classes": "text-slate-500",
    }


def _verification_meta(user) -> dict:
    if user.is_verified:
        return {
            "label": "Verifie",
            "classes": "bg-emerald-100 text-emerald-700",
        }
    return {
        "label": "En attente",
        "classes": "bg-amber-100 text-amber-700",
    }


def _two_factor_label(user) -> str:
    if user.two_factor_method == "google_auth":
        return "2FA Google"
    if user.two_factor_method == "email":
        return "2FA Email"
    return "2FA inactive"


def _initials_for(user) -> str:
    initials = f"{(user.first_name or '')[:1]}{(user.last_name or '')[:1]}".strip()
    if initials:
        return initials.upper()
    return (user.username or "US")[:2].upper()


def _pagination_range(current_page: int, total_pages: int, radius: int = 2):
    start = max(1, current_page - radius)
    end = min(total_pages, current_page + radius)
    return range(start, end + 1)


@method_decorator(login_required, name="dispatch")
class AdminOnlyMixin(View):
    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, "est_admin", False):
            raise PermissionDenied("Acces reserve a l'administration.")
        return super().dispatch(request, *args, **kwargs)


class UserListView(AdminOnlyMixin):
    template_name = "accounts/liste_utilisateurs.html"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        role = request.GET.get("role", "").strip()
        status = request.GET.get("status", "").strip()
        village_id = request.GET.get("village", "").strip()
        page = _safe_positive_int(request.GET.get("page", 1), 1)
        par_page = _safe_positive_int(request.GET.get("par_page", 10), 10)

        base_qs = User.objects.filter(deleted__isnull=True).select_related("village")
        filtered_qs = base_qs.order_by("-is_online", "-last_login", "-created_at", "username")

        if q:
            filtered_qs = filtered_qs.filter(
                Q(username__icontains=q)
                | Q(email__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(telephone__icontains=q)
                | Q(village__nom__icontains=q)
            )

        valid_roles = {choice[0] for choice in User.TYPES_USER}
        if role == "admin":
            filtered_qs = filtered_qs.filter(Q(role="admin") | Q(is_superuser=True))
        elif role in valid_roles:
            filtered_qs = filtered_qs.filter(role=role)

        if village_id:
            filtered_qs = filtered_qs.filter(village_id=village_id)

        if status == "online":
            filtered_qs = filtered_qs.filter(is_active=True, is_online=True)
        elif status == "verified":
            filtered_qs = filtered_qs.filter(is_verified=True)
        elif status == "pending":
            filtered_qs = filtered_qs.filter(is_active=True, is_verified=False)
        elif status == "inactive":
            filtered_qs = filtered_qs.filter(is_active=False)
        elif status == "2fa":
            filtered_qs = filtered_qs.exclude(two_factor_method__isnull=True).exclude(two_factor_method="")

        paginator = Paginator(filtered_qs, par_page)
        page_obj = paginator.get_page(page)
        current_page = page_obj.number
        total = paginator.count
        display_start = ((current_page - 1) * par_page) + 1 if total else 0
        display_end = min(current_page * par_page, total) if total else 0

        role_counts = {
            item["role"]: item["total"]
            for item in base_qs.values("role").annotate(total=Count("id"))
        }
        admin_count = base_qs.filter(Q(role="admin") | Q(is_superuser=True)).count()
        verified_count = base_qs.filter(is_verified=True).count()
        pending_count = base_qs.filter(is_active=True, is_verified=False).count()
        online_count = base_qs.filter(is_active=True, is_online=True).count()
        recent_login_count = base_qs.filter(
            last_login__gte=timezone.now() - timedelta(days=7)
        ).count()
        users_with_village = base_qs.exclude(village__isnull=True).count()
        secured_count = base_qs.exclude(two_factor_method__isnull=True).exclude(
            two_factor_method=""
        ).count()

        user_rows = []
        for user in page_obj.object_list:
            user_rows.append(
                {
                    "id": user.id,
                    "display_name": (user.get_full_name() or "").strip() or user.username,
                    "secondary_line": user.email or user.telephone or f"@{user.username}",
                    "initials": _initials_for(user),
                    "avatar_classes": _avatar_classes(user.role, user.is_superuser),
                    "role_label": "Super Admin" if user.is_superuser else user.get_role_display(),
                    "role_classes": _role_badge(user.role, user.is_superuser),
                    "status": _status_meta(user),
                    "verification": _verification_meta(user),
                    "two_factor_label": _two_factor_label(user),
                    "last_login": user.last_login,
                    "created_at": user.created_at,
                    "village_name": user.village.nom if user.village else "Non rattache",
                    "email": user.email,
                    "telephone": user.telephone,
                }
            )

        role_tabs = [
            {
                "value": "",
                "label": "Tous",
                "count": base_qs.count(),
                "active": role == "",
            },
            {
                "value": "admin",
                "label": "Admins",
                "count": admin_count,
                "active": role == "admin",
            },
            {
                "value": "chef_village",
                "label": "Chefs",
                "count": role_counts.get("chef_village", 0),
                "active": role == "chef_village",
            },
            {
                "value": "saisie",
                "label": "Agents",
                "count": role_counts.get("saisie", 0),
                "active": role == "saisie",
            },
            {
                "value": "diaspora",
                "label": "Diaspora",
                "count": role_counts.get("diaspora", 0),
                "active": role == "diaspora",
            },
            {
                "value": "visiteur",
                "label": "Visiteurs",
                "count": role_counts.get("visiteur", 0),
                "active": role == "visiteur",
            },
        ]

        role_summary = []
        total_users = base_qs.count() or 1
        for value, label in User.TYPES_USER:
            count = admin_count if value == "admin" else role_counts.get(value, 0)
            role_summary.append(
                {
                    "label": "Administrateurs" if value == "admin" else label,
                    "count": count,
                    "percent": int(round((count / total_users) * 100)),
                    "classes": _role_badge(value, value == "admin"),
                }
            )

        return render(
            request,
            self.template_name,
            {
                "user_rows": user_rows,
                "q": q,
                "role": role,
                "status": status,
                "village_id": village_id,
                "villages": Village.objects.filter(deleted__isnull=True).order_by("nom"),
                "page": current_page,
                "nb_pages": paginator.num_pages,
                "page_range": _pagination_range(current_page, paginator.num_pages),
                "total": total,
                "par_page": par_page,
                "display_start": display_start,
                "display_end": display_end,
                "role_tabs": role_tabs,
                "role_summary": role_summary,
                "stats": {
                    "total_users": base_qs.count(),
                    "online_now": online_count,
                    "pending_approvals": pending_count,
                    "recent_logins": recent_login_count,
                    "verified_users": verified_count,
                    "secured_users": secured_count,
                    "users_with_village": users_with_village,
                    "admin_users": admin_count,
                },
            },
        )


class UserCreateView(AdminOnlyMixin):
    template_name = "accounts/formulaire_utilisateur.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "form": DashboardUserCreationForm(),
            },
        )

    def post(self, request):
        form = DashboardUserCreationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"L'utilisateur {user.username} a ete cree avec succes.",
            )
            return redirect("dashbord:user-list")

        messages.error(
            request,
            "Impossible de creer cet utilisateur. Verifiez les champs du formulaire.",
        )
        return render(
            request,
            self.template_name,
            {
                "form": form,
            },
        )
