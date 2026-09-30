import datetime
import ipaddress
from ipaddress import IPv4Address, IPv6Address
from typing import Callable, Annotated, Literal, Any
from dateutil.parser import parse
from pydantic import TypeAdapter, Field, ValidationError

"""
Here lies the logic for the translation from ClickHouse DataTypes to Python datatypes.
It is a dict with the name of the ClickHouse Datatype and a lambda Function that tests if a specific element is
from the desired python type.
Note: It is still possible that ClickHouse has a Problem with some Data that is accepted here beacuse
Python and ClickHouse Datatypes are not completely the same. But it should do the job most of the time.
If a new import_types with new header-fields is added, they need to be registered here!

The analyzers use this function to determine if a value is im the expected format for ClickHouse.

Deprecated. We now use ClickHouse
"""

typeDict: dict[str, Callable[[any], bool]] = {
    "UInt8": lambda v: isinstance(int(v), int) and 0 <= int(v) <= 65535,
    "UInt16": lambda v: isinstance(int(v), int) and 0 <= int(v) <= 65535,
    "UInt32": lambda v: isinstance(int(v), int) and int(v) >= 0,
    "Int32": lambda v: isinstance(int(v), int),
    "String": lambda v: isinstance(v, str),

    "Date": lambda v: isinstance(parse(v), datetime.date),

    "DateTime": lambda v: isinstance(parse(v), datetime.datetime),

    "IPv4": lambda v: ipaddress.ip_address(v), # throws value error if not the case
    "IPv6": lambda v: ipaddress.ip_address(v), # throws value error if not the case

    "Enum8('offline' = 1, 'online' = 2)": lambda v: v in ("online", "offline"),
}

typeDictPydantic: dict[str, TypeAdapter] = {
    "UInt8": TypeAdapter(Annotated[int, Field(ge=0, le=255)]),
    "UInt16": TypeAdapter(Annotated[int, Field(ge=0, le=65535)]),
    "UInt32": TypeAdapter(Annotated[int, Field(ge=0, le=4_294_967_295)]),
    "Int32": TypeAdapter(Annotated[int, Field(ge=-2_147_483_648, le=2_147_483_647)]),
    "String": TypeAdapter(str),

    "Date": TypeAdapter(datetime.date),

    "DateTime": TypeAdapter(datetime.datetime),

    "IPv4": TypeAdapter(IPv4Address),
    "IPv6": TypeAdapter(IPv6Address),

    "Enum8('offline' = 1, 'online' = 2)": TypeAdapter(Literal["online", "offline"]),
}


def validate_value(type_name: str, value: Any) -> bool:
    """
    Function that uses the new typeDictPydantic to check a specific value.
    Args:
        type_name: the ClickHouse Type name that the value should be
        value: the value that should be checked for compatibility.

    Returns: Bool if the value can be the type_name or not

    """
    adapter = typeDictPydantic.get(type_name)
    if adapter is None:
        # Type not in typeDict
        return False

    try:
        adapter.validate_python(value)
        return True
    except ValidationError:
        return False
