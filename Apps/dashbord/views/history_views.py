from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views import View

from Apps.histoire.models import ActionHistory


def _safe_positive_int(value, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


@method_decorator(login_required, name='dispatch')
class ActionHistoryListView(View):
    template_name = 'dashbord/historique_actions.html'

    def dispatch(self, request, *args, **kwargs):
        if not getattr(request.user, 'est_admin', False):
            raise PermissionDenied("Acces reserve a l'administration.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        q = request.GET.get('q', '').strip()
        action = request.GET.get('action', '').strip()
        page = _safe_positive_int(request.GET.get('page', 1), 1)
        par_page = _safe_positive_int(request.GET.get('par_page', 20), 20)

        base_qs = ActionHistory.objects.select_related('user').order_by('-date_action')
        filtered_qs = base_qs

        if q:
            filtered_qs = filtered_qs.filter(
                Q(user_name__icontains=q)
                | Q(user_role__icontains=q)
                | Q(fonction__icontains=q)
                | Q(action__icontains=q)
                | Q(pays__icontains=q)
                | Q(ville__icontains=q)
                | Q(chemin__icontains=q)
            )

        if action:
            filtered_qs = filtered_qs.filter(action=action)

        paginator = Paginator(filtered_qs, par_page)
        page_obj = paginator.get_page(page)
        current_page = page_obj.number
        total = paginator.count
        display_start = ((current_page - 1) * par_page) + 1 if total else 0
        display_end = min(current_page * par_page, total) if total else 0
        actions = list(
            base_qs.order_by().values_list('action', flat=True).distinct()
        )

        today = timezone.localdate()
        stats = {
            'total': base_qs.count(),
            'today': base_qs.filter(date_action__date=today).count(),
            'failed': base_qs.filter(statut_code__gte=400).count(),
            'unique_users': base_qs.exclude(user_name='').values('user_name').distinct().count(),
        }

        return render(request, self.template_name, {
            'logs': page_obj.object_list,
            'q': q,
            'action': action,
            'actions': actions,
            'page': current_page,
            'nb_pages': paginator.num_pages,
            'total': total,
            'par_page': par_page,
            'display_start': display_start,
            'display_end': display_end,
            'stats': stats,
        })
