from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from Apps.medias.models import CategorieMedia, Media


@method_decorator(login_required, name='dispatch')
class MediaDashboardView(TemplateView):
    template_name = 'medias/dashboard.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        qs = Media.objects.filter(deleted__isnull=True)

        total_images = qs.filter(type_media=Media.TYPE_IMAGE).count()
        total_videos = qs.filter(type_media=Media.TYPE_VIDEO).count()
        total_medias = qs.count()
        taille_totale = qs.aggregate(t=Sum('taille_fichier'))['t'] or 0

        recents = qs.select_related('categorie', 'uploade_par').order_by('-date_creation')[:12]

        categories = (
            CategorieMedia.objects
            .annotate(nb=Count('medias', filter=__import__('django.db.models', fromlist=['Q']).Q(medias__deleted__isnull=True)))
            .order_by('-nb')[:6]
        )

        ctx.update({
            'total_images': total_images,
            'total_videos': total_videos,
            'total_medias': total_medias,
            'taille_totale': _format_size(taille_totale),
            'recents': recents,
            'categories': categories,
        })
        return ctx


def _format_size(octets):
    if octets < 1024:
        return f"{octets} o"
    if octets < 1024 ** 2:
        return f"{octets / 1024:.1f} Ko"
    if octets < 1024 ** 3:
        return f"{octets / 1024 ** 2:.1f} Mo"
    return f"{octets / 1024 ** 3:.2f} Go"
