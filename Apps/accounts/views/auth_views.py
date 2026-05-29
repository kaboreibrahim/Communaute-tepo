from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect, render

from Apps.accounts.forms import LoginForm
from Apps.accounts.repositories.user_repository import UserRepository
from Apps.accounts.services.auth_service import AuthService


def connexion(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            next_url = request.POST.get("next") or request.GET.get("next")
            redirect_url = AuthService.complete_login(request, user, next_url)
            return redirect(redirect_url)
    else:
        form = LoginForm()

    return render(
        request,
        "connexion/login/login.html",
        {
            "form": form,
            "next": request.GET.get("next", ""),
        },
    )


def user_logout(request):
    user_was_authenticated = getattr(request.user, "is_authenticated", False)
    user_name = (
        UserRepository.get_user_display_name(request.user)
        if user_was_authenticated
        else ""
    )
    logout(request)
    if user_was_authenticated:
        messages.success(request, f"Au revoir {user_name} ! Vous etes deconnecte.")
    return redirect("website:accueil")
