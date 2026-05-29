from dataclasses import dataclass, field
from typing      import Optional, List
from datetime    import datetime, date
from Apps.person.dtos.person_dto import PersonLightDTO
# ══════════════════════════════════════════════════════════════
# DTOs FAMILY
# ══════════════════════════════════════════════════════════════

@dataclass
class FamilyDTO:
    """Version complète d'une famille."""
    id:             str
    nom_famille:    str
    village_id:     str
    village_nom:    str
    description:    str
    date_creation:  datetime
    date_maj:       datetime
    nombre_membres: int
    chef_nom:       Optional[str]
    chef_id:        Optional[str]
    membres:        List[PersonLightDTO] = field(default_factory=list)


@dataclass
class FamilyLightDTO:
    """Version légère — pour les listes et l'autocomplétion."""
    id:             str
    nom_famille:    str
    village_nom:    str
    nombre_membres: int
    chef_nom:       Optional[str]
    date_creation:  datetime


@dataclass
class FamilyListDTO:
    """Résultat paginé pour la liste des familles."""
    familles:   List[FamilyLightDTO]
    total:      int
    page:       int
    par_page:   int
    nb_pages:   int
    q:          str = ''


@dataclass
class CreateFamilyDTO:
    """Données entrantes pour créer une famille."""
    nom_famille:    str
    village_id:     str
    description:    str = ''
    created_by_id:  Optional[str] = None


@dataclass
class UpdateFamilyDTO:
    """Données entrantes pour modifier une famille."""
    id:             str
    nom_famille:    str
    village_id:     str
    description:    str = ''



