import datetime
import ipaddress
from typing import Callable
from dateutil.parser import parse

"""
Here lies the logic for the translation from ClickHouse DataTypes to Python datatypes.
It is a dict with the name of the ClickHouse Datatype and a lambda Function that tests if a specific element is
from the desired python type.
Note: It is still possible that ClickHouse has a Problem with some Data that is accepted here beacuse
Python and ClickHouse Datatypes are not completely the same. But it should do the job most of the time.
If a new Analyzer with new header-fields is added, they need to be registered here!

The analyzers use this function to determine if a
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
