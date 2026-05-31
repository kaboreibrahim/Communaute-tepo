from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from Apps.website.models import AccueilImage


@method_decorator(login_required, name="dispatch")
class AccueilImageListView(View):
    template_name = "website_images/liste.html"

    def get(self, request):
        hero_images = AccueilImage.objects.filter(section="hero").order_by("ordre", "-date_creation")
        about_images = AccueilImage.objects.filter(section="about").order_by("ordre", "-date_creation")
        return render(request, self.template_name, {
            "title": "Images du site web",
            "hero_images": hero_images,
            "about_images": about_images,
            "total_hero": hero_images.count(),
            "total_about": about_images.count(),
        })


@method_decorator(login_required, name="dispatch")
class AccueilImageCreateView(View):
    template_name = "website_images/formulaire.html"

    def get(self, request):
        section = request.GET.get("section", "hero")
        return render(request, self.template_name, {
            "title": "Ajouter une image",
            "action": "create",
            "section_defaut": section,
        })

    def post(self, request):
        section = request.POST.get("section", "hero")
        titre = request.POST.get("titre", "").strip()
        sous_titre = request.POST.get("sous_titre", "").strip()
        texte_alt = request.POST.get("texte_alt", "").strip()
        image_url = request.POST.get("image_url", "").strip()
        ordre = request.POST.get("ordre", "0").strip() or "0"
        est_active = request.POST.get("est_active") == "on"
        image_file = request.FILES.get("image")

        errors = {}
        if section not in ("hero", "about"):
            errors["section"] = "Section invalide."
        if not image_file and not image_url:
            errors["image"] = "Ajoutez un fichier image ou renseignez une URL d'image."
        try:
            ordre_val = int(ordre)
        except ValueError:
            ordre_val = 0
            errors["ordre"] = "L'ordre doit être un nombre entier."

        if errors:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
            return render(request, self.template_name, {
                "title": "Ajouter une image",
                "action": "create",
                "errors": errors,
                "form_data": request.POST,
                "section_defaut": section,
            })

        obj = AccueilImage(
            section=section,
            titre=titre,
            sous_titre=sous_titre,
            texte_alt=texte_alt,
            image_url=image_url,
            ordre=ordre_val,
            est_active=est_active,
        )
        if image_file:
            obj.image = image_file
        obj.save()

        messages.success(request, f"Image « {obj} » ajoutée avec succès.")
        return redirect("dashbord:site-images-list")


@method_decorator(login_required, name="dispatch")
class AccueilImageUpdateView(View):
    template_name = "website_images/formulaire.html"

    def get(self, request, pk):
        obj = get_object_or_404(AccueilImage, pk=pk)
        return render(request, self.template_name, {
            "title": "Modifier l'image",
            "action": "update",
            "obj": obj,
        })

    def post(self, request, pk):
        obj = get_object_or_404(AccueilImage, pk=pk)
        section = request.POST.get("section", obj.section)
        titre = request.POST.get("titre", "").strip()
        sous_titre = request.POST.get("sous_titre", "").strip()
        texte_alt = request.POST.get("texte_alt", "").strip()
        image_url = request.POST.get("image_url", "").strip()
        ordre = request.POST.get("ordre", "0").strip() or "0"
        est_active = request.POST.get("est_active") == "on"
        image_file = request.FILES.get("image")
        supprimer_image = request.POST.get("supprimer_image") == "on"

        errors = {}
        if section not in ("hero", "about"):
            errors["section"] = "Section invalide."
        try:
            ordre_val = int(ordre)
        except ValueError:
            ordre_val = obj.ordre
            errors["ordre"] = "L'ordre doit être un nombre entier."

        has_image_after = (
            (obj.image and not supprimer_image) or image_file or image_url
        )
        if not has_image_after:
            errors["image"] = "Ajoutez un fichier image ou renseignez une URL d'image."

        if errors:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")
            return render(request, self.template_name, {
                "title": "Modifier l'image",
                "action": "update",
                "obj": obj,
                "errors": errors,
                "form_data": request.POST,
            })

        obj.section = section
        obj.titre = titre
        obj.sous_titre = sous_titre
        obj.texte_alt = texte_alt
        obj.image_url = image_url
        obj.ordre = ordre_val
        obj.est_active = est_active

        if supprimer_image and obj.image:
            obj.image.delete(save=False)
            obj.image = None
        if image_file:
            if obj.image:
                obj.image.delete(save=False)
            obj.image = image_file

        obj.save()
        messages.success(request, f"Image « {obj} » mise à jour avec succès.")
        return redirect("dashbord:site-images-list")


@method_decorator(login_required, name="dispatch")
class AccueilImageDeleteView(View):
    def post(self, request, pk):
        obj = get_object_or_404(AccueilImage, pk=pk)
        label = str(obj)
        if obj.image:
            obj.image.delete(save=False)
        obj.delete()

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True, "message": f"Image « {label} » supprimée."})

        messages.success(request, f"Image « {label} » supprimée.")
        return redirect("dashbord:site-images-list")


@method_decorator(login_required, name="dispatch")
class AccueilImageToggleView(View):
    def post(self, request, pk):
        obj = get_object_or_404(AccueilImage, pk=pk)
        obj.est_active = not obj.est_active
        obj.save(update_fields=["est_active"])
        return JsonResponse({"success": True, "est_active": obj.est_active})
