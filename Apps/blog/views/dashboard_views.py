from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, TemplateView
from django.views.generic.edit import CreateView, UpdateView

from Apps.blog.forms import ArticleForm, CategorieForm, TagForm
from Apps.blog.models import Article, Categorie, Commentaire, Newsletter, Tag


@method_decorator(login_required, name="dispatch")
class BlogDashboardView(TemplateView):
    template_name = "blog/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        now = timezone.now()
        total = Article.objects.filter(deleted__isnull=True).count()
        publies = Article.objects.filter(
            statut=Article.STATUT_PUBLIE,
            date_publication__lte=now,
            deleted__isnull=True,
        ).count()
        brouillons = Article.objects.filter(
            statut=Article.STATUT_BROUILLON, deleted__isnull=True
        ).count()
        total_vues = sum(
            Article.objects.filter(deleted__isnull=True).values_list("vues", flat=True)
        )
        commentaires_en_attente = Commentaire.objects.filter(
            approuve=False, deleted__isnull=True
        ).count()
        abonnes_newsletter = Newsletter.objects.filter(actif=True).count()
        recents = (
            Article.objects.filter(deleted__isnull=True)
            .select_related("auteur", "categorie")
            .order_by("-date_creation")[:8]
        )
        categories_stats = (
            Categorie.objects.annotate(
                nb=Count(
                    "articles",
                    filter=Q(
                        articles__deleted__isnull=True,
                        articles__statut=Article.STATUT_PUBLIE,
                    ),
                )
            ).order_by("-nb")[:6]
        )
        ctx.update(
            {
                "total_articles": total,
                "articles_publies": publies,
                "articles_brouillons": brouillons,
                "total_vues": total_vues,
                "commentaires_en_attente": commentaires_en_attente,
                "abonnes_newsletter": abonnes_newsletter,
                "articles_recents": recents,
                "categories_stats": categories_stats,
            }
        )
        return ctx


