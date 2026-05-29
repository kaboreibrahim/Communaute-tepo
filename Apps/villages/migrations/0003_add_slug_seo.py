from django.db import migrations, models
from django.utils.text import slugify


def populate_village_slugs(apps, schema_editor):
    Village = apps.get_model('villages', 'Village')
    seen = {}
    for village in Village.objects.all().order_by('nom'):
        base = slugify(village.nom) or f"village-{village.pk}"
        slug = base
        counter = 1
        while slug in seen or Village.objects.filter(slug=slug).exclude(pk=village.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        seen[slug] = True
        village.slug = slug
        village.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('villages', '0002_village_created_by'),
    ]

    operations = [
        # db_index=False évite un index LIKE en double lors de l'AlterField suivant
        migrations.AddField(
            model_name='village',
            name='slug',
            field=models.SlugField(blank=True, max_length=120, default='', db_index=False),
            preserve_default=False,
        ),
        migrations.RunPython(populate_village_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='village',
            name='slug',
            field=models.SlugField(blank=True, max_length=120, unique=True),
        ),
    ]
