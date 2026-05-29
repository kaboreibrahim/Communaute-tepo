from abc     import ABC, abstractmethod
from typing  import Optional, List, Tuple
from Apps.families.dtos.family_dto import (
    FamilyDTO, FamilyLightDTO, CreateFamilyDTO, UpdateFamilyDTO,
     PersonLightDTO, 
)

from Apps.person.dtos.person_dto import (
    PersonDTO,
    PersonSearchResultDTO,
    CreatePersonDTO, UpdatePersonDTO,
    TreeNodeDTO,
)
from Apps.person.models import Person

class PersonRepositoryInterface(ABC):

    @abstractmethod
    def get_all(
        self, q: str = '', famille_id: str = '',
        genre: str = '', village_id: str = '',
        created_by_id: str = '',
        page: int = 1, par_page: int = 20
    ) -> Tuple[List[PersonLightDTO], int]: ...

    @abstractmethod
    def get_by_id(
        self, person_id: str, created_by_id: str = ''
    ) -> Optional[PersonDTO]: ...

    @abstractmethod
    def create(self, data: CreatePersonDTO) -> PersonDTO: ...

    @abstractmethod
    def update(self, data: UpdatePersonDTO) -> PersonDTO: ...

    @abstractmethod
    def delete(self, person_id: str) -> bool: ...

    @abstractmethod
    def search_autocomplete(
        self, q: str, genre: str = '', village_id: str = '',
        created_by_id: str = '', limit: int = 15
    ) -> List[PersonSearchResultDTO]: ...

    @abstractmethod
    def build_tree(
        self, person_id: str, profondeur_max: int = 6
    ) -> Optional[TreeNodeDTO]: ...

# ============================================================
# familles/repositories/django_family_repo.py
# ============================================================

from math                        import ceil
from django.core.paginator       import Paginator
from django.db.models            import Q


def _person_to_light(p) -> 'PersonLightDTO':

    return PersonLightDTO(
        id=str(p.id),
        code=p.code,
        nom=p.nom,
        prenom=p.prenom,
        nom_complet=p.nom_complet,
        genre=p.genre,
        genre_label=p.get_genre_display(),
        age=p.age,
        village=p.famille.village.nom if p.famille_id else '',
        famille_id=str(p.famille_id) if p.famille_id else '',
        famille_nom=p.famille.nom_famille if p.famille_id else '',
        est_vivant=p.est_vivant,
        photo=p.photo.url if p.photo else None,
    )



def _person_to_dto(p) -> 'PersonDTO':

    return PersonDTO(
        id=str(p.id),
        code=p.code,
        nom=p.nom,
        prenom=p.prenom,
        surnom=p.surnom or '',
        nom_complet=p.nom_complet,
        genre=p.genre,
        genre_label=p.get_genre_display(),
        date_naissance=p.date_naissance,
        lieu_naissance=p.lieu_naissance or '',
        nationalite=p.nationalite or 'Ivoirienne',
        numero_cni=p.numero_cni or '',
        profession=p.profession or '',
        photo=p.photo.url if p.photo else None,
        situation_matrimoniale=p.situation_matrimoniale,
        situation_label=p.get_situation_matrimoniale_display(),
        est_vivant=p.est_vivant,
        date_deces=p.date_deces,
        telephone=p.telephone or '',
        email=p.email or '',
        type_residence=p.type_residence,
        residence_label=p.get_type_residence_display(),
        lieu_residence=p.lieu_residence or '',
        famille_id=str(p.famille_id),
        famille_nom=p.famille.nom_famille,
        village_id=str(p.famille.village_id),
        village_nom=p.famille.village.nom,
        est_chef_famille=p.est_chef_famille,
        pere_id=str(p.pere_id) if p.pere_id else None,
        pere_nom=p.pere.nom_complet if p.pere else (p.pere_nom_libre or None),
        pere_nom_libre=p.pere_nom_libre or '',
        mere_id=str(p.mere_id) if p.mere_id else None,
        mere_nom=p.mere.nom_complet if p.mere else (p.mere_nom_libre or None),
        mere_nom_libre=p.mere_nom_libre or '',
        conjoint_id=str(p.conjoint_id) if p.conjoint_id else None,
        conjoint_nom=(
            p.conjoint.nom_complet if p.conjoint else (p.conjoint_nom_libre or None)
        ),
        conjoint_nom_libre=p.conjoint_nom_libre or '',
        age=p.age,
        notes=p.notes or '',
        date_creation=p.date_creation,
        date_maj=p.date_maj,
        has_diaspora=hasattr(p, 'profil_diaspora'),
    )




