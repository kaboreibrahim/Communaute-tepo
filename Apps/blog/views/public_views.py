from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import DetailView, ListView

from Apps.blog.forms import CommentaireForm, NewsletterForm, RechercheForm
from Apps.blog.models import Article, Categorie, Tag


class ArticleListView(ListView):
    model = Article
    template_name = "blog/article_list.html"
    context_object_name = "articles"
    paginate_by = 9

    def get_queryset(self):
        qs = (
            Article.objects.filter(
                statut=Article.STATUT_PUBLIE,
                date_publication__lte=timezone.now(),
                deleted__isnull=True,
            )
            .select_related("auteur", "categorie")
            .prefetch_related("tags")
            .order_by("-featured", "-date_publication")
        )
        cat_slug = self.request.GET.get("categorie")
        tag_slug = self.request.GET.get("tag")
        q = self.request.GET.get("q", "").strip()
        if cat_slug:
            qs = qs.filter(categorie__slug=cat_slug)
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        if q:
            qs = qs.filter(
                Q(titre__icontains=q) | Q(extrait__icontains=q) | Q(contenu__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Categorie.objects.all().order_by("ordre", "nom")
        ctx["tags_populaires"] = Tag.objects.all()[:20]
        ctx["articles_recents"] = (
            Article.objects.filter(
                statut=Article.STATUT_PUBLIE,
                date_publication__lte=timezone.now(),
                deleted__isnull=True,
            )
            .select_related("auteur")
            .order_by("-date_publication")[:5]
        )
        ctx["articles_populaires"] = (
            Article.objects.filter(
                statut=Article.STATUT_PUBLIE,
                date_publication__lte=timezone.now(),
                deleted__isnull=True,
            )
            .order_by("-vues")[:5]
        )
        ctx["newsletter_form"] = NewsletterForm()
        ctx["recherche_form"] = RechercheForm(self.request.GET or None)
        ctx["categorie_active"] = self.request.GET.get("categorie", "")
        ctx["tag_actif"] = self.request.GET.get("tag", "")
        ctx["q"] = self.request.GET.get("q", "")
        ctx["total_articles"] = Article.objects.filter(
            statut=Article.STATUT_PUBLIE,
            date_publication__lte=timezone.now(),
            deleted__isnull=True,
        ).count()
        return ctx


class ArticleDetailView(DetailView):
    model = Article
    template_name = "blog/article_detail.html"
    context_object_name = "article"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Article.objects.filter(deleted__isnull=True)
            .select_related("auteur", "categorie")
            .prefetch_related("tags")
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.est_publie:
            from django.http import Http404
            raise Http404
        return obj

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        self.object.incrementer_vues()
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        article = self.object
        ctx["commentaires"] = (
            article.commentaires.filter(approuve=True, parent__isnull=True, deleted__isnull=True)
            .select_related("auteur")
            .prefetch_related("reponses__auteur")
            .order_by("date_creation")
        )
        ctx["commentaire_form"] = CommentaireForm(user=self.request.user)
        ctx["newsletter_form"] = NewsletterForm()
        user_a_like = False
        if self.request.user.is_authenticated:
            user_a_like = article.likes.filter(utilisateur=self.request.user).exists()
        ctx["user_a_like"] = user_a_like
        ctx["articles_similaires"] = (
            Article.objects.filter(
                statut=Article.STATUT_PUBLIE,
                date_publication__lte=timezone.now(),
                deleted__isnull=True,
                categorie=article.categorie,
            )
            .exclude(pk=article.pk)
            .select_related("auteur", "categorie")
            .order_by("-date_publication")[:3]
        )
        ctx["categories"] = Categorie.objects.all().order_by("ordre", "nom")
        ctx["articles_recents"] = (
            Article.objects.filter(
                statut=Article.STATUT_PUBLIE,
                date_publication__lte=timezone.now(),
                deleted__isnull=True,
            )
            .exclude(pk=article.pk)
            .select_related("auteur")
            .order_by("-date_publication")[:5]
        )
        return ctx


class ArticleByCategorieView(ArticleListView):
    template_name = "blog/article_list.html"

    def get_queryset(self):
        self.categorie = get_object_or_404(Categorie, slug=self.kwargs["slug"])
        qs = (
            Article.objects.filter(
                statut=Article.STATUT_PUBLIE,
                date_publication__lte=timezone.now(),
                deleted__isnull=True,
                categorie=self.categorie,
            )
            .select_related("auteur", "categorie")
            .prefetch_related("tags")
            .order_by("-date_publication")
        )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categorie_courante"] = self.categorie
        ctx["titre_filtre"] = f"Catégorie : {self.categorie.nom}"
        return ctx


class ArticleByTagView(ArticleListView):
    template_name = "blog/article_list.html"

    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs["slug"])
        qs = (
            Article.objects.filter(
                statut=Article.STATUT_PUBLIE,
                date_publication__lte=timezone.now(),
                deleted__isnull=True,
                tags=self.tag,
            )
            .select_related("auteur", "categorie")
            .prefetch_related("tags")
            .order_by("-date_publication")
        )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tag_courant"] = self.tag
        ctx["titre_filtre"] = f"Tag : #{self.tag.nom}"
        return ctx


class RechercheView(ArticleListView):
    template_name = "blog/article_list.html"

    def get_queryset(self):
        q = self.request.GET.get("q", "").strip()
        if not q:
            return Article.objects.none()
        return (
            Article.objects.filter(
                statut=Article.STATUT_PUBLIE,
                date_publication__lte=timezone.now(),
                deleted__isnull=True,
            )
            .filter(Q(titre__icontains=q) | Q(extrait__icontains=q) | Q(contenu__icontains=q))
            .select_related("auteur", "categorie")
            .prefetch_related("tags")
            .order_by("-date_publication")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["titre_filtre"] = f"Recherche : « {ctx['q']} »"
        return ctx
