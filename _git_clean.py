import re, os, shutil

# Supprimer .history/
shutil.rmtree('.history', ignore_errors=True)

# Supprimer media/ (fichiers volumineux)
shutil.rmtree('media', ignore_errors=True)

# Nettoyer les secrets dans config/settings.py
f = 'config/settings.py'
if os.path.exists(f):
    content = open(f, encoding='utf-8', errors='ignore').read()
    # Supprimer le token Mapbox hardcodé
    content = re.sub(
        r"'pk\.eyJ1[A-Za-z0-9._-]*'",
        "''",
        content
    )
    # Supprimer le mot de passe email hardcodé
    content = re.sub(
        r"EMAIL_HOST_PASSWORD\s*=\s*'[^']*'",
        "EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')",
        content
    )
    content = re.sub(
        r"EMAIL_HOST_USER\s*=\s*'[^'@]*@[^']*'.*",
        "EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')",
        content
    )
    open(f, 'w', encoding='utf-8').write(content)
