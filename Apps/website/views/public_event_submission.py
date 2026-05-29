from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from Apps.events.forms import PublicEventSubmissionForm


class PublicEventSubmissionView(View):
    template_name = "public_event_submit.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "form": PublicEventSubmissionForm(),
            },
        )

    def post(self, request):
        form = PublicEventSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save()
            messages.success(
                request,
                (
                    f"Votre annonce '{event.titre}' a bien ete envoyee. "
                    "Elle sera relue par l'administration avant publication."
                ),
            )
            return redirect("website:event-submit")

        messages.error(
            request,
            "Impossible d'envoyer l'annonce. Verifiez les informations saisies.",
        )
        return render(
            request,
            self.template_name,
            {
                "form": form,
            },
        )
