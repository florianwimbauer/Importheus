# This file houses the TableCreator and the Coll Creator.
# Those classes are used to describe a structure of a table

from typing import List, Optional, Union
from dataclasses import dataclass, field

@dataclass
class CollCreator:
    """
    dataclass for defining a new Column of a Table
    """
    name: str
    type: str
    default: Optional[str] = None
    optional: Optional[bool] = False
    codec: Optional[Union[str, List[str]]] = None

    def to_sql(self) -> str:
        """
        function that makes SQL Code from the Column
        Returns: the SQL string

        """
        returner = [f"{self.name} {self.type}"]

        if self.codec:
            if isinstance(self.codec, list):
                codec_sql = ", ".join(self.codec)
            else:
                codec_sql = self.codec
            returner.append(f"CODEC({codec_sql})")

        return " ".join(returner)


@dataclass
class TableCreator:
    """
    dataclass for defining a new Table in ClickHouse.
    Uses CollCreator directly
    """
    name: str
    columns: list[CollCreator]
    engine: str = "ReplacingMergeTree"
    order_by: List[str] = field(default_factory=list)
    partition_by: Optional[str] = None

    def to_sql(self) -> str:
        """
        function that makes SQL Code from the whole Table (to create)
        Returns: the SQL string

        """
        cols_sql = ",\n  ".join(col.to_sql() for col in self.columns)

        # Partition
        partition_sql = f"PARTITION BY {self.partition_by}" if self.partition_by else ""

        effective_order = self.order_by or [self.columns[0].name]
        order_sql = f"ORDER BY ({', '.join(effective_order)})"

        sql = (
            f"CREATE TABLE IF NOT EXISTS {self.name} (\n  {cols_sql}\n)"
            f" ENGINE = {self.engine} {partition_sql} {order_sql}"
        ).strip()

        return sql