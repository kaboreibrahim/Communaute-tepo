from django.contrib import admin
from .models import CategorieMedia, Media


@admin.register(CategorieMedia)
class CategorieMediaAdmin(admin.ModelAdmin):
    list_display = ('nom', 'slug', 'nombre_medias', 'date_creation')
    search_fields = ('nom',)
    prepopulated_fields = {'slug': ('nom',)}


@admin.register(Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type_media', 'categorie', 'format_fichier',
                    'taille_affichage', 'uploade_par', 'date_creation')
    list_filter = ('type_media', 'categorie', 'format_fichier')
    search_fields = ('titre', 'description')
    readonly_fields = ('id', 'taille_fichier', 'largeur', 'hauteur',
                       'format_fichier', 'date_creation', 'date_maj')
    raw_id_fields = ('uploade_par',)
