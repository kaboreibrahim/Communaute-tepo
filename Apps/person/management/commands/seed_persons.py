import random
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from safedelete import HARD_DELETE

from Apps.families.models import Family
from Apps.person.models import Person


MALE_FIRST_NAMES = [
    "Mamadou",
    "Bakary",
    "Seydou",
    "Souleymane",
    "Adama",
    "Ibrahim",
    "Lassina",
    "Drissa",
    "Yacouba",
    "Siaka",
    "Moussa",
    "Abdoulaye",
    "Issouf",
    "Lamine",
    "Sekou",
]

FEMALE_FIRST_NAMES = [
    "Aminata",
    "Aissatou",
    "Mariam",
    "Fatoumata",
    "Kadja",
    "Rokia",
    "Nafissatou",
    "Hawa",
    "Kadiatou",
    "Assetou",
    "Awa",
    "Masse",
    "Salimata",
    "Mariam",
    "Nene",
]

SURNOMS = [
    "Petit",
    "Vieux Pere",
    "Doyen",
    "Belle",
    "Champion",
    "Dada",
    "Courage",
    "Riche",
]

CI_LOCATIONS = [
    "Abidjan",
    "San Pedro",
    "Daloa",
    "Sassandra",
    "Soubre",
    "Yamoussoukro",
]

DIASPORA_LOCATIONS = [
    "Paris, France",
    "Lyon, France",
    "Bruxelles, Belgique",
    "Milan, Italie",
    "Montreal, Canada",
    "New York, USA",
]


