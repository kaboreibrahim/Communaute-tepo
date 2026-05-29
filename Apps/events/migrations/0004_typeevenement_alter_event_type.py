import django.db.models.deletion
from django.db import migrations, models


TYPES_DEFAUT = [
    ("naissance",  "Naissance",           "child_care",   "#E1F5EE", "#0F6E56", False, 1),
    ("deces",      "Deces",               "mood_bad",     "#F1EFE8", "#444441", False, 2),
    ("mariage",    "Mariage",             "favorite",     "#FAECE7", "#712B13", False, 3),
    ("bapteme",    "Bapteme / Ceremonie", "auto_awesome", "#FAEEDA", "#633806", False, 4),
    ("diplome",    "Diplome / Reussite",  "school",       "#E6F1FB", "#0C447C", False, 5),
    ("deuil",      "Deuil",               "candle",       "#1F2937", "#FFFFFF", False, 6),
    ("fete",       "Fete",                "celebration",  "#FFF1E7", "#9A3412", True,  7),
    ("communaute", "Communaute",          "groups",       "#EEEDFE", "#26215C", True,  8),
    ("autre",      "Autre",               "event_note",   "#F8FAFC", "#334155", False, 9),
]


def populate_types(apps, schema_editor):
    TypeEvenement = apps.get_model("events", "TypeEvenement")
    for slug, nom, icone, fond, texte, communautaire, ordre in TYPES_DEFAUT:
        TypeEvenement.objects.get_or_create(
            slug=slug,
            defaults=dict(
                nom=nom,
                icone=icone,
                couleur_fond=fond,
                couleur_texte=texte,
                est_communautaire=communautaire,
                ordre=ordre,
            ),
        )


def migrate_type_values(apps, schema_editor):
    db = schema_editor.connection
    with db.cursor() as cursor:
        cursor.execute("SELECT slug, id FROM events_typeevenement")
        type_map = {row[0]: row[1] for row in cursor.fetchall()}
        for slug, type_id in type_map.items():
            cursor.execute(
                "UPDATE events_event SET type_id = %s WHERE type_old = %s",
                [type_id, slug],
            )


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0003_event_email_contact_event_nom_contact_and_more'),
    ]

    operations = [
        # 1. Creer la table TypeEvenement
        migrations.CreateModel(
            name='TypeEvenement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField(help_text='Identifiant unique (ex: naissance, deces, mariage…)', max_length=30, unique=True)),
                ('nom', models.CharField(max_length=100)),
                ('icone', models.CharField(default='event_note', help_text="Nom de l'icone Material Icons", max_length=60)),
                ('couleur_fond', models.CharField(default='#F8FAFC', help_text='Couleur de fond du badge (hex)', max_length=10)),
                ('couleur_texte', models.CharField(default='#334155', help_text='Couleur du texte du badge (hex)', max_length=10)),
                ('est_communautaire', models.BooleanField(default=False, help_text='Cocher si ce type concerne la communaute (fete, reunion…)')),
                ('ordre', models.PositiveSmallIntegerField(default=0, help_text="Ordre d'affichage dans les listes et formulaires")),
            ],
            options={
                'verbose_name': "Type d'evenement",
                'verbose_name_plural': "Types d'evenement",
                'ordering': ['ordre', 'nom'],
            },
        ),
        # 2. Inserer les 9 types par defaut
        migrations.RunPython(populate_types, migrations.RunPython.noop),
        # 3. Renommer l'ancienne colonne varchar pour liberer le nom 'type'
        migrations.RenameField(
            model_name='event',
            old_name='type',
            new_name='type_old',
        ),
        # 4. Ajouter la nouvelle colonne FK (nullable)
        migrations.AddField(
            model_name='event',
            name='type',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='evenements',
                to='events.typeevenement',
                verbose_name="Type d'evenement",
            ),
        ),
        # 5. Remplir type_id a partir des anciennes valeurs varchar
        migrations.RunPython(migrate_type_values, migrations.RunPython.noop),
        # 6. Supprimer l'ancienne colonne varchar
        migrations.RemoveField(
            model_name='event',
            name='type_old',
        ),
    ]
