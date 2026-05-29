from django.db import migrations, models
from django.utils.text import slugify


def populate_event_slugs(apps, schema_editor):
    Event = apps.get_model('events', 'Event')
    seen = {}
    for event in Event.objects.all().order_by('id'):
        base = slugify(event.titre) or f"evenement-{event.pk}"
        slug = base
        counter = 1
        while slug in seen or Event.objects.filter(slug=slug).exclude(pk=event.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        seen[slug] = True
        event.slug = slug
        event.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0004_typeevenement_alter_event_type'),
    ]

    operations = [
        # db_index=False évite un index LIKE en double lors de l'AlterField suivant
        migrations.AddField(
            model_name='event',
            name='slug',
            field=models.SlugField(blank=True, max_length=220, default='', db_index=False),
            preserve_default=False,
        ),
        migrations.RunPython(populate_event_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='event',
            name='slug',
            field=models.SlugField(blank=True, max_length=220, unique=True),
        ),
    ]
