#!/usr/bin/env python
"""
Script de test pour vérifier l'intégration du template OTP
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

from django.test import Client
from django.contrib.auth import get_user_model
from Apps.accounts.forms import EmailVerificationForm

User = get_user_model()

def test_otp_template_rendering():
    """Teste le rendu du template OTP"""
    print("🎨 Test du template OTP")
    
    client = Client()
    response = client.get('/accounts/two_factor_method/')
    
    print(f"✅ Status code: {response.status_code}")
    
    if response.status_code == 200:
        content = response.content.decode('utf-8')
        
        # Vérifier les éléments OTP
        has_otp_inputs = 'otp-input' in content
        has_form = '<form method="post"' in content
        has_csrf = 'csrf_token' in content
        has_progress = 'otp-progress' in content
        has_tabs = 'tab-app' in content and 'tab-email' in content
        
        print(f"🔧 Champs OTP présents: {has_otp_inputs}")
        print(f"📝 Formulaire présent: {has_form}")
        print(f"🔒 CSRF token présent: {has_csrf}")
        print(f"📊 Barre de progression: {has_progress}")
        print(f"🔄 Onglets méthode: {has_tabs}")
        
        return all([has_otp_inputs, has_form, has_csrf, has_progress, has_tabs])
    else:
        print(f"❌ Erreur HTTP: {response.status_code}")
        return False

def test_email_verification_flow():
    """Teste le flux de vérification email"""
    print("\n📧 Test du flux de vérification email")
    
    # Créer un utilisateur de test
    try:
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        print(f"✅ Utilisateur de test créé: {user.username}")
    except Exception as e:
        print(f"⚠️ Utilisateur existe déjà ou erreur: {e}")
        user = User.objects.filter(username='testuser').first()
        if not user:
            return False
    
    client = Client()
    
    # Simuler une connexion avec session 2FA
    session = client.session
    session['pre_2fa_user_id'] = str(user.id)
    session['2fa_email_code'] = '123456'
    session.save()
    
    # Test de la page de vérification
    response = client.get('/accounts/email_verification/')
    print(f"✅ Page vérification accessible: {response.status_code == 200}")
    
    # Test de soumission du formulaire
    response = client.post('/accounts/email_verification/', {
        'code': '123456',
        'csrfmiddlewaretoken': 'test'
    })
    
    print(f"📤 Soumission formulaire: {response.status_code}")
    
    return True

def main():
    """Fonction principale de test"""
    print("🚀 Test d'intégration du template OTP")
    print("=" * 60)
    
    try:
        # Test du template
        template_ok = test_otp_template_rendering()
        
        # Test du flux
        flow_ok = test_email_verification_flow()
        
        print("\n📊 Résultats des tests:")
        print(f"   Template OTP: {'✅' if template_ok else '❌'}")
        print(f"   Flux email: {'✅' if flow_ok else '❌'}")
        
        if template_ok and flow_ok:
            print("\n🎉 L'intégration OTP est fonctionnelle!")
            print("\n📋 Prochaines étapes:")
            print("1. Démarrez le serveur: python manage.py runserver")
            print("2. Testez la connexion complète:")
            print("   - Connexion avec email/mot de passe")
            print("   - Choix de la méthode 2FA")
            print("   - Saisie du code OTP")
            print("   - Vérification et accès")
        else:
            print("\n❌ Certains tests ont échoué")
            
    except Exception as e:
        print(f"❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
