# familles/dtos/family_dto.py
# ============================================================
#  DTOs — Data Transfer Objects
#  Objets Python purs — aucune dépendance Django
#  Le dashboard ne reçoit QUE ces objets
# ============================================================

from dataclasses import dataclass, field
from typing      import Optional, List
from datetime    import datetime, date


# ══════════════════════════════════════════════════════════════
# DTOs PERSON
# ══════════════════════════════════════════════════════════════

@dataclass
class PersonLightDTO:
    """Version légère de Person — pour les listes et l'autocomplétion."""
    id:             str
    code:           Optional[str]
    nom:            str
    prenom:         str
    nom_complet:    str
    genre:          str
    genre_label:    str
    age:            Optional[int]
    village:        str
    famille_id:     str
    famille_nom:    str
    est_vivant:     bool
    photo:          Optional[str]


@dataclass
class PersonDTO:
    """Version complète de Person — pour la fiche détail."""
    id:                     str
    code:                   Optional[str]
    nom:                    str
    prenom:                 str
    surnom:                 str
    nom_complet:            str
    genre:                  str
    genre_label:            str
    date_naissance:         Optional[date]
    lieu_naissance:         str
    nationalite:            str
    numero_cni:             str
    profession:             str
    photo:                  Optional[str]
    situation_matrimoniale: str
    situation_label:        str
    est_vivant:             bool
    date_deces:             Optional[date]
    telephone:              str
    email:                  str
    type_residence:         str
    residence_label:        str
    lieu_residence:         str
    famille_id:             str
    famille_nom:            str
    village_id:             str
    village_nom:            str
    est_chef_famille:       bool
    pere_id:                Optional[str]
    pere_nom:               Optional[str]
    pere_nom_libre:         str
    mere_id:                Optional[str]
    mere_nom:               Optional[str]
    mere_nom_libre:         str
    conjoint_id:            Optional[str]
    conjoint_nom:           Optional[str]
    conjoint_nom_libre:     str
    age:                    Optional[int]
    notes:                  str
    date_creation:          datetime
    date_maj:               datetime

    # Relations calculées (chargées séparément)
    enfants:        List['PersonLightDTO'] = field(default_factory=list)
    freres_soeurs:  List['PersonLightDTO'] = field(default_factory=list)

    # Profil diaspora si existant
    has_diaspora:   bool = False


@dataclass
class CreatePersonDTO:
    """Données entrantes pour créer une personne."""
    nom:                    str
    prenom:                 str
    genre:                  str
    famille_id:             str
    surnom:                 str            = ''
    date_naissance:         Optional[date] = None
    lieu_naissance:         str            = ''
    nationalite:            str            = 'Ivoirienne'
    numero_cni:             str            = ''
    profession:             str            = ''
    situation_matrimoniale: str            = 'celibataire'
    est_vivant:             bool           = True
    date_deces:             Optional[date] = None
    telephone:              str            = ''
    email:                  str            = ''
    type_residence:         str            = 'village'
    lieu_residence:         str            = ''
    pere_id:                Optional[str]  = None
    pere_nom_libre:         str            = ''
    mere_id:                Optional[str]  = None
    mere_nom_libre:         str            = ''
    conjoint_id:            Optional[str]  = None
    conjoint_nom_libre:     str            = ''
    notes:                  str            = ''
    photo:                  object         = None   # InMemoryUploadedFile
    est_chef_famille:       bool           = False
    created_by_id:          Optional[str]  = None


@dataclass
class UpdatePersonDTO(CreatePersonDTO):
    """Données entrantes pour modifier une personne."""
    id: str = ''


# ══════════════════════════════════════════════════════════════
# DTO RECHERCHE AUTOCOMPLÉTION
# ══════════════════════════════════════════════════════════════

@dataclass
class PersonSearchResultDTO:
    """Résultat d'autocomplétion pour les champs père/mère."""
    id:         str
    code:       Optional[str]
    nom_complet: str
    village:    str
    age:        Optional[int]
    genre:      str
    photo:      Optional[str]

# ══════════════════════════════════════════════════════════════
# DTO ARBRE GÉNÉALOGIQUE
# ══════════════════════════════════════════════════════════════

@dataclass
class TreeNodeDTO:
    """Nœud de l'arbre généalogique — structure récursive."""
    id:         str
    nom_complet: str
    prenom:     str
    nom:        str
    genre:      str
    age:        Optional[int]
    est_vivant: bool
    photo:      Optional[str]
    conjoint:   Optional[str]
    generation: int
    date_naissance: Optional[date] = None
    date_deces:     Optional[date] = None
    residence_label: str = ''
    lieu_residence: str = ''
    enfants:    List['TreeNodeDTO'] = field(default_factory=list)
