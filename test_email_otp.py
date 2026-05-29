#!/usr/bin/env python
"""
Script de test pour envoyer un email OTP de vérification
"""
import os
import sys
import django
from pathlib import Path

# Configuration de l'environnement Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import random

def generate_otp_code():
    """Génère un code OTP à 6 chiffres"""
    return str(random.randint(100000, 999999))

def send_test_otp_email():
    """Teste l'envoi d'un email OTP"""
    
    # Email de test (à remplacer par l'email réel de l'utilisateur)
    test_email = "empotageoilsofafrica@gmail.com"  # Changez ceci
    
    # Générer un code OTP
    code = generate_otp_code()
    
    print(f"🔢 Code OTP généré: {code}")
    print(f"📧 Email de destination: {test_email}")
    
    try:
        # Contexte pour le template
        context = {
            "code": code,
            "user": type('User', (), {
                'get_full_name': lambda: "Utilisateur Test",
                'username': "testuser"
            })(),
            "logo_url": f"http://localhost:8000/static/images/logo.png",
            "site_name": getattr(settings, "SITE_NAME", "Olodio Platform"),
            "support_email": getattr(settings, "SUPPORT_EMAIL", "contact@olodio-pref.ci"),
            "support_url": "http://localhost:8000",
        }
        
        # Rendre le template HTML
        html_content = render_to_string("emails/2fa_verification.html", context)
        text_content = strip_tags(html_content)
        
        # Créer l'email
        email = EmailMultiAlternatives(
            subject=f"{context['site_name']} - Code de verification de connexion",
            body=text_content,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
            to=[test_email],
        )
        email.attach_alternative(html_content, "text/html")
        
        # Envoyer l'email
        sent_count = email.send()
        
        if sent_count == 1:
            print("✅ Email OTP envoyé avec succès!")
            print(f"📬 Vérifiez votre boîte de réception: {test_email}")
            print(f"🔑 Le code à utiliser est: {code}")
        else:
            print("❌ L'email n'a pas pu être envoyé")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'email: {e}")
        import traceback
        traceback.print_exc()

def test_email_configuration():
    """Teste la configuration email"""
    print("🔧 Configuration Email:")
    print(f"   Backend: {settings.EMAIL_BACKEND}")
    print(f"   Host: {settings.EMAIL_HOST}")
    print(f"   Port: {settings.EMAIL_PORT}")
    print(f"   Use TLS: {settings.EMAIL_USE_TLS}")
    print(f"   Host User: {settings.EMAIL_HOST_USER}")
    print(f"   From Email: {settings.DEFAULT_FROM_EMAIL}")
    print()

if __name__ == "__main__":
    print("🧪 Test d'envoi d'email OTP pour Olodio Platform")
    print("=" * 50)
    
    test_email_configuration()
    send_test_otp_email()
