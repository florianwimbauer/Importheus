from util.dataclasses.tableLogistic import CollCreator

"""
This file houses a dict that translates import_types into table syntax.
This was former implemented in the child-classes of the great analyzer class (that is now split into analyzer
and tablecheck)

In case a field should be optional, just add optional=True as a third argument
"""

import_table_schemes: dict[str, list[CollCreator]] = {
    "aspop": [
        CollCreator("rank", "UInt32"), # TODO DateTime
        CollCreator("asn", "String"),
        CollCreator("descr", "String"),
        CollCreator("cc", "String"),
        CollCreator("users", "UInt32"), # TODO Date
        CollCreator("country_percent", "UInt8"),
        CollCreator("internet_percent", "UInt8"),
        CollCreator("samples", "UInt32")
    ],
    "blacklist" : [
        CollCreator("first_seen_utc", "String"), # TODO DateTime
        CollCreator("dst_ip", "IPv4"),
        CollCreator("dst_port", "UInt16"),
        CollCreator("c2_status", "Enum8('offline' = 1, 'online' = 2)"),
        CollCreator("last_online", "String"), # TODO Date
        CollCreator("malware", "String")
    ]
}

# CollCreator that describes the setDate column
setDate_scheme: CollCreator = CollCreator("setDate", "String") # TODO DateTime