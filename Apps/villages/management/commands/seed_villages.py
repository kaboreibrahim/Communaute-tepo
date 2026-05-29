# villages/management/commands/seed_villages.py
# ============================================================
#  PLATEFORME OLODIO — Seed des 26 villages + infrastructures
#  Utilisation :
#      python manage.py seed_villages
#      python manage.py seed_villages --reset   (repart de zéro)
# ============================================================

from django.core.management.base import BaseCommand
from django.utils                 import timezone
import random

# ── Import des modèles ───────────────────────────────────────
from ...models import Village, Infrastructure


# ============================================================
# DONNÉES : 26 villages d'Olodio avec coords GPS approximatives
# ============================================================

VILLAGES_DATA = [
    {
        "nom": "Olodio",
        "chef_village": "Koné Mamadou",
        "population_estimee": 1200,
        "description": "Chef-lieu de la sous-préfecture d'Olodio",
        "latitude":  4.8521,
        "longitude": -7.3842,
    },
    {
        "nom": "Kpéhiri",
        "chef_village": "Bamba Seydou",
        "population_estimee": 650,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8734,
        "longitude": -7.4012,
    },
    {
        "nom": "Zégban",
        "chef_village": "Coulibaly Bakary",
        "population_estimee": 480,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8612,
        "longitude": -7.3654,
    },
    {
        "nom": "Gbalébré",
        "chef_village": "Diallo Moussa",
        "population_estimee": 390,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8445,
        "longitude": -7.3901,
    },
    {
        "nom": "Dakpadou",
        "chef_village": "Traoré Souleymane",
        "population_estimee": 520,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8289,
        "longitude": -7.4123,
    },
    {
        "nom": "Niéproyo",
        "chef_village": "Ouattara Drissa",
        "population_estimee": 310,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8901,
        "longitude": -7.3567,
    },
    {
        "nom": "Kpata",
        "chef_village": "Konaté Adama",
        "population_estimee": 420,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8156,
        "longitude": -7.4234,
    },
    {
        "nom": "Kpéhiri 2",
        "chef_village": "Camara Lamine",
        "population_estimee": 280,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8801,
        "longitude": -7.4067,
    },
    {
        "nom": "Kpanda",
        "chef_village": "Sanogo Issouf",
        "population_estimee": 360,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8034,
        "longitude": -7.3789,
    },
    {
        "nom": "Grihiri",
        "chef_village": "Fofana Abdoulaye",
        "population_estimee": 440,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8678,
        "longitude": -7.3456,
    },
    {
        "nom": "Bobouo",
        "chef_village": "Diabaté Mamadou",
        "population_estimee": 510,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8345,
        "longitude": -7.4345,
    },
    {
        "nom": "Niangoussou",
        "chef_village": "Dosso Yacouba",
        "population_estimee": 290,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8923,
        "longitude": -7.3678,
    },
    {
        "nom": "Kpoussoussou",
        "chef_village": "Silué Navigué",
        "population_estimee": 380,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8112,
        "longitude": -7.4456,
    },
    {
        "nom": "Zakoua",
        "chef_village": "Coulibaly Soungalo",
        "population_estimee": 460,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8567,
        "longitude": -7.3234,
    },
    {
        "nom": "Gnalégribouo",
        "chef_village": "Koné Drissa",
        "population_estimee": 320,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8789,
        "longitude": -7.4189,
    },
    {
        "nom": "Doussou",
        "chef_village": "Bamba Lacina",
        "population_estimee": 270,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8234,
        "longitude": -7.3567,
    },
    {
        "nom": "Gbaléguhé",
        "chef_village": "Konaté Seydou",
        "population_estimee": 490,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8456,
        "longitude": -7.4567,
    },
    {
        "nom": "Kpéhiri 3",
        "chef_village": "Diallo Ibrahim",
        "population_estimee": 240,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8845,
        "longitude": -7.4089,
    },
    {
        "nom": "N'goussouyo",
        "chef_village": "Traoré Moussa",
        "population_estimee": 330,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8067,
        "longitude": -7.3901,
    },
    {
        "nom": "Blibouo",
        "chef_village": "Ouattara Lassina",
        "population_estimee": 410,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8912,
        "longitude": -7.3345,
    },
    {
        "nom": "Kpado",
        "chef_village": "Koné Siaka",
        "population_estimee": 350,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8178,
        "longitude": -7.4678,
    },
    {
        "nom": "Zébréguhé",
        "chef_village": "Fofana Sekou",
        "population_estimee": 280,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8634,
        "longitude": -7.3123,
    },
    {
        "nom": "Kpoussouya",
        "chef_village": "Diabaté Souleymane",
        "population_estimee": 390,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8023,
        "longitude": -7.4012,
    },
    {
        "nom": "Gbalouyo",
        "chef_village": "Silué Dramane",
        "population_estimee": 450,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8756,
        "longitude": -7.3789,
    },
    {
        "nom": "Niézéko",
        "chef_village": "Coulibaly Adama",
        "population_estimee": 300,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8389,
        "longitude": -7.4234,
    },
    {
        "nom": "Kpéhiri 4",
        "chef_village": "Bamba Noufou",
        "population_estimee": 260,
        "description": "Village de la sous-préfecture d'Olodio",
        "latitude":  4.8867,
        "longitude": -7.4134,
    },
]


