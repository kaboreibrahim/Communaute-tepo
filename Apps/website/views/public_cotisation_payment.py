from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from Apps.cotisations.models import ComptePaiement
from Apps.website.forms import PublicCotisationPaymentForm


class PublicCotisationPaymentView(View):
    template_name = "public_cotisation_payment.html"

    def _context(self, form):
        return {
            "form": form,
            "active_accounts": ComptePaiement.objects.filter(est_actif=True).order_by(
                "ordre_affichage",
                "mode",
                "nom_titulaire",
            ),
        }

    def get(self, request):
        initial = {}
        person_id = request.GET.get("personne", "").strip()
        cotisation_id = request.GET.get("cotisation", "").strip()
        if person_id:
            initial["personne"] = person_id
        if cotisation_id:
            initial["cotisation"] = cotisation_id
        return render(
            request,
            self.template_name,
            self._context(PublicCotisationPaymentForm(initial=initial)),
        )

    def post(self, request):
        form = PublicCotisationPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            paiement = form.save()
            messages.success(
                request,
                (
                    f"Le paiement pour {paiement.personne.nom_complet} a bien ete soumis. "
                    "Il reste en attente de verification par l'administration avant validation."
                ),
            )
            return redirect("website:cotisation-payment-submit")

        messages.error(
            request,
            "Impossible d'envoyer cette demande de paiement. Verifiez les informations saisies.",
        )
        return render(
            request,
            self.template_name,
            self._context(form),
        )
