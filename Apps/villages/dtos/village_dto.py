# villages/dtos/village_dto.py
# DTO = Data Transfer Object
# Objet simple Python — aucune dépendance Django
# C'est ce que le dashboard reçoit et affiche

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class InfrastructureDTO:
    id:                  str
    type_infrastructure: str
    type_label:          str
    nom:                 str
    etat:                str
    etat_label:          str
    capacite:            Optional[int]
    responsable:         str
    contact_responsable: str


@dataclass
class VillageDTO:
    id:                    str
    nom:                   str
    description:           str
    latitude:              Optional[float]
    longitude:             Optional[float]
    chef_village:          str
    date_creation:         datetime
    nombre_familles:       int       = 0
    nombre_habitants:      int       = 0
    nombre_infrastructures: int      = 0
    infrastructures:       List[InfrastructureDTO] = field(default_factory=list)


@dataclass
class VillageListDTO:
    """Résultat paginé pour la liste des villages"""
    villages:       List[VillageDTO]
    total:          int
    page:           int
    par_page:       int
    nb_pages:       int
    q:              str = ''


@dataclass
class CreateVillageDTO:
    """Données entrantes pour créer un village"""
    nom:                str
    description:        str  = ''
    latitude:           Optional[float] = None
    longitude:          Optional[float] = None
    chef_village:       str  = ''
    infrastructure_types: List[str] = field(default_factory=list)
    created_by_id:      Optional[str] = None


@dataclass
class UpdateVillageDTO:
    """Données entrantes pour modifier un village"""
    id:                 str
    nom:                str
    description:        str  = ''
    latitude:           Optional[float] = None
    longitude:          Optional[float] = None
    chef_village:       str  = ''
    infrastructure_types: List[str] = field(default_factory=list)
