from core.analyzer import Analyzer
from core.clickhouse import CollCreator


class BlacklistsAnalyzer(Analyzer):
    """
    Analyzing Logic for blacklist-imports, derives from abstract Analyzer and baseclass
    setDate gets added automatically
    """
    import_type = "blacklist"

    columns=[
        CollCreator("first_seen_utc", "String"), # TODO DateTime
        CollCreator("dst_ip", "IPv4"),
        CollCreator("dst_port", "UInt16"),
        CollCreator("c2_status", "Enum8('offline' = 1, 'online' = 2)"),
        CollCreator("last_online", "String"), # TODO Date
        CollCreator("malware", "String")
    ]