@method_decorator(login_required, name="dispatch")
class ArticleListAdminView(ListView):
    model = Article
    template_name = "blog/article_list_admin.html"
    context_object_name = "articles"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Article.objects.filter(deleted__isnull=True)
            .select_related("auteur", "categorie")
            .order_by("-date_creation")
        )
        statut = self.request.GET.get("statut", "")
        cat = self.request.GET.get("categorie", "")
        q = self.request.GET.get("q", "").strip()
        if statut:
            qs = qs.filter(statut=statut)
        if cat:
            qs = qs.filter(categorie__slug=cat)
        if q:
            qs = qs.filter(Q(titre__icontains=q) | Q(extrait__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Categorie.objects.all()
        ctx["statuts"] = Article.STATUT_CHOICES
        ctx["filtre_statut"] = self.request.GET.get("statut", "")
        ctx["filtre_categorie"] = self.request.GET.get("categorie", "")
        ctx["q"] = self.request.GET.get("q", "")
        return ctx


@method_decorator(login_required, name="dispatch")
class ArticleCreateView(CreateView):
    model = Article
    form_class = ArticleForm
    template_name = "blog/article_form.html"

    def form_valid(self, form):
        article = form.save(commit=False)
        article.auteur = self.request.user
        article.save()
        form.save_m2m()
        messages.success(self.request, f"Article «{article.titre}» créé avec succès.")
        return redirect("dashbord:blog-article-list")

    def form_invalid(self, form):
        messages.error(self.request, "Veuillez corriger les erreurs dans le formulaire.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["action"] = "Créer"
        ctx["tags_disponibles"] = Tag.objects.all()
        ctx["categories"] = Categorie.objects.all()
        return ctx


@method_decorator(login_required, name="dispatch")
class ArticleUpdateView(UpdateView):
    model = Article
    form_class = ArticleForm
    template_name = "blog/article_form.html"

    def get_queryset(self):
        return Article.objects.filter(deleted__isnull=True)

    def form_valid(self, form):
        article = form.save()
        messages.success(self.request, f"Article «{article.titre}» mis à jour.")
        return redirect("dashbord:blog-article-list")

    def form_invalid(self, form):
        messages.error(self.request, "Veuillez corriger les erreurs dans le formulaire.")
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["action"] = "Modifier"
        ctx["tags_disponibles"] = Tag.objects.all()
        ctx["categories"] = Categorie.objects.all()
        return ctx


@method_decorator(login_required, name="dispatch")
class ArticleDeleteView(View):
    def post(self, request, pk):
        article = get_object_or_404(Article, pk=pk, deleted__isnull=True)
        titre = article.titre
        article.delete()
        messages.success(request, f"Article «{titre}» supprimé.")
        return redirect("dashbord:blog-article-list")


@method_decorator(login_required, name="dispatch")
class ArticlePublierView(View):
    def post(self, request, pk):
        article = get_object_or_404(Article, pk=pk, deleted__isnull=True)
        if article.statut == Article.STATUT_PUBLIE:
            article.statut = Article.STATUT_BROUILLON
            article.save(update_fields=["statut"])
            messages.info(request, f"Article «{article.titre}» repassé en brouillon.")
        else:
            article.statut = Article.STATUT_PUBLIE
            if not article.date_publication:
                article.date_publication = timezone.now()
            article.save(update_fields=["statut", "date_publication"])
            messages.success(request, f"Article «{article.titre}» publié.")
        return redirect("dashbord:blog-article-list")


@method_decorator(login_required, name="dispatch")
class CommentaireListView(ListView):
    model = Commentaire
    template_name = "blog/commentaire_list.html"
    context_object_name = "commentaires"
    paginate_by = 30

    def get_queryset(self):
        qs = (
            Commentaire.objects.filter(deleted__isnull=True)
            .select_related("article", "auteur")
            .order_by("-date_creation")
        )
        filtre = self.request.GET.get("filtre", "")
        if filtre == "attente":
            qs = qs.filter(approuve=False)
        elif filtre == "approuve":
            qs = qs.filter(approuve=True)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["en_attente"] = Commentaire.objects.filter(approuve=False, deleted__isnull=True).count()
        ctx["filtre"] = self.request.GET.get("filtre", "")
        return ctx


@method_decorator(login_required, name="dispatch")
class CommentaireApprouverView(View):
    def post(self, request, pk):
        commentaire = get_object_or_404(Commentaire, pk=pk, deleted__isnull=True)
        commentaire.approuve = True
        commentaire.save(update_fields=["approuve"])
        messages.success(request, "Commentaire approuvé.")
        return redirect("dashbord:blog-commentaire-list")


@method_decorator(login_required, name="dispatch")
class CommentaireRejeterView(View):
    def post(self, request, pk):
        commentaire = get_object_or_404(Commentaire, pk=pk, deleted__isnull=True)
        commentaire.delete()
        messages.success(request, "Commentaire supprimé.")
        return redirect("dashbord:blog-commentaire-list")


@method_decorator(login_required, name="dispatch")
class NewsletterListView(ListView):
    model = Newsletter
    template_name = "blog/newsletter_list.html"
    context_object_name = "abonnes"
    paginate_by = 30

    def get_queryset(self):
        qs = Newsletter.objects.all().order_by("-date_inscription")
        filtre = self.request.GET.get("filtre", "")
        if filtre == "actif":
            qs = qs.filter(actif=True)
        elif filtre == "inactif":
            qs = qs.filter(actif=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["total_actifs"] = Newsletter.objects.filter(actif=True).count()
        ctx["filtre"] = self.request.GET.get("filtre", "")
        return ctx


@method_decorator(login_required, name="dispatch")
class CategorieListView(ListView):
    model = Categorie
    template_name = "blog/categorie_list.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Categorie.objects.annotate(
            nb=Count(
                "articles",
                filter=Q(
                    articles__deleted__isnull=True,
                    articles__statut=Article.STATUT_PUBLIE,
                ),
            )
        ).order_by("ordre", "nom")


@method_decorator(login_required, name="dispatch")
class CategorieCreateView(CreateView):
    model = Categorie
    form_class = CategorieForm
    template_name = "blog/categorie_form.html"

    def form_valid(self, form):
        cat = form.save()
        messages.success(self.request, f"Catégorie «{cat.nom}» créée.")
        return redirect("dashbord:blog-categorie-list")


@method_decorator(login_required, name="dispatch")
class CategorieUpdateView(UpdateView):
    model = Categorie
    form_class = CategorieForm
    template_name = "blog/categorie_form.html"

    def form_valid(self, form):
        cat = form.save()
        messages.success(self.request, f"Catégorie «{cat.nom}» mise à jour.")
        return redirect("dashbord:blog-categorie-list")


@method_decorator(login_required, name="dispatch")
class CategorieDeleteView(View):
    def post(self, request, pk):
        cat = get_object_or_404(Categorie, pk=pk)
        nom = cat.nom
        cat.delete()
        messages.success(request, f"Catégorie «{nom}» supprimée.")
        return redirect("dashbord:blog-categorie-list")


@method_decorator(login_required, name="dispatch")
class TagListView(ListView):
    model = Tag
    template_name = "blog/tag_list.html"
    context_object_name = "tags"

    def get_queryset(self):
        return Tag.objects.annotate(
            nb=Count(
                "articles",
                filter=Q(
                    articles__deleted__isnull=True,
                    articles__statut=Article.STATUT_PUBLIE,
                ),
            )
        ).order_by("nom")


@method_decorator(login_required, name="dispatch")
class TagCreateView(CreateView):
    model = Tag
    form_class = TagForm
    template_name = "blog/tag_form.html"

    def form_valid(self, form):
        tag = form.save()
        messages.success(self.request, f"Tag «{tag.nom}» créé.")
        return redirect("dashbord:blog-tag-list")


@method_decorator(login_required, name="dispatch")
class TagDeleteView(View):
    def post(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        nom = tag.nom
        tag.delete()
        messages.success(request, f"Tag «{nom}» supprimé.")
        return redirect("dashbord:blog-tag-list")
