# My files
import copy

from util.CHtools import CHtools
from util.dataclasses.Instruct import Instruct
from util.dataclasses.baseclass import Base
from util.dataclasses.dataContainer import DataContainer
from util.dataclasses.tableLogistic import TableCreator, CollCreator
from util.dicts.import_types import import_table_schemes, setDate_scheme
from util.dicts.typeDict import typeDict
from util.logsetup import logtable_name

# Lib
import logging

class TableCheck(Base):
    """
    This class checks if a file matches the desired import-table in the database on a logical level.
    The functionality of this class previously was part of the Analyzer.

    It performs the following steps:
    - check if the header-field of the data-container already contains information.
      if not, we try to collect it by consuming the first few generator lines.
    - check if the header-filed of the data-container matches the expected header-field for this import-type
    - checks for double import
    - creates the desired table in the ClickHouse database, if not already existent

    Information: This pipeline stage doesn't interact with the data. It only looks at the header- and
    table-information, not into the data-generator itself!
    """

    # Get logger for this stage
    logger = logging.getLogger("importheus.tablechecker")

    # Manual Header (can be set in subclass when file does not container headers)
    manual_header: list[str] = None

    def __init__(self, chtool: CHtools, meta: Instruct):
        self.chtool = chtool # the CHtool to communicate with the database
        self.meta = meta # meta info for this import to get header information
        # Load reference-data for the current import data from import_type-dict
        self.reference : list[CollCreator] = import_table_schemes.get(self.meta.type, []).copy()

    def _head_list(self) -> dict[str, str]:
        """
        helper function that extracts the column-types from the TableBuilder in the subclass for easier checking
        it ignores the setDate because it is artificially added
        Returns: dict of columns names mapped to the types from our table

        """
        returner: dict[str, str] = {}
        for elem in self.reference:
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
            self.logger.error(f"File seems to have unmatching header length for a {self.meta.type}. "
                              f"There are {len(header)} fields "
                              f"but we expect {len(should_be)} fields. Look at them:\n"
                              f"Actual:   {header}\n"
                              f"Expected: {should_be}\n")
            return False

        if not self.reference:
            # check if this type was not found / is empty / faulty
            self.logger.error(f"Import-Type {self.meta.type} not known in import_type_dict")
            return False

        # iterate over every item in the template and search it in the header
        for i, elem in enumerate(self.reference):
            if elem.name not in header:
                self.logger.error(f"File seems to not be the expected type. Header fields do not contain field "
                                  f"\"{elem.name}\" that is expected from table definition")
                return False
            if typeDict.get(self.reference[i].type) is None:
                self.logger.error(f"Header name \"{header[i]}\" in column {i} with CH-type "
                                  f"\"{self.reference[i].type}\" is unknown in typeDict! "
                                  f"Please update the typeDict with this type!")
                return False
        # If no errors occurred -> return true
        return True

    def build_table(self) -> None:
        """
        creates the table for this type if it is not already created.
        if the table is already existent, it checks if the syntax is as expected
        needs to be here because we need the table-type information from the specific import_types

        """
        if not self.chtool.table_exists(self.meta.table):
            # not existing: create with through an inline TableCreator instance based on a reference-copy
            if self.meta.table != logtable_name:
                # if it is not a logtable, we add the set-date Column
                self.reference.append(setDate_scheme)
            # actual table creation command in to clickhouse
            self.chtool.create_table(TableCreator(self.meta.table, copy.copy(self.reference)))
        else:
            # table name already existing, we need to check for syntax match
            extract: dict[str,str] = self.chtool.get_table_scheme(self.meta.table)
            # ch_names normally contains setDate while our_names obviously does not. Remove
            extract.pop("setDate", None)

            # Check Column-Names (need not be in order)
            ch_names: list[str] = list[str](extract.keys())
            our_names: list[str] = list[str](self._head_list().keys())
            if ch_names != our_names:
                self.logger.critical(f"Table {self.meta.table} already exists but has different column names\n"
                                     f"Expected: {our_names}\n"
                                     f"Actual:   {ch_names}")

            # Check Column-Types
            ch_types: list[str] = list[str](extract.values())
            our_types: list[str] = list[str](self._head_list().values())
            if ch_types != our_types:
                self.logger.critical(f"Table {self.meta.table} already exists but has different datatypes\n"
                                     f"Expected: {our_types}\n"
                                     f"Actual:   {ch_types}")

    def execute(self, data: DataContainer) -> DataContainer | None:
        """
        Main function from this class.
        Unites all helper functions.

        Args:
            data: DataContainer from a previous stage

        Returns: DataContainer for the next stage

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
        if self.chtool.lookout(self.meta.filepath, logtable_name, "file"):
            if not self.meta.force:  # we do not want to force the import
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
        # return the unmodified data-container for the next pipeline stage
        return data