class Command(BaseCommand):
    help = "Cree des personnes de demonstration rattachees aux familles existantes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime les personnes existantes dans les familles ciblees avant regeneration",
        )
        parser.add_argument(
            "--min-children",
            type=int,
            default=2,
            help="Nombre minimum d'enfants a creer par famille",
        )
        parser.add_argument(
            "--max-children",
            type=int,
            default=5,
            help="Nombre maximum d'enfants a creer par famille",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Graine aleatoire pour obtenir des donnees reproductibles",
        )
        parser.add_argument(
            "--family",
            action="append",
            dest="families",
            help="Nom d'une famille cible. Option repetable.",
        )
        parser.add_argument(
            "--village",
            action="append",
            dest="villages",
            help="Nom d'un village cible. Option repetable.",
        )

    def handle(self, *args, **options):
        reset = options["reset"]
        min_children = options["min_children"]
        max_children = options["max_children"]
        families_filter = options.get("families") or []
        villages_filter = options.get("villages") or []
        seed = options["seed"]

        if min_children < 0 or max_children < 0:
            raise CommandError("Les volumes d'enfants doivent etre positifs ou nuls.")

        if min_children > max_children:
            raise CommandError("--min-children ne peut pas etre superieur a --max-children.")

        random.seed(seed)

        families_qs = Family.objects.select_related("village").order_by(
            "village__nom", "nom_famille"
        )
        if villages_filter:
            families_qs = families_qs.filter(village__nom__in=villages_filter)
        if families_filter:
            families_qs = families_qs.filter(nom_famille__in=families_filter)

        families = list(families_qs)
        if not families:
            if villages_filter or families_filter:
                raise CommandError("Aucune famille ciblee n'a ete trouvee.")
            raise CommandError(
                "Aucune famille disponible. Lancez d'abord `python manage.py seed_families`."
            )

        self.stdout.write(self.style.MIGRATE_HEADING("\nSEED - Personnes Olodio\n"))
        self.stdout.write(f"  Graine utilisee : {seed}")
        self.stdout.write(f"  Familles ciblees: {len(families)}")

        with transaction.atomic():
            if reset:
                persons_qs = Person.all_objects.all()
                if villages_filter:
                    persons_qs = persons_qs.filter(famille__village__nom__in=villages_filter)
                if families_filter:
                    persons_qs = persons_qs.filter(famille__nom_famille__in=families_filter)

                deleted_count, _ = persons_qs.delete(force_policy=HARD_DELETE)
                self.stdout.write(
                    self.style.WARNING(
                        f"  Personnes supprimees avant regeneration : {deleted_count}"
                    )
                )

            total_created = 0
            total_skipped = 0

            for family in families:
                created, skipped = self._seed_family(
                    family=family,
                    min_children=min_children,
                    max_children=max_children,
                )
                total_created += created
                total_skipped += skipped
                self.stdout.write(
                    f"  {family.village.nom:<18} / {family.nom_famille:<15}"
                    f" -> {created} creee(s), {skipped} deja presente(s)"
                )

        self.stdout.write("\n" + "-" * 52)
        self.stdout.write(
            self.style.SUCCESS(
                f"  Total personnes actives : {Person.objects.count()}\n"
                f"  Nouvelles personnes    : {total_created}\n"
                f"  Personnes ignorees     : {total_skipped}\n"
            )
        )

    def _seed_family(self, family, min_children, max_children):
        existing_members = family.membres.filter(deleted__isnull=True).count()
        if existing_members:
            return 0, existing_members

        used_names = set()
        surname = family.nom_famille.strip() or "Famille"

        father_birth = self._random_date(1952, 1974)
        mother_birth = self._random_date(max(father_birth.year - 3, 1950), 1979)

        father_residence_type, father_residence = self._pick_residence(
            family=family,
            adult=True,
        )
        mother_residence_type, mother_residence = (
            (father_residence_type, father_residence)
            if random.random() < 0.7
            else self._pick_residence(family=family, adult=True)
        )

        father = Person.objects.create(
            nom=surname,
            prenom=self._pick_first_name(MALE_FIRST_NAMES, used_names),
            surnom=self._pick_surnom(),
            genre="M",
            date_naissance=father_birth,
            lieu_naissance=family.village.nom,
            nationalite="Ivoirienne",
            numero_cni=self._build_cni(),
            situation_matrimoniale="marie",
            est_vivant=True,
            telephone=self._build_phone(),
            email=self._build_email("chef", surname),
            type_residence=father_residence_type,
            lieu_residence=father_residence,
            famille=family,
            est_chef_famille=True,
            notes=self._build_note(family, "Chef de famille genere automatiquement."),
        )

        mother = Person.objects.create(
            nom=surname,
            prenom=self._pick_first_name(FEMALE_FIRST_NAMES, used_names),
            surnom=self._pick_surnom(),
            genre="F",
            date_naissance=mother_birth,
            lieu_naissance=family.village.nom,
            nationalite="Ivoirienne",
            numero_cni=self._build_cni(),
            situation_matrimoniale="marie",
            est_vivant=True,
            telephone=self._build_phone(),
            email=self._build_email("conjoint", surname),
            type_residence=mother_residence_type,
            lieu_residence=mother_residence,
            famille=family,
            notes=self._build_note(family, "Conjointe generee automatiquement."),
        )

        father.conjoint = mother
        father.save(update_fields=["conjoint"])
        mother.conjoint = father
        mother.save(update_fields=["conjoint"])

        children_count = random.randint(min_children, max_children)
        current_year = date.today().year
        first_child_year = min(
            current_year - 1,
            max(father_birth.year, mother_birth.year) + random.randint(18, 26),
        )
        child_year = first_child_year

        created = 2
        for index in range(children_count):
            if index > 0:
                child_year = min(current_year - 1, child_year + random.randint(1, 4))

            child_birth = self._random_date(child_year, child_year)
            age = self._age(child_birth)
            child_genre = random.choice(["M", "F"])
            residence_type, residence = self._pick_residence(
                family=family,
                adult=age >= 18,
                force_village=age < 12,
            )

            Person.objects.create(
                nom=surname,
                prenom=self._pick_first_name(
                    MALE_FIRST_NAMES if child_genre == "M" else FEMALE_FIRST_NAMES,
                    used_names,
                ),
                surnom=self._pick_surnom(child=True),
                genre=child_genre,
                date_naissance=child_birth,
                lieu_naissance=family.village.nom,
                nationalite="Ivoirienne",
                numero_cni=self._build_cni() if age >= 18 else "",
                situation_matrimoniale="celibataire",
                est_vivant=True,
                telephone=self._build_phone() if age >= 18 else "",
                email=self._build_email(f"enfant{index + 1}", surname) if age >= 18 else "",
                type_residence=residence_type,
                lieu_residence=residence,
                famille=family,
                pere=father,
                mere=mother,
                notes=self._build_note(
                    family,
                    f"Enfant {index + 1} genere automatiquement.",
                ),
            )
            created += 1

        return created, 0

    def _pick_first_name(self, pool, used_names):
        available = [name for name in pool if name not in used_names]
        if not available:
            available = pool
        choice = random.choice(available)
        used_names.add(choice)
        return choice

    def _pick_surnom(self, child=False):
        chance = 0.12 if child else 0.25
        return random.choice(SURNOMS) if random.random() < chance else ""

    def _pick_residence(self, family, adult=False, force_village=False):
        if force_village:
            return "village", family.village.nom

        if adult:
            residence_type = random.choices(
                population=["village", "ci", "diaspora"],
                weights=[60, 25, 15],
                k=1,
            )[0]
        else:
            residence_type = random.choices(
                population=["village", "ci", "diaspora"],
                weights=[78, 18, 4],
                k=1,
            )[0]

        if residence_type == "village":
            return residence_type, family.village.nom
        if residence_type == "ci":
            return residence_type, random.choice(CI_LOCATIONS)
        return residence_type, random.choice(DIASPORA_LOCATIONS)

    def _random_date(self, year_min, year_max):
        if year_min > year_max:
            year_min, year_max = year_max, year_min
        year = random.randint(year_min, year_max)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return date(year, month, day)

    def _build_phone(self):
        return f"07{random.randint(10, 99)}{random.randint(10, 99)}{random.randint(10, 99)}{random.randint(10, 99)}"

    def _build_cni(self):
        return f"CNI{random.randint(10000000, 99999999)}"

    def _build_email(self, prefix, surname):
        suffix = random.randint(10, 999)
        local_part = f"{prefix}.{surname}".lower().replace(" ", "").replace("'", "")
        return f"{local_part}{suffix}@olodio.test"

    def _build_note(self, family, message):
        return (
            "[seed_persons] "
            f"{message} Famille {family.nom_famille}, village {family.village.nom}."
        )

    def _age(self, birth_date):
        today = date.today()
        return today.year - birth_date.year - (
            (today.month, today.day) < (birth_date.month, birth_date.day)
        )
