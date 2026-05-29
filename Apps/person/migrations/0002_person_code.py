from django.db import migrations, models
from django.utils.text import slugify


def _build_prefix(nom_famille):
    prefix = slugify(nom_famille or "").replace("-", "").upper()[:8]
    return prefix or "PERS"


def populate_person_codes(apps, schema_editor):
    Person = apps.get_model("person", "Person")
    db_alias = schema_editor.connection.alias
    manager = Person._base_manager.using(db_alias)

    existing_codes = set(
        manager.exclude(code__isnull=True)
        .exclude(code="")
        .values_list("code", flat=True)
    )

    for person in manager.select_related("famille").order_by("date_creation", "id"):
        if person.code:
            continue

        prefix = _build_prefix(
            person.famille.nom_famille if person.famille_id else ""
        )
        compteur = 1
        candidate = f"{prefix}-{compteur:04d}"
        while candidate in existing_codes:
            compteur += 1
            candidate = f"{prefix}-{compteur:04d}"

        person.code = candidate
        person.save(update_fields=["code"])
        existing_codes.add(candidate)


class Migration(migrations.Migration):

    dependencies = [
        ("person", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="code",
            field=models.CharField(
                blank=True,
                editable=False,
                max_length=32,
                null=True,
                unique=True,
                verbose_name="Code",
            ),
        ),
        migrations.AddField(
            model_name="historicalperson",
            name="code",
            field=models.CharField(
                blank=True,
                db_index=True,
                editable=False,
                max_length=32,
                null=True,
                verbose_name="Code",
            ),
        ),
        migrations.RunPython(
            populate_person_codes,
            migrations.RunPython.noop,
        ),
    ]
