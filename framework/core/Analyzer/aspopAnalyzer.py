from core.analyzer import Analyzer
from core.clickhouse import CollCreator


class AspopAnalyzer(Analyzer):
    """
    Analyzing Logic for apnic-aspop-imports, derives from abstract Analyzer and baseclass
    setDate gets added automatically on creation in ClickHouse ;)
    """
    import_type = "aspop"

    columns=[
        CollCreator("rank", "UInt32"), # TODO DateTime
        CollCreator("asn", "String"),
        CollCreator("descr", "String"),
        CollCreator("cc", "String"),
        CollCreator("users", "UInt32"), # TODO Date
        CollCreator("country_percent", "UInt8"),
        CollCreator("internet_percent", "UInt8"),
        CollCreator("samples", "UInt32")
    ]