from django.db import migrations, models
from django.db.models import Q


def set_existing_family_heads(apps, schema_editor):
    Person = apps.get_model("person", "Person")

    seen_family_ids = set()
    queryset = (
        Person.objects.filter(
            deleted__isnull=True,
            genre="M",
            pere__isnull=True,
            mere__isnull=True,
            pere_nom_libre="",
            mere_nom_libre="",
        )
        .order_by("famille_id", "date_naissance", "date_creation", "id")
    )

    for person in queryset.iterator():
        if person.famille_id in seen_family_ids:
            continue
        Person.objects.filter(pk=person.pk).update(est_chef_famille=True)
        seen_family_ids.add(person.famille_id)


class Migration(migrations.Migration):

    dependencies = [
        ("person", "0004_historicalperson_pere_nom_libre_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalperson",
            name="est_chef_famille",
            field=models.BooleanField(default=False, verbose_name="Chef de famille"),
        ),
        migrations.AddField(
            model_name="person",
            name="est_chef_famille",
            field=models.BooleanField(default=False, verbose_name="Chef de famille"),
        ),
        migrations.RunPython(
            set_existing_family_heads,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="person",
            constraint=models.UniqueConstraint(
                condition=Q(
                    deleted__isnull=True,
                    est_chef_famille=True,
                ),
                fields=("famille",),
                name="uq_person_chef_famille_actif",
            ),
        ),
    ]
