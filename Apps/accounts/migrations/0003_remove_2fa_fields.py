from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_add_google_auth_confirmed'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='utilisateur',
            name='two_factor_method',
        ),
        migrations.RemoveField(
            model_name='utilisateur',
            name='google_auth_secret',
        ),
        migrations.RemoveField(
            model_name='utilisateur',
            name='google_auth_confirmed',
        ),
        migrations.RemoveField(
            model_name='historicalutilisateur',
            name='two_factor_method',
        ),
        migrations.RemoveField(
            model_name='historicalutilisateur',
            name='google_auth_secret',
        ),
        migrations.RemoveField(
            model_name='historicalutilisateur',
            name='google_auth_confirmed',
        ),
    ]
