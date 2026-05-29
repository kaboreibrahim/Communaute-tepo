from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from Apps.medias.forms import CategorieMediaForm
from Apps.medias.models import CategorieMedia


@method_decorator(login_required, name='dispatch')
class CategorieListView(ListView):
    template_name = 'medias/categorie_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return CategorieMedia.objects.annotate(
            nb_medias=Count('medias', filter=Q(medias__deleted__isnull=True))
        ).order_by('nom')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['form'] = CategorieMediaForm()
        return ctx


@method_decorator(login_required, name='dispatch')
class CategorieCreateView(View):
    def post(self, request):
        form = CategorieMediaForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Catégorie « {cat.nom} » créée.")
        else:
            for field_errors in form.errors.values():
                for err in field_errors:
                    messages.error(request, err)
        return redirect('medias:categorie-list')


@method_decorator(login_required, name='dispatch')
class CategorieUpdateView(View):
    template_name = 'medias/categorie_list.html'

    def post(self, request, pk):
        cat = get_object_or_404(CategorieMedia, pk=pk)
        form = CategorieMediaForm(request.POST, instance=cat)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Catégorie « {cat.nom} » modifiée.")
        else:
            for field_errors in form.errors.values():
                for err in field_errors:
                    messages.error(request, err)
        return redirect('medias:categorie-list')


@method_decorator(login_required, name='dispatch')
class CategorieDeleteView(View):
    def post(self, request, pk):
        cat = get_object_or_404(CategorieMedia, pk=pk)
        nom = cat.nom
        cat.delete()
        messages.success(request, f"Catégorie « {nom} » supprimée.")
        return redirect('medias:categorie-list')
