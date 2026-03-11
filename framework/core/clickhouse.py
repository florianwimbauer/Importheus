# Class that will talk to the ClickHouse Database for Importing

# Libs
import clickhouse_connect
import logging
from sqlalchemy import create_engine
from typing import List, Optional, Generator, Union
from itertools import batched
import pandas as pd

# My Files
from util.dataclasses.Instruct import Instruct
from util.dataclasses.baseclass import base
from dataclasses import dataclass, field
from util.dataclasses.dataContainer import DataContainer


@dataclass
class ChAccess:
    """
    Dataclass argState that saves all the information needed for connection with the local
    ClickHouse Server instance. It is default hardcoded if no access data is given in the CLI
    WARNING: can only connect to localhost database as different Information would be needed if it shall connect
    to a database in the cloud!
    """
    host: str = "localhost"
    username: str = "default"
    password: str = "default"

    def __init__(self, username, password):
        if password is not None:
            self.password = password
        if username is not None:
            self.username = username


@dataclass
class CollCreator:
    """
    dataclass for defining a new Column of a Table
    """
    name: str
    type: str
    default: Optional[str] = None
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


class ClickHouse(base):
    """
    Class that handles the interaction with ClickHouse. New object created for each file that shall be imported
    """

    # Setup SQL Engine
    alchemy_engine = create_engine("clickhouse+http://default:@localhost/default")

    # Setup logger
    logger = logging.getLogger("importheus.Clickhouse")

    # Save import instructions from json to know to which table to import
    meta: Instruct

    # Save how big a batch should be
    batchsize: int

    def __init__(self, ch_access: ChAccess, meta: Instruct, batchsize: int):
        """
        Constructor, connects this object with the desired ClickHouse server on localhost
        Connect to the database that is created in the setup script (always the same, only different tables)
        Args:
            ch_access: CH_access instance that contains the information for which ClickHouse Database to connect to
        """
        self.database = clickhouse_connect.get_client(
            host=ch_access.host,
            username=ch_access.username,
            password=ch_access.password
        )
        self.meta = meta
        self.batchsize = batchsize

    def table_exists(self, table: str) -> bool:
        """
        queries the database to test if a table with the given parameters does exist or not
        Args:
            table: to look for

        Returns: bool if it exists or not

        """
        # Create query for this table
        query = f"SELECT count() FROM system.tables WHERE database='default' AND name='{table}'"

        # test if more than 0 results came back
        return self.database.query(query).result_rows[0][0] > 0

    def create_table(self, table: TableCreator) -> None:
        """
        Creates a table in the ClickHouse database that is connected to this instance

        """
        if self.table_exists(table.name):
            self.logger.warning(f"Table {table.name} already exists!")
            return

        # send request to database
        self.database.command(table.to_sql())

    def insert_row(self, table: str, data: list) -> None:
        """
        wrapper that inserts the given list (with given data without types) into this database.
        Warning: No in-flight datatype checking! Force insert only catches exception
        WARNING: Inserts only one line! Use carefully only for logtable entry. No productive batch-imports with this
        function!

        Args:
            table: table where the insert should take place
            data: one data-row (without typehint) that should be inserted

        """
        if not self.table_exists(table):
            self.logger.critical(f"Table {table} does not exist! Can not be inserted")
            return
        # actual insert as list with one entry
        try:
            self.database.insert(table, [data])
        except Exception as e:
            self.logger.error(f"Forced Single-Row insert failed: \"{e}\"")

    def get_table_scheme(self, table: str) -> dict:
        """
        gets the syntax of an existing table from clickhouse. Can be matched with util/typeDict
        Args:
            table: that we want the syntax from

        Returns: a dict with ("ColumnName" : "CH-Datattyp")

        """
        query = f"""
            SELECT name, type 
            FROM system.columns 
            WHERE database = 'default' AND table = '{table}'
            ORDER BY position
            """
        result = self.database.query(query)

        scheme = {row[0]: row[1] for row in result.result_rows}
        return scheme

    def lookout(self, entry: str, table: str, column: str) -> bool:
        """
        function that looks at a specific column of a specific table for a specific entry and tells if it is there
        Args:
            entry: look for the entry we want to find
            table: look in this table
            column: look in this column

        Returns: bool if we found what we were looking for

        """
        query = f"""
                SELECT count() 
                FROM default.{table} 
                WHERE {column} = '{entry}'
                LIMIT 1
            """
        try:
            result = self.database.query(query)
            # table we want to search for does not exist yet
        except Exception as e:
            # something went wrong -> give back false!
            self.logger.warning(f"Lookup in table {table} failed - something went wrong:\n{e}")
            return False  # because if table does not exist -> data not there (need not bee a problem)
        # if query finished, we can compute real result
        return result.result_rows[0][0] > 0

    # Function that executes the class, main thing in here. Is called by the pipeline in main
    def execute(self, container: DataContainer) -> None:
        """
        MAIN FUNCTION of this class for the Importing-pipeline
        Implementation of the abstract baseclass function execute for the pipeline
        We assume that the table already exists (the analyzer did this for us)
        Args:
            container: the DataContainer that shall be imported to the ClickHouse Database connected to this instance
        """
        if container is None:
            self.logger.warning("Nothing to import for this file. Datatainer is empty")
            return

        if not self.table_exists(self.meta.table):
            self.logger.critical(f"Table {self.meta.table} did not exist on import but was expected to."
                                 f" Something went wrong internally in the analyzer!")
            return

        # Prepare batch insert - Itertools.batched() functionality
        try:
            for batch in batched(container.rawData, self.batchsize):
                # Iterate over all batches that shall be imported
                to_import = pd.DataFrame(list(batch))
                self.database.insert_df(self.meta.table, to_import)
        except Exception as e:
            self.logger.critical(f"Pipelined Batch insert went wrong:\n{e}")