# ============================================================
# TEMPLATES D'INFRASTRUCTURES PAR TAILLE DE VILLAGE
# ============================================================

# Infrastructures de base (tous les villages)
INFRAS_BASE = [
    {
        "type_infrastructure": "ecole",
        "nom_template":        "École primaire de {village}",
        "capacite_range":      (80, 250),
        "etat_choices":        ["bon", "bon", "moyen"],
    },
    {
        "type_infrastructure": "puit",
        "nom_template":        "Puits central de {village}",
        "capacite_range":      (None, None),
        "etat_choices":        ["bon", "bon", "moyen", "mauvais"],
    },
]

# Infrastructures villages moyens (pop > 300)
INFRAS_MOYENS = [
    {
        "type_infrastructure": "dispensaire",
        "nom_template":        "Dispensaire de {village}",
        "capacite_range":      (20, 60),
        "etat_choices":        ["bon", "moyen", "moyen"],
    },
    {
        "type_infrastructure": "marche",
        "nom_template":        "Marché hebdomadaire de {village}",
        "capacite_range":      (50, 200),
        "etat_choices":        ["bon", "moyen"],
    },
    {
        "type_infrastructure": "forage",
        "nom_template":        "Forage communautaire de {village}",
        "capacite_range":      (None, None),
        "etat_choices":        ["bon", "bon", "moyen"],
    },
]

# Infrastructures grands villages (pop > 500)
INFRAS_GRANDS = [
    {
        "type_infrastructure": "centre_sante",
        "nom_template":        "Centre de santé de {village}",
        "capacite_range":      (30, 80),
        "etat_choices":        ["bon", "bon", "moyen"],
    },
    {
        "type_infrastructure": "lycee",
        "nom_template":        "Lycée moderne de {village}",
        "capacite_range":      (200, 600),
        "etat_choices":        ["bon", "en_construction", "moyen"],
    },
    {
        "type_infrastructure": "mairie",
        "nom_template":        "Mairie de {village}",
        "capacite_range":      (None, None),
        "etat_choices":        ["bon", "moyen"],
    },
    {
        "type_infrastructure": "electricite",
        "nom_template":        "Réseau électrique de {village}",
        "capacite_range":      (None, None),
        "etat_choices":        ["bon", "moyen", "mauvais"],
    },
]

# Infrastructures aléatoires bonus
INFRAS_BONUS = [
    {
        "type_infrastructure": "ecole_maternelle",
        "nom_template":        "École maternelle de {village}",
        "capacite_range":      (30, 80),
        "etat_choices":        ["bon", "moyen"],
    },
    {
        "type_infrastructure": "place_publique",
        "nom_template":        "Place publique de {village}",
        "capacite_range":      (100, 500),
        "etat_choices":        ["bon", "bon"],
    },
    {
        "type_infrastructure": "centre_communautaire",
        "nom_template":        "Centre communautaire de {village}",
        "capacite_range":      (50, 150),
        "etat_choices":        ["bon", "moyen", "en_construction"],
    },
    {
        "type_infrastructure": "telephone",
        "nom_template":        "Antenne téléphonique de {village}",
        "capacite_range":      (None, None),
        "etat_choices":        ["bon", "moyen"],
    },
    {
        "type_infrastructure": "internet",
        "nom_template":        "Point internet de {village}",
        "capacite_range":      (None, None),
        "etat_choices":        ["bon", "moyen", "mauvais"],
    },
    {
        "type_infrastructure": "poste_police",
        "nom_template":        "Poste de sécurité de {village}",
        "capacite_range":      (None, None),
        "etat_choices":        ["bon", "moyen"],
    },
]

# Responsables fictifs pour les infrastructures
RESPONSABLES = [
    ("Koné Fatou",       "0701020304"),
    ("Bamba Aminata",    "0702030405"),
    ("Coulibaly Marie",  "0703040506"),
    ("Diallo Aïssatou",  "0704050607"),
    ("Traoré Mariam",    "0705060708"),
    ("Ouattara Kadiatou","0706070809"),
    ("Konaté Fatoumata", "0707080910"),
    ("Camara Rokia",     "0708091011"),
    ("Sanogo Hawa",      "0709101112"),
    ("Fofana Nafissatou","0710111213"),
    ("Diabaté Kadja",    "0711121314"),
    ("Silué Masséré",    "0712131415"),
]


# ============================================================
# COMMANDE DJANGO
# ============================================================

