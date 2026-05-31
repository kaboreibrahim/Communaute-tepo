from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('villages', '0003_add_slug_seo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='village',
            name='population_estimee',
        ),
    ]
