import numbers

import requests, json
from typing import Optional, List, Dict, Any

from attr import dataclass, field

ioBroker_url = 'xyz'


class IoBroker:
    def __init__(self):
        pass

    @staticmethod
    def _get(query):
        try:
            raise Exception('use offline')
            content = json.loads(requests.get(ioBroker_url + query).content)
            with open('serialized/allObjects.json', 'w', encoding='utf-8') as f:
                f.write(json.dumps(content))
                print('online')
            return content
        except:
            print('offline, using cache')
            with open('serialized/ioBroker.json', 'r', encoding='utf-8') as f:
                return json.loads(f.read())

    @staticmethod
    def _set(query, data):
        requests.get(ioBroker_url + query, data=data)

    def getObjects(self):
        return IoBroker._get('objects')


ioBroker = IoBroker()


@dataclass
class Acl:
    object: Optional[int]
    state: Optional[int]
    file: Optional[int]
    owner: Optional[str]
    ownerGroup: Optional[str]

    @staticmethod
    def fromJson(j):
        return Acl(
            object=j.get('object', None),
            state=j.get('state', None),
            file=j.get('file', None),
            owner=j.get('owner', None),
            ownerGroup=j.get('ownerGroup', None)
        )


@dataclass
class Common:
    name: str
    def_: bool
    type: str
    read: bool
    write: bool
    role: str
    min: Optional[numbers.Number]
    max: Optional[numbers.Number]
    states: Optional[Dict[str, str]]

    @staticmethod
    def fromJson(j):
        return Common(
            name=j.get('name', None),
            def_=j.get('_def', None),
            type=j.get('type', None),
            read=j.get('read', None),
            write=j.get('write', None),
            role=j.get('role', None),
            min=j.get('min', None),
            max=j.get('max', None),
            states=j.get('states', None)
        )


@dataclass
class IOBrokerState:
    id: str
    type: str
    common: Optional[Common]
    native: Optional[Dict[str, Any]]
    from_: str
    user: str
    ts: int
    acl: Optional[Acl]
    enums: Dict[str, str]

    def toDict(self):
        return self._todict(self)

    @staticmethod
    def _todict(obj, classkey=None):
        if isinstance(obj, dict):
            data = {}
            for (k, v) in obj.items():
                data[k] = IOBrokerState._todict(v, classkey)
            return data
        elif hasattr(obj, "_ast"):
            return IOBrokerState._todict(obj._ast())
        elif hasattr(obj, "__iter__") and not isinstance(obj, str):
            return [IOBrokerState._todict(v, classkey) for v in obj]
        elif hasattr(obj, "__dict__"):
            data = dict([(key, IOBrokerState._todict(value, classkey))
                         for key, value in obj.__dict__.items()
                         if not callable(value) and not key.startswith('_') and not value is None])
            if classkey is not None and hasattr(obj, "__class__"):
                data[classkey] = obj.__class__.__name__
            return data
        else:
            return obj

    def toString(self):
        return json.dumps(self.toDict(), indent=2, sort_keys=True)

    @staticmethod
    def fromJson(j):
        common = j.get('common', None)
        if common is not None:
            common = Common.fromJson(common)
        acl = j.get('acl', None)
        if acl is not None:
            acl = Acl.fromJson(acl)
        return IOBrokerState(
            id=j.get('_id', None),
            type=j.get('state', None),
            common=common,
            native=j.get('native', None),
            from_=j.get('from', None),
            user=j.get('user', None),
            ts=j.get('ts', 0),
            acl=acl,
            enums=j.get('enums', None)
        )

