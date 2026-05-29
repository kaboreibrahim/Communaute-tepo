import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import DetailView, UpdateView

from Apps.medias.forms import MediaUpdateForm, MediaUploadForm
from Apps.medias.models import CategorieMedia, Media


@method_decorator(login_required, name='dispatch')
class MediaListView(View):
    template_name = 'medias/media_list.html'
    per_page = 24

    def get(self, request):
        qs = Media.objects.filter(deleted__isnull=True).select_related(
            'categorie', 'uploade_par'
        )

        type_filtre = request.GET.get('type', '')
        categorie_filtre = request.GET.get('categorie', '')
        date_debut = request.GET.get('date_debut', '')
        date_fin = request.GET.get('date_fin', '')
        utilisateur_filtre = request.GET.get('utilisateur', '')
        recherche = request.GET.get('q', '').strip()

        if type_filtre in (Media.TYPE_IMAGE, Media.TYPE_VIDEO):
            qs = qs.filter(type_media=type_filtre)
        if categorie_filtre:
            qs = qs.filter(categorie__slug=categorie_filtre)
        if date_debut:
            qs = qs.filter(date_creation__date__gte=date_debut)
        if date_fin:
            qs = qs.filter(date_creation__date__lte=date_fin)
        if utilisateur_filtre:
            qs = qs.filter(uploade_par_id=utilisateur_filtre)
        if recherche:
            qs = qs.filter(titre__icontains=recherche)

        paginator = Paginator(qs, self.per_page)
        page = paginator.get_page(request.GET.get('page', 1))

        categories = CategorieMedia.objects.all()

        return render(request, self.template_name, {
            'page_obj': page,
            'categories': categories,
            'type_filtre': type_filtre,
            'categorie_filtre': categorie_filtre,
            'date_debut': date_debut,
            'date_fin': date_fin,
            'utilisateur_filtre': utilisateur_filtre,
            'recherche': recherche,
            'total_resultats': paginator.count,
        })


@method_decorator(login_required, name='dispatch')
class MediaUploadView(View):
    template_name = 'medias/media_upload.html'

    def get(self, request):
        form = MediaUploadForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = MediaUploadForm(request.POST, request.FILES)
        if form.is_valid():
            media = form.save(commit=False)
            media.uploade_par = request.user
            media.save()
            messages.success(request, f"Média « {media.titre} » ajouté avec succès.")
            return redirect('medias:media-detail', pk=media.pk)
        return render(request, self.template_name, {'form': form})


@method_decorator(login_required, name='dispatch')
class MediaDetailView(DetailView):
    template_name = 'medias/media_detail.html'
    context_object_name = 'media'

    def get_queryset(self):
        return Media.objects.filter(deleted__isnull=True).select_related(
            'categorie', 'uploade_par'
        )


@method_decorator(login_required, name='dispatch')
class MediaUpdateView(UpdateView):
    template_name = 'medias/media_update.html'
    form_class = MediaUpdateForm
    context_object_name = 'media'

    def get_queryset(self):
        return Media.objects.filter(deleted__isnull=True)

    def form_valid(self, form):
        media = form.save()
        messages.success(self.request, f"Média « {media.titre} » mis à jour.")
        return redirect('medias:media-detail', pk=media.pk)

    def form_invalid(self, form):
        messages.error(self.request, "Veuillez corriger les erreurs ci-dessous.")
        return super().form_invalid(form)


@method_decorator(login_required, name='dispatch')
class MediaDeleteView(View):
    def post(self, request, pk):
        media = get_object_or_404(Media, pk=pk, deleted__isnull=True)
        titre = media.titre
        media.delete()
        messages.success(request, f"Média « {titre} » supprimé.")
        return redirect('medias:media-list')


@login_required
def media_delete_ajax(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    media = get_object_or_404(Media, pk=pk, deleted__isnull=True)
    titre = media.titre
    media.delete()
    return JsonResponse({'success': True, 'message': f'Média « {titre} » supprimé.'})
