from dataclasses import dataclass, fields
from types import UnionType, NoneType
from typing import get_origin, Union


def canBeNone(tp) -> bool:
    ''' Prüft, ob der Typ tp None annehmen kann. '''
    if get_origin(tp) is Union or get_origin(tp) is UnionType:
        return any(canBeNone(subtp) for subtp in tp.__args__)
    return tp is NoneType or tp is None


def typeChecked(cls):
    original_init = cls.__init__
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        for field in fields(cls):
            value = getattr(self, field.name)
            expected_type = field.type
            if not isinstance(value, expected_type):
                raise TypeError(f"Expected {field.name} to be {expected_type}, "
                                f"got {type(value)}")
            if canBeNone(expected_type) and hasattr(value, 'isAllNone') and value.isAllNone():
                setattr(self, field.name, None)
    def isAllNone(self):
        for field in fields(cls):
            if getattr(self, field.name) is not None: return False
        return True
    cls.__init__ = new_init
    cls.isAllNone = isAllNone
    return cls


@typeChecked
@dataclass
class Address:
    street: str 
    plz: int
    town: str
    district: str


@typeChecked
@dataclass
class Authority:
    name: str
    url: str | None
    

@typeChecked
@dataclass
class Sponsor:
    sponsorType: str | None
    name: str | None


@typeChecked
@dataclass
class School:
    state: str
    id: str
    name: str
    authority: Authority | None
    address: Address | None
    phone: str | None
    fax: str | None
    email: str | None
    url: str | None
    principal: str | None
    vicePrincipal: str | None
    students: int | None
    teachers: int | None
    classes: int | None
    description: str | None
    sponsor: Sponsor | None
