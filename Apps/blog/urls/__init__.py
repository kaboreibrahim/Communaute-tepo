from django.urls import path
from Apps.blog.views import (
    ArticleListView,
    ArticleDetailView,
    ArticleByCategorieView,
    ArticleByTagView,
    RechercheView,
    CommenterView,
    LikeToggleView,
    NewsletterSubscribeView,
)

app_name = "blog"

urlpatterns = [
    path("", ArticleListView.as_view(), name="article-list"),
    path("recherche/", RechercheView.as_view(), name="recherche"),
    path("newsletter/souscrire/", NewsletterSubscribeView.as_view(), name="newsletter-subscribe"),
    path("categorie/<slug:slug>/", ArticleByCategorieView.as_view(), name="categorie"),
    path("tag/<slug:slug>/", ArticleByTagView.as_view(), name="tag"),
    path("<slug:slug>/", ArticleDetailView.as_view(), name="article-detail"),
    path("<slug:slug>/commenter/", CommenterView.as_view(), name="commenter"),
    path("<slug:slug>/like/", LikeToggleView.as_view(), name="like-toggle"),
]
