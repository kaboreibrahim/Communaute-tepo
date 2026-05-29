from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic.edit import FormView

from Apps.blog.forms import CommentaireForm, NewsletterForm
from Apps.blog.models import Article, Commentaire, Like, Newsletter


class CommenterView(View):
    def post(self, request, slug):
        article = get_object_or_404(
            Article,
            slug=slug,
            statut=Article.STATUT_PUBLIE,
            deleted__isnull=True,
        )
        form = CommentaireForm(request.POST, user=request.user)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = article
            if request.user.is_authenticated:
                comment.auteur = request.user
            parent_id = request.POST.get("parent_id")
            if parent_id:
                try:
                    import uuid
                    comment.parent = Commentaire.objects.get(
                        id=uuid.UUID(parent_id), article=article
                    )
                except (Commentaire.DoesNotExist, ValueError):
                    pass
            comment.save()
            messages.success(
                request,
                "Votre commentaire a été soumis et sera visible après validation.",
            )
        else:
            messages.error(request, "Erreur dans le formulaire. Veuillez vérifier vos informations.")
        return redirect("blog:article-detail", slug=slug)


class LikeToggleView(View):
    def post(self, request, slug):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Connexion requise"}, status=401)
        article = get_object_or_404(
            Article,
            slug=slug,
            statut=Article.STATUT_PUBLIE,
            deleted__isnull=True,
        )
        like, created = Like.objects.get_or_create(
            article=article, utilisateur=request.user
        )
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
        return JsonResponse(
            {"liked": liked, "count": article.nombre_likes}
        )


class NewsletterSubscribeView(View):
    def post(self, request):
        form = NewsletterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            nom = form.cleaned_data.get("nom", "")
            obj, created = Newsletter.objects.get_or_create(
                email=email,
                defaults={"nom": nom, "actif": True},
            )
            if created:
                messages.success(request, "Vous êtes maintenant abonné à notre newsletter !")
            else:
                if not obj.actif:
                    obj.actif = True
                    obj.save(update_fields=["actif"])
                    messages.success(request, "Votre abonnement a été réactivé.")
                else:
                    messages.info(request, "Vous êtes déjà abonné à notre newsletter.")
        else:
            messages.error(request, "Adresse email invalide.")
        referer = request.META.get("HTTP_REFERER", "/blog/")
        return redirect(referer)
