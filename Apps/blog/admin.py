from django.contrib import admin
from .models import Article, Categorie, Commentaire, Like, Newsletter, Tag


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ["nom", "slug", "ordre", "nombre_articles", "date_creation"]
    prepopulated_fields = {"slug": ("nom",)}
    ordering = ["ordre", "nom"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["nom", "slug", "nombre_articles", "date_creation"]
    prepopulated_fields = {"slug": ("nom",)}


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["titre", "auteur", "categorie", "statut", "featured", "vues", "date_publication"]
    list_filter = ["statut", "featured", "categorie"]
    search_fields = ["titre", "contenu", "extrait"]
    prepopulated_fields = {"slug": ("titre",)}
    filter_horizontal = ["tags"]
    readonly_fields = ["vues", "date_creation", "date_maj"]
    date_hierarchy = "date_publication"


@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):
    list_display = ["article", "nom_affiche", "approuve", "date_creation"]
    list_filter = ["approuve"]
    actions = ["approuver", "rejeter"]

    @admin.action(description="Approuver les commentaires sélectionnés")
    def approuver(self, request, queryset):
        queryset.update(approuve=True)

    @admin.action(description="Rejeter les commentaires sélectionnés")
    def rejeter(self, request, queryset):
        queryset.update(approuve=False)


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ["utilisateur", "article", "date_creation"]


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ["email", "nom", "confirme", "actif", "date_inscription"]
    list_filter = ["actif", "confirme"]
    search_fields = ["email", "nom"]
