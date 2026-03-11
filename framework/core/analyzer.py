# My files
from typing import Generator

from core.clickhouse import ClickHouse, TableCreator, CollCreator
from util.dataclasses.Instruct import Instruct
from util.dataclasses.baseclass import base

# Lib
import logging
from datetime import datetime
from abc import ABC
import copy

from util.dataclasses.dataContainer import DataContainer
from util.logsetup import logTable, logtable_name
from util.typeDict import typeDict


class Analyzer(base, ABC):
    """
    Second stage after Decoding. Class that analyzes the raw dataContainer that comes from the Rowizer and checks
    for broken lines, unconventional things and potential problems.
    Determines the data-types for columns and builds a "refined" dataFrame from it.

    """
    # Get logger for this stage
    logger = logging.getLogger("importheus.analyzer")

    # Type of the Analyzer, overwritten from subclass
    import_type: str

    # Definition on the layout of the type-table, overwritten from subclass (includes setDate)
    table: TableCreator

    # Database that is used to create tables and to insert to import-log
    database: ClickHouse

    # Instructions from the JSON that are used for this file (the logtable uses it)
    meta: Instruct

    # The columns list defined in the subclass
    columns: list[CollCreator]

    # Returner
    returner: DataContainer

    # Manual Header (can be set in subclass when file does not container headers)
    manual_header: list[str] = None

    def __init__(self, database: ClickHouse, meta: Instruct):
        """
        Constructor that sets the clickhouse handler for the analyzer
        Args:
            database: the clickhouse handler
        """
        self.database = database
        self.meta = meta
        self.table = TableCreator(name=meta.table, columns=copy.copy(self.columns))
        self.returner = DataContainer()

        if self.meta.table != logtable_name:
            # we append the obligatory setDate Column (except it is a logtable)
            self.table.columns.append(CollCreator("setDate", "String"))  # TODO DateTime

    def __init_subclass__(cls, **kwargs):
        """
        hook that registers subclasses on definition in the AnalyzeRegistry for easy plug and play of new analyzers
        Args:
            **kwargs: debug
        """
        ext = cls.import_type
        if ext:
            AnalyzeRegistry.register(ext, cls)

    def logtable(self, good: int, bad: int) -> None:
        """
        function that analyses the code and logs everything that has a problem. How many Imports, timestamp,
        how many problems, etc.
        merge with execute?

        Args:
            good: number of rows that this file has
            bad: error-rows that this file threw on import
        """

        if not self.database.table_exists(logtable_name):
            self.database.create_table(logTable)

        # Inserting the data
        # TODO generating correct UUID / Index
        data = [0, datetime.now(), self.meta.filepath, self.meta.type, self.meta.table, good + bad, good, bad]
        self.database.insert_row(logtable_name, data)

    def _head_list(self) -> dict[str, str]:
        """
        helper function that extracts the column-types from the TableBuilder in the subclass for easier checking
        it ignores the setDate because it is artificially added
        Returns: dict of columns names mapped to the types from our table

        """
        returner: dict[str, str] = {}
        for elem in self.columns:
            returner.update({elem.name: elem.type})
        return returner

    def checkHeader(self, header: list) -> bool:
        """
        helper function for execute() that analyzes the integrity of the header of a file
        Returns true if header fields are complete and in line with the planned ClickHouse table
        Returns false if header fields are missing, empty or not in line with planned ClickHouse table
        Different arrangement is ok and returns true
        Args:
            header: the header of the file that should be analyzed

        Returns: bool if we can proceed analyzing the rows or if the desired type does not match with the actual data

        """
        should_be: list[str] = list(self._head_list().keys())
        if len(header) != len(should_be):
            # Header is not as long as expected, print reference where something went wrong
            self.logger.error(f"File seems to have unmatching header length for a {self.import_type}. "
                              f"There are {len(header)} fields "
                              f"but we expect {len(should_be)} fields. Look at them:\n"
                              f"Actual:   {header}\n"
                              f"Expected: {should_be}\n")
            return False
        # iterate over every item in the template and search it in the header
        for i, elem in enumerate(self.columns):
            if elem.name not in header:
                self.logger.error(f"File seems to not be the expected type. Header fields do not contain field "
                                  f"\"{elem.name}\" that is expected from table definition")
                return False
            if typeDict.get(self.columns[i].type) is None:
                self.logger.error(f"Header name \"{header[i]}\" in column {i} with CH-type "
                                  f"\"{self.table.columns[i].type}\" is unknown in typeDict! "
                                  f"Please update the typeDict with this type!")
                return False
        # If no errors occurred -> return true
        return True

    def checkRow(self, row: dict[str, str], it: int) -> bool:
        """
        helper function for execute() that analyzes the integrity of one row of data.
        Returns true if all fields are filled and the syntax & data-types are correct
        Returns false if there are empty fields, wrong syntax or wrong data-types
        Can be in the generic class because of the typeDict that handles the data
        potential parallelism
        Args:
            row: one row as a dict[name: str, type: str]

        Returns: bool if the row is intact or should go into the err-list

        """
        # Check if the length of the row is the same as expected
        should_be = len(list(self._head_list().keys()))
        if should_be != len(row)-1:
            # if not -> instant err
            self.logger.error(f"Row {it} has {len(row)} elements but should have {should_be}")
            return False

        dictus: dict[str, str] = {col.name: col.type for col in self.table.columns}
        # Iterate over every item in the row and check if it matches the datatype described in the header
        for i, (name, value) in enumerate(row.items()):
            if value == "" or value == " ":
                # Field is empty
                self.logger.error(f"Row {it} has an empty value for \"{name}\"")
                return False
            try:
                # Check if we know this name in the typeDict
                if typeDict.get(dictus[name])(value):
                    continue  # there is no problem -> next field
            except ValueError:
                # ignore the error specifics
                pass
            # We had a problem wit the cast -> this field is not as we want it to be
            self.logger.error(f"Element {i} of row {it} has an invalid item. "
                              f"Should be \"{name}\" but looks like \"{value}\"")
            return False

        # If no errors occurred -> return true
        return True

    def build_table(self) -> None:
        """
        creates the table for this type if it is not already created.
        if the table is already existent, it checks if the syntax is as expected
        needs to be here because we need the table-type information from the specific Analyzer

        """
        if not self.database.table_exists(self.meta.table):
            # not existing: create with self.tableCreator
            self.database.create_table(self.table)
        else:
            # table name already existing, we need to check for syntax match

            # Check Column-Names (need not be in order)
            ch_names: set[str] = set(list(self.database.get_table_scheme(self.meta.table).keys()))
            our_names: set[str] = set(self._head_list().keys())
            if ch_names != our_names:
                self.logger.critical(f"Table {self.meta.table} already exists but has different column names\n"
                                     f"Expected: {our_names}\n"
                                     f"Actual:   {ch_names}")

            # Check Column-Types
            ch_types: set[str] = set(self.database.get_table_scheme(self.meta.table).values())
            our_types: set[str] = set(self._head_list().values())
            if ch_types != our_types:
                self.logger.critical(f"Table {self.meta.table} already exists but has different datatypes\n"
                                     f"Expected: {our_types}\n"
                                     f"Actual:   {ch_types}")

    def execute(self, data: DataContainer) -> DataContainer | None:
        """
        Main function from this class. unites all helper functions.

        Args:
            data: the raw DataContainer from the Decoding stage

        Returns: a new DataContainer

        """
        # Check if there is already a header here
        if not data.head:
            # No header -> Check if we got one from definition
            if self.manual_header is not None:
                # set header from manual definition
                data.head = self.manual_header
            else:
                # we got no header & we got no manual header
                try:
                    while not data.head:
                        # Push Iterator until we get the head
                        next(data.rawData)
                except StopIteration:
                    self.logger.critical(f"Problem with reading header of \"{self.meta.filepath}\". Skipping this file")
                    self.meta.bad = True
                    return None

        # Check if the data was imported already before (is filepath in Import-History?)
        if self.database.lookout(self.meta.filepath, logtable_name, "file"):
            if not self.meta.force: # we do not want to force the import
                # there is an entry -> STOP -> no double import
                self.logger.critical(f"Potential Double Import of file \"{self.meta.filepath}\". Skipping this file")
                self.meta.bad = True
                return None
            else:
                # double import and force is set -> notify and continue
                self.logger.info(f"Potential Double Import of file \"{self.meta.filepath}\". Force importing it.")

        if not self.checkHeader(data.head):
            # the header is not equal to the database-header error message already sent
            self.meta.bad = True
            return None

        # Create table for this type if not already happened.
        self.build_table()

        # Check each row of data for syntax problems / empty fields
        def internal_for_yield() -> Generator[dict[str, str]]:
            counter: int = 0  # how many good rows
            total_counter: int = 2  # total row-counter for logging in checkRow
            try:
                for row in data.rawData:
                    if not self.checkRow(row, total_counter):  # row has a problem
                        self.returner.error.append(row)  # put in error list of returner & don't yield
                    else:
                        counter += 1  # one mor good row
                        yield row
                    total_counter += 1
            finally:
                # Final execution when all rows are analyzed, logging
                self.logtable(counter, len(self.returner.error))

        self.returner.head = data.head
        self.returner.rawData = internal_for_yield()

        # Return the new DataContainer
        return self.returner


class AnalyzeRegistry:
    _registry = {}  # all Analyzers live here

    @classmethod
    def register(cls, import_type: str, analyzer_class: Analyzer) -> None:
        """
        registers a new analyzer class in the analyzer-registry
        needs to be done for every new analyzer (that implements a new file type)

        Args:
            import_type: string that describes the file ending (to parse later)
            analyzer_class: class that contains the analyzing functionality for this class

        """
        cls._registry[import_type] = analyzer_class

    @classmethod
    def get_analyzer(cls, import_type):
        """
        factory method that gives you a specific decoder-Object suitable for a specific file ending
        Args:
            import_type: the file ending you want to decode

        Returns: a suitable decoder for this specific file ending

        """
        return cls._registry.get(import_type)
