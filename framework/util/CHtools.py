import sys
from dataclasses import dataclass
import clickhouse_connect
import logging

from asynch.errors import OperationalError
from clickhouse_connect.driver.exceptions import DatabaseError
from pandas import DataFrame
from util.dataclasses.tableLogistic import TableCreator


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
    database: str = "default"

    def __init__(self, username: str, password: str, database: str):
        if password is not None:
            self.password = password
        if username is not None:
            self.username = username
        if database is not None:
            self.database = database

class CHtools:
    """
    This class talks to the ClickHouse Database.
    It is used by every part that needs information from ClickHouse. Communication with the database takes place
    only via this class
    """

    logger = logging.getLogger("importheus.CHtools")

    def __init__(self, ch_access: ChAccess):
        """
        Constructor, connects this object with the desired ClickHouse server on localhost
        Connect to the database that is created in the setup script (always the same, only different tables)
        Args:
            ch_access: CH_access instance that contains the information for which ClickHouse Database to connect to
        """
        try:
            self.db_handle = clickhouse_connect.get_client(
                host=ch_access.host,
                username=ch_access.username,
                password=ch_access.password
            )
        except OperationalError as op_err:
            self.logger.critical(f"Connection to Clickhouse failed: \n{op_err}")
            sys.exit(1)
        except DatabaseError as db_err:
            self.logger.critical(f"Connection to ClickHouse failed. Authentication Problems: \n{db_err}")
            sys.exit(1)

        self.database = ch_access.database

    def table_exists(self, table: str) -> bool:
        """
        queries the database to test if a table with the given parameters does exist or not
        Args:
            table: to look for

        Returns: bool if it exists or not

        """
        # Create query for this table
        query = f"SELECT count() FROM system.tables WHERE database='{self.database}' AND name='{table}'"

        # test if more than 0 results came back
        return self.db_handle.query(query).result_rows[0][0] > 0

    def create_table(self, table: TableCreator) -> None:
        """
        Creates a table in the ClickHouse database that is connected to this instance.
        If the table already exists, it does nothing.

        Args:
            table: TableCreator instance that describes the desired table

        Returns: nothing

        """
        if self.table_exists(table.name):
            self.logger.warning(f"Table {table.name} already exists!")
            return

        # send request to database
        self.db_handle.command(table.to_sql())

    def insert_row(self, table: str, data: list) -> None:
        """
        wrapper that inserts the given list (with given data without types) into the connected database.
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
            self.db_handle.insert(table, [data])
        except Exception as e:
            self.logger.error(f"Forced Single-Row insert failed: \"{e}\"")

    def get_table_scheme(self, table: str) -> dict:
        """
        gets the syntax of an existing table from the connected ClickHouse database.
        Intended to be matched with util/typeDict
        Args:
            table: that we want the syntax from

        Returns: a dict with ("ColumnName" : "CH-DataType")

        """
        query = f"""
            SELECT name, type 
            FROM system.columns 
            WHERE database = '{self.database}' AND table = '{table}'
            ORDER BY position
            """
        result = self.db_handle.query(query)

        scheme = {row[0]: row[1] for row in result.result_rows}
        return scheme

    def lookout(self, entry: str, table: str, column: str) -> bool:
        """
        function that looks at a specific column of a specific table in the connected ClickHouse database
        for a specific entry and tells if it is there

        Args:
            entry: look for the entry we want to find
            table: look in this table
            column: look in this column

        Returns: bool if we found what we were looking for

        """
        query = f"""
                SELECT count() 
                FROM {self.database}.{table} 
                WHERE {column} = '{entry}'
                LIMIT 1
            """
        try:
            result = self.db_handle.query(query)
            # table we want to search for does not exist yet
        except Exception as e:
            # something went wrong -> give back false!
            self.logger.warning(f"Lookup in table {table} failed - something went wrong:\n{e}")
            return False  # because if table does not exist -> data not there (need not bee a problem)
        # if query finished, we can compute real result
        return result.result_rows[0][0] > 0

    def productiveInsert(self, table: str, to_import: DataFrame) -> None:
        """
        Function that inserts a DataFrame into the connected ClickHouse Database
        Warning: No exception handling! Must be done in the importing stage!
        Args:
            table: Str with the name of the table we want to insert to
            to_import: DataFrame with the batch-data we want to insert

        Returns:

        """
        self.db_handle.insert_df(table, to_import)