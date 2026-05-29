from django.core.paginator import Paginator
from django.shortcuts import render
from django.views import View

from Apps.medias.models import CategorieMedia, Media


class PublicMediaView(View):
    template_name = 'galerie.html'
    per_page = 24

    def get(self, request):
        qs = Media.objects.filter(deleted__isnull=True).select_related('categorie')

        type_filtre = request.GET.get('type', '')
        categorie_filtre = request.GET.get('categorie', '')

        if type_filtre in (Media.TYPE_IMAGE, Media.TYPE_VIDEO):
            qs = qs.filter(type_media=type_filtre)
        if categorie_filtre:
            qs = qs.filter(categorie__slug=categorie_filtre)

        paginator = Paginator(qs, self.per_page)
        page = paginator.get_page(request.GET.get('page', 1))

        total_images = Media.objects.filter(deleted__isnull=True, type_media=Media.TYPE_IMAGE).count()
        total_videos = Media.objects.filter(deleted__isnull=True, type_media=Media.TYPE_VIDEO).count()
        categories = CategorieMedia.objects.filter(medias__deleted__isnull=True).distinct()

        return render(request, self.template_name, {
            'page_obj': page,
            'categories': categories,
            'type_filtre': type_filtre,
            'categorie_filtre': categorie_filtre,
            'total_images': total_images,
            'total_videos': total_videos,
            'total': paginator.count,
        })
