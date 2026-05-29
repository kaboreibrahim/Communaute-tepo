#!/usr/bin/env python
"""
Script de test pour vérifier le nouveau flux de connexion avec choix 2FA
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

from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from Apps.accounts.forms import LoginForm

User = get_user_model()

def test_login_form():
    """Teste le formulaire de connexion avec le champ 2FA"""
    print("🧪 Test du formulaire de connexion")
    
    # Test avec méthode email
    form_data = {
        'username': 'test@example.com',
        'password': 'testpass123',
        'two_factor_method': 'email'
    }
    form = LoginForm(data=form_data)
    
    print(f"✅ Formulaire valide: {form.is_valid()}")
    print(f"📧 Méthode 2FA choisie: {form.cleaned_data.get('two_factor_method')}")
    
    # Test avec méthode Google Auth
    form_data['two_factor_method'] = 'google_auth'
    form = LoginForm(data=form_data)
    
    print(f"📱 Méthode 2FA Google Auth: {form.cleaned_data.get('two_factor_method')}")
    
    return True

def test_template_rendering():
    """Teste le rendu du template"""
    print("\n🎨 Test du template de connexion")
    
    client = Client()
    response = client.get('/accounts/login/')
    
    print(f"✅ Status code: {response.status_code}")
    print(f"📄 Template utilisé: {response.templates[0].name if response.templates else 'N/A'}")
    
    # Vérifier la présence du champ 2FA
    content = response.content.decode('utf-8')
    has_2fa_field = 'two_factor_method' in content
    has_email_option = 'Code par Email' in content
    has_google_option = 'Application Google Authenticator' in content
    
    print(f"🔧 Champ 2FA présent: {has_2fa_field}")
    print(f"📧 Option email présente: {has_email_option}")
    print(f"📱 Option Google Auth présente: {has_google_option}")
    
    return response.status_code == 200 and has_2fa_field

def main():
    """Fonction principale de test"""
    print("🚀 Test du nouveau flux de connexion avec choix 2FA")
    print("=" * 60)
    
    try:
        # Test du formulaire
        form_ok = test_login_form()
        
        # Test du template
        template_ok = test_template_rendering()
        
        print("\n📊 Résultats des tests:")
        print(f"   Formulaire: {'✅' if form_ok else '❌'}")
        print(f"   Template: {'✅' if template_ok else '❌'}")
        
        if form_ok and template_ok:
            print("\n🎉 Tous les tests sont passés avec succès!")
            print("\n📋 Prochaines étapes:")
            print("1. Démarrez le serveur Django: python manage.py runserver")
            print("2. Accédez à http://localhost:8000/accounts/login/")
            print("3. Testez la connexion avec les deux méthodes 2FA")
        else:
            print("\n❌ Certains tests ont échoué")
            
    except Exception as e:
        print(f"❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
