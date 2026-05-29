from django.urls import path
from .views.accueil import AccueilView
from .views.public_person_registration import PublicPersonRegistrationView
from .views.public_event_submission import PublicEventSubmissionView
from .views.public_cotisation_payment import PublicCotisationPaymentView
from .views.public_media import PublicMediaView
from .views.public_evenements import (
    EvenementListView,
    EvenementDetailView,
    EvenementByTypeView,
)
from django.views.i18n import set_language
from django.shortcuts import redirect

app_name = 'website'

urlpatterns = [
    path('', lambda request: redirect('/accueil/', permanent=True)),
    path('accueil/', AccueilView.as_view(), name='accueil'),
    path('galerie/', PublicMediaView.as_view(), name='galerie'),
    path('inscription/', PublicPersonRegistrationView.as_view(), name='person-register'),
    path('annonces/soumettre/', PublicEventSubmissionView.as_view(), name='event-submit'),
    path('cotisations/payer/', PublicCotisationPaymentView.as_view(), name='cotisation-payment-submit'),
    path('set_language/', set_language, name='set_language'),
    # Événements publics
    path('evenements/', EvenementListView.as_view(), name='evenement-list'),
    path('evenements/<int:pk>/', EvenementDetailView.as_view(), name='evenement-detail'),
    path('evenements/type/<slug:type_slug>/', EvenementByTypeView.as_view(), name='evenement-type'),
]
