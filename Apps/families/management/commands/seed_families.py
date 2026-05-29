import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from safedelete import HARD_DELETE

from Apps.families.models import Family
from Apps.villages.models import Village


FAMILY_NAMES = [
    "Kone",
    "Bamba",
    "Coulibaly",
    "Diallo",
    "Traore",
    "Ouattara",
    "Konate",
    "Camara",
    "Sanogo",
    "Fofana",
    "Diabate",
    "Silue",
    "Soro",
    "Dosso",
    "Toure",
    "Cisse",
    "Kouyate",
    "Bakayoko",
    "Yeo",
    "Tuo",
    "Sangare",
    "Sidibe",
    "Keita",
    "Diarra",
]

ACTIVITIES = [
    "agriculture",
    "cacao",
    "riziculture",
    "commerce local",
    "elevage",
    "artisanat",
    "transport",
    "maraichage",
]

DESCRIPTION_TEMPLATES = [
    "Famille {nom_famille} installee a {village}, active dans {activite}.",
    "Menage de reference du village de {village}, la famille {nom_famille} vit principalement de {activite}.",
    "Famille {nom_famille} recensee a {village} pour les besoins de demonstration de la plateforme.",
    "Famille fictive rattachee a {village}, avec une activite dominante en {activite}.",
]


class Command(BaseCommand):
    help = "Cree des familles de demonstration rattachees aux villages existants"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les familles existantes avant regeneration",
        )
        parser.add_argument(
            "--min-per-village",
            type=int,
            default=4,
            help="Nombre minimum de familles a creer par village",
        )
        parser.add_argument(
            "--max-per-village",
            type=int,
            default=8,
            help="Nombre maximum de familles a creer par village",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Graine aleatoire pour obtenir des donnees reproductibles",
        )
        parser.add_argument(
            "--village",
            action="append",
            dest="villages",
            help="Nom d'un village cible. Option repetable.",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        min_per_village = options["min_per_village"]
        max_per_village = options["max_per_village"]
        villages_filter = options.get("villages") or []
        seed = options["seed"]

        if min_per_village <= 0 or max_per_village <= 0:
            raise CommandError("Les volumes par village doivent etre strictement positifs.")

        if min_per_village > max_per_village:
            raise CommandError("--min-per-village ne peut pas etre superieur a --max-per-village.")

        random.seed(seed)

        villages_qs = Village.objects.all().order_by("nom")
        if villages_filter:
            villages_qs = villages_qs.filter(nom__in=villages_filter)

        villages = list(villages_qs)
        if not villages:
            if villages_filter:
                raise CommandError("Aucun des villages demandes n'a ete trouve.")
            raise CommandError(
                "Aucun village disponible. Lancez d'abord `python manage.py seed_villages`."
            )

        self.stdout.write(
            self.style.MIGRATE_HEADING("\nSEED - Familles Olodio\n")
        )
        self.stdout.write(f"  Graine utilisee : {seed}")
        self.stdout.write(f"  Villages cibles : {len(villages)}")

        with transaction.atomic():
            if reset:
                families_qs = Family.all_objects.all()
                if villages_filter:
                    families_qs = families_qs.filter(village__nom__in=villages_filter)

                deleted_count, _ = families_qs.delete(force_policy=HARD_DELETE)
                self.stdout.write(
                    self.style.WARNING(
                        f"  Familles supprimees avant regeneration : {deleted_count}"
                    )
                )

            total_created = 0
            total_existing = 0

            for village in villages:
                target = random.randint(min_per_village, max_per_village)
                created, existing = self._seed_village(village, target)
                total_created += created
                total_existing += existing

                self.stdout.write(
                    f"  {village.nom:<20} -> {created} creee(s), {existing} existante(s)"
                )

        self.stdout.write("\n" + "-" * 48)
        self.stdout.write(
            self.style.SUCCESS(
                f"  Total familles actives : {Family.objects.count()}\n"
                f"  Nouvelles familles     : {total_created}\n"
                f"  Familles deja la       : {total_existing}\n"
            )
        )

    def _seed_village(self, village, target):
        used_names = set(
            Family.objects.filter(village=village).values_list("nom_famille", flat=True)
        )

        existing = len(used_names)
        created = 0

        while len(used_names) < target:
            nom_famille = self._generate_family_name(used_names)

            Family.objects.create(
                nom_famille=nom_famille,
                village=village,
                description=self._build_description(village.nom, nom_famille),
            )
            used_names.add(nom_famille)
            created += 1

        return created, existing

    def _generate_family_name(self, used_names):
        base_name = random.choice(FAMILY_NAMES)
        if base_name not in used_names:
            return base_name

        suffix = 2
        while f"{base_name} {suffix}" in used_names:
            suffix += 1
        return f"{base_name} {suffix}"

    def _build_description(self, village_name, family_name):
        template = random.choice(DESCRIPTION_TEMPLATES)
        activite = random.choice(ACTIVITIES)
        return template.format(
            nom_famille=family_name,
            village=village_name,
            activite=activite,
        )