class DjangoPersonRepository(PersonRepositoryInterface):

    def _qs(self, created_by_id: str = ''):
        qs = Person.objects.filter(deleted__isnull=True)
        if created_by_id:
            qs = qs.filter(created_by_id=created_by_id)
        return qs

    def get_all(
        self, q='', famille_id='', genre='',
        village_id='', created_by_id='', page=1, par_page=20
    ) -> Tuple[List['PersonLightDTO'], int]:
        qs = self._qs(created_by_id=created_by_id).select_related(
            'famille__village'
        ).order_by('nom', 'prenom')

        if q:
            qs = qs.filter(
                Q(code__icontains=q)
                | Q(nom__icontains=q)
                | Q(prenom__icontains=q)
                | Q(profession__icontains=q)
                | Q(pere_nom_libre__icontains=q)
                | Q(mere_nom_libre__icontains=q)
                | Q(conjoint_nom_libre__icontains=q)
            )
        if famille_id:
            qs = qs.filter(famille_id=famille_id)
        if genre:
            qs = qs.filter(genre=genre)
        if village_id:
            qs = qs.filter(famille__village_id=village_id)

        total    = qs.count()
        page_obj = Paginator(qs, par_page).get_page(page)
        return [_person_to_light(p) for p in page_obj], total

    def get_by_id(self, person_id, created_by_id='') -> Optional['PersonDTO']:
        try:
            p = self._qs(created_by_id=created_by_id).select_related(
                'famille__village', 'pere', 'mere', 'conjoint'
            ).get(id=person_id)
            dto        = _person_to_dto(p)
            dto.enfants       = [_person_to_light(e) for e in p.enfants]
            dto.freres_soeurs = [_person_to_light(f) for f in p.freres_soeurs]
            return dto
        except Exception:
            return None

    def create(self, data: 'CreatePersonDTO') -> 'PersonDTO':
        kwargs = {
            'nom':                    data.nom,
            'prenom':                 data.prenom,
            'surnom':                 data.surnom,
            'genre':                  data.genre,
            'famille_id':             data.famille_id,
            'date_naissance':         data.date_naissance,
            'lieu_naissance':         data.lieu_naissance,
            'nationalite':            data.nationalite,
            'numero_cni':             data.numero_cni,
            'profession':             data.profession,
            'situation_matrimoniale': data.situation_matrimoniale,
            'est_vivant':             data.est_vivant,
            'date_deces':             data.date_deces,
            'telephone':              data.telephone,
            'email':                  data.email,
            'type_residence':         data.type_residence,
            'lieu_residence':         data.lieu_residence,
            'est_chef_famille':       data.est_chef_famille,
            'pere_id':                data.pere_id,
            'pere_nom_libre':         data.pere_nom_libre,
            'mere_id':                data.mere_id,
            'mere_nom_libre':         data.mere_nom_libre,
            'conjoint_id':            data.conjoint_id,
            'conjoint_nom_libre':     data.conjoint_nom_libre,
            'notes':                  data.notes,
            'created_by_id':          data.created_by_id,
        }
        p = Person.objects.create(**kwargs)
        if data.photo:
            p.photo = data.photo
            p.save()
        return self.get_by_id(str(p.id))

    def update(self, data: 'UpdatePersonDTO') -> 'PersonDTO':
        p = Person.objects.get(id=data.id, deleted__isnull=True)
        champs = [
            'nom', 'prenom', 'surnom', 'genre', 'famille_id',
            'date_naissance', 'lieu_naissance', 'nationalite',
            'numero_cni', 'profession', 'situation_matrimoniale', 'est_vivant',
            'date_deces', 'telephone', 'email',
            'type_residence', 'lieu_residence', 'est_chef_famille',
            'pere_id', 'pere_nom_libre', 'mere_id', 'mere_nom_libre',
            'conjoint_id', 'conjoint_nom_libre', 'notes',
        ]
        for champ in champs:
            setattr(p, champ, getattr(data, champ))
        if data.photo:
            p.photo = data.photo
        p.save()
        return self.get_by_id(str(p.id))

    def delete(self, person_id) -> bool:
        try:
            p = Person.objects.get(id=person_id, deleted__isnull=True)
            p.delete()
            return True
        except Exception:
            return False

    def search_autocomplete(
        self, q, genre='', village_id='', created_by_id='', limit=15
    ) -> List['PersonSearchResultDTO']:
        if len(q) < 2:
            return []
        qs = self._qs(created_by_id=created_by_id).filter(
            Q(code__icontains=q)
            | Q(nom__icontains=q)
            | Q(prenom__icontains=q),
        ).select_related('famille__village')
        if genre:
            qs = qs.filter(genre=genre)
        if village_id:
            qs = qs.filter(famille__village_id=village_id)
        qs = qs[:limit]
        return [
            PersonSearchResultDTO(
                id=str(p.id),
                code=p.code,
                nom_complet=p.nom_complet,
                village=p.famille.village.nom,
                age=p.age,
                genre=p.genre,
                photo=p.photo.url if p.photo else None,
            )
            for p in qs
        ]

    def build_tree(
        self, person_id, profondeur_max=6
    ) -> Optional['TreeNodeDTO']:
        try:
            p = Person.objects.get(
                id=person_id, deleted__isnull=True
            )
            return self._node(p, profondeur_max, 0)
        except Exception:
            return None

    def _node(self, p, max_depth, niveau) -> 'TreeNodeDTO':
        enfants = []
        if niveau < max_depth:
            for enfant in p.enfants.select_related('conjoint'):
                enfants.append(self._node(enfant, max_depth, niveau + 1))
        return TreeNodeDTO(
            id=str(p.id),
            nom_complet=p.nom_complet,
            prenom=p.prenom,
            nom=p.nom,
            genre=p.genre,
            age=p.age,
            est_vivant=p.est_vivant,
            photo=p.photo.url if p.photo else None,
            conjoint=p.conjoint.nom_complet if p.conjoint else None,
            generation=niveau,
            date_naissance=p.date_naissance,
            date_deces=p.date_deces,
            residence_label=p.get_type_residence_display(),
            lieu_residence=p.lieu_residence or '',
            enfants=enfants,
        )
