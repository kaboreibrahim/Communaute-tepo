from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from Apps.villages.models import Village

User = get_user_model()


class PasswordInputWithToggle(forms.PasswordInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["id"] = "password-input"


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "class": "field-input w-full pl-10 pr-4 h-13 py-4 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm placeholder:text-slate-300",
                "placeholder": "nom.prenom@gouv.ci",
                "id": "username",
                "autocomplete": "email",
                "inputmode": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=PasswordInputWithToggle(
            attrs={
                "class": "field-input w-full pl-10 pr-12 h-13 py-4 rounded-xl border border-slate-200 bg-slate-50 text-slate-800 text-sm placeholder:text-slate-300",
                "placeholder": "........",
                "autocomplete": "current-password",
            }
        ),
    )



class DashboardUserCreationForm(forms.ModelForm):
    temporary_password = forms.CharField(
        label="Mot de passe provisoire",
        min_length=8,
        widget=PasswordInputWithToggle(
            attrs={
                "class": "w-full h-14 rounded-lg border border-slate-200 bg-slate-50 px-4 pr-12 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                "placeholder": "............",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "telephone",
            "photo_profil",
            "role",
            "village",
            "is_verified",
            "is_active",
        ]
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "w-full h-14 rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                    "placeholder": "j.dupont",
                    "autocomplete": "username",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full h-14 rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                    "placeholder": "jean.dupont@olodio.gov",
                    "autocomplete": "email",
                }
            ),
            "telephone": forms.TextInput(
                attrs={
                    "class": "w-full h-14 rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10",
                    "placeholder": "+225 XX XX XX XX XX",
                    "autocomplete": "tel",
                }
            ),
            "photo_profil": forms.ClearableFileInput(
                attrs={
                    "class": "hidden",
                    "accept": "image/*",
                }
            ),
            "role": forms.Select(
                attrs={
                    "class": "w-full h-14 rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10 appearance-none",
                }
            ),
            "village": forms.Select(
                attrs={
                    "class": "w-full h-14 rounded-lg border border-slate-200 bg-slate-50 px-4 text-sm text-slate-800 outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/10 appearance-none",
                }
            ),
            "is_verified": forms.CheckboxInput(
                attrs={
                    "class": "h-5 w-5 rounded border-slate-300 text-primary focus:ring-primary/20",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "h-5 w-5 rounded border-slate-300 text-primary focus:ring-primary/20",
                }
            ),
        }
        labels = {
            "username": "Nom d'utilisateur",
            "email": "Email officiel",
            "telephone": "Telephone",
            "photo_profil": "Photo de profil",
            "role": "Role",
            "village": "Village de rattachement",
            "is_verified": "Email verifie",
            "is_active": "Acces actif",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self.fields["telephone"].required = False
        self.fields["photo_profil"].required = False
        self.fields["village"].required = False
        self.fields["village"].queryset = Village.objects.filter(
            deleted__isnull=True
        ).order_by("nom")
        self.fields["village"].empty_label = "Selectionner un village..."
        self.fields["is_verified"].required = False
        self.fields["is_active"].required = False
        self.fields["is_active"].initial = True

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("L'email officiel est obligatoire.")
        if User.objects.filter(email__iexact=email, deleted__isnull=True).exists():
            raise forms.ValidationError("Un utilisateur avec cet email existe deja.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("Le nom d'utilisateur est obligatoire.")
        if User.objects.filter(
            username__iexact=username,
            deleted__isnull=True,
        ).exists():
            raise forms.ValidationError(
                "Un utilisateur avec ce nom d'utilisateur existe deja."
            )
        return username

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data["temporary_password"]
        user.email = self.cleaned_data["email"]
        user.set_password(password)
        user.is_staff = user.role == "admin"
        if commit:
            user.save()
        return user