class Command(BaseCommand):

    help = "Seed les 26 villages d'Olodio avec leurs infrastructures"

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Supprime tous les villages existants avant de recréer',
        )
        parser.add_argument(
            '--villages-only',
            action='store_true',
            help='Crée uniquement les villages, sans infrastructures',
        )

    def handle(self, *args, **options):

        reset         = options.get('reset', False)
        villages_only = options.get('villages_only', False)

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n🌍 SEED — Sous-préfecture d'Olodio\n"
        ))

        # ── Reset optionnel ──────────────────────────────────
        if reset:
            self.stdout.write("  ⚠️  Suppression des données existantes...")
            Infrastructure.objects.all().delete()
            Village.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Données supprimées.\n"))

        # ── Création des villages ────────────────────────────
        self.stdout.write("  📍 Création des villages...")
        villages_crees   = 0
        villages_existants = 0
        villages_objets  = []

        for data in VILLAGES_DATA:
            village, created = Village.objects.get_or_create(
                nom=data["nom"],
                defaults={
                    "description":        data["description"],
                    "chef_village":       data["chef_village"],
                    "population_estimee": data["population_estimee"],
                    "latitude":           data["latitude"],
                    "longitude":          data["longitude"],
                }
            )
            villages_objets.append(village)

            if created:
                villages_crees += 1
                self.stdout.write(
                    f"    ✅ {village.nom} "
                    f"(pop. {village.population_estimee})"
                )
            else:
                villages_existants += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"    ⏭️  {village.nom} — déjà existant, ignoré"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n  Villages créés    : {villages_crees}"
                f"\n  Villages ignorés  : {villages_existants}\n"
            )
        )

        if villages_only:
            self.stdout.write(self.style.SUCCESS(
                "✅ Terminé (villages uniquement).\n"
            ))
            return

        # ── Création des infrastructures ─────────────────────
        self.stdout.write("  🏗️  Ajout des infrastructures...")
        total_infras = 0

        for village in villages_objets:
            pop  = village.population_estimee
            infras_ajoutees = self._creer_infrastructures(village, pop)
            total_infras   += infras_ajoutees
            self.stdout.write(
                f"    🏘️  {village.nom} → {infras_ajoutees} infrastructure(s)"
            )

        # ── Résumé final ─────────────────────────────────────
        self.stdout.write("\n" + "─" * 50)
        self.stdout.write(self.style.SUCCESS(
            f"  ✅ TERMINÉ !\n"
            f"  Villages        : {Village.objects.count()}\n"
            f"  Infrastructures : {Infrastructure.objects.count()}\n"
        ))
        self._afficher_stats()

    # ── Méthodes privées ─────────────────────────────────────

    def _creer_infrastructures(
        self, village: "Village", population: int
    ) -> int:
        """
        Crée les infrastructures adaptées à la taille du village.
        Retourne le nombre d'infrastructures créées.
        """
        compte = 0
        templates_a_creer = []

        # Tous les villages ont les infras de base
        templates_a_creer.extend(INFRAS_BASE)

        # Villages moyens (pop > 300)
        if population > 300:
            templates_a_creer.extend(INFRAS_MOYENS)

        # Grands villages (pop > 500)
        if population > 500:
            templates_a_creer.extend(INFRAS_GRANDS)

        # 2 à 4 infrastructures bonus aléatoires
        nb_bonus = random.randint(2, 4)
        bonus    = random.sample(INFRAS_BONUS, min(nb_bonus, len(INFRAS_BONUS)))
        templates_a_creer.extend(bonus)

        # Créer chaque infrastructure
        for tpl in templates_a_creer:
            # Vérifier si elle n'existe pas déjà
            nom = tpl["nom_template"].format(village=village.nom)
            if Infrastructure.objects.filter(
                village=village,
                type_infrastructure=tpl["type_infrastructure"]
            ).exists():
                continue

            # Capacité aléatoire dans la fourchette
            cap_min, cap_max = tpl["capacite_range"]
            capacite = (
                random.randint(cap_min, cap_max)
                if cap_min and cap_max
                else None
            )

            # État aléatoire selon les poids définis
            etat = random.choice(tpl["etat_choices"])

            # Responsable aléatoire
            responsable, contact = random.choice(RESPONSABLES)

            # Date de construction aléatoire (entre 1980 et 2022)
            annee = random.randint(1980, 2022)
            mois  = random.randint(1, 12)
            jour  = random.randint(1, 28)
            from datetime import date
            date_construction = date(annee, mois, jour)

            Infrastructure.objects.create(
                village              = village,
                type_infrastructure  = tpl["type_infrastructure"],
                nom                  = nom,
                description          = (
                    f"Infrastructure de type "
                    f"{tpl['type_infrastructure']} "
                    f"dans le village de {village.nom}"
                ),
                capacite             = capacite,
                etat                 = etat,
                responsable          = responsable,
                contact_responsable  = contact,
                date_construction    = date_construction,
            )
            compte += 1

        return compte

    def _afficher_stats(self):
        """Affiche un résumé des infrastructures par type."""
        self.stdout.write("\n  📊 Répartition des infrastructures :\n")
        types_counts = {}
        for infra in Infrastructure.objects.all():
            label = infra.get_type_infrastructure_display()
            types_counts[label] = types_counts.get(label, 0) + 1

        for label, count in sorted(
            types_counts.items(), key=lambda x: -x[1]
        ):
            barre = "█" * min(count, 30)
            self.stdout.write(f"    {label:<25} {barre} {count}")
        self.stdout.write("")
