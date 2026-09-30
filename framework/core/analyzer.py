# My files
from util.dicts import typeDict
from util.dicts.import_types import (import_table_schemes, setDate_scheme)
from util.CHtools import CHtools
from util.dataclasses.Instruct import Instruct
from util.dataclasses.baseclass import Base
from util.dataclasses.dataContainer import DataContainer
from util.logsetup import logTable, logtable_name
from util.dicts.typeDict import typeDictPydantic

# Lib
import logging
from typing import Generator
from datetime import datetime

class Analyzer(Base):
    """
    Second stage after Decoding. Class that analyzes the raw dataContainer that comes from the Rowizer and checks
    for broken lines, unconventional things and potential problems.
    Determines the data-types for columns and builds a "refined" dataFrame from it.

    """
    # Get logger for this stage
    logger = logging.getLogger("importheus.analyzer")

    # overwritten from child-class
    import_type = "basecase"

    def __init__(self, chtool: CHtools, meta: Instruct):
        """
        Constructor that sets the variables and gets the table information from the import_table_scheme.
        Args:
            chtool: to work with clickhouse (for the logtable entry)
            meta: Instruct element to have context over the import (header field)
        """
        # chtool to work with import-log of the ClickHouse Database
        self.chtool = chtool

        # Instructions from the JSON that are used for this file (the logtable uses it)
        self.meta = meta

        self.returner = DataContainer()

        # column list that gets filled from the official table-scheme
        self.column_reference = import_table_schemes.get(meta.type, []).copy()

        if self.meta.table != logtable_name:
            # append the obligatory setDate Column (except if it is a logtable)
            self.column_reference.append(setDate_scheme)

    def logtable(self, good: int, bad: int) -> None:
        """
        function that analyses the code and logs everything that has a problem. How many Imports, timestamp,
        how many problems, etc.
        merge with execute?

        Args:
            good: number of rows that this file has
            bad: error-rows that this file threw on import
        """

        if not self.chtool.table_exists(logtable_name):
            self.chtool.create_table(logTable)

        # Inserting the data
        # TODO generating correct UUID / Index
        data = [0, datetime.now(), self.meta.filepath, self.meta.type, self.meta.table, good + bad, good, bad]
        self.chtool.insert_row(logtable_name, data)

    def checkRow(self, row: dict[str, str], it: int, headlength: int) -> bool:
        """
        helper function for execute() that analyzes the integrity of one row of data.
        Returns true if all fields are filled and the syntax & data-types are correct
        Returns false if there are empty fields, wrong syntax or wrong data-types
        typeDict that handles the data
        Args:
            row: the singular data row that should be checked for integrity
            it: id of the given row (for error-messages)
            headlength: how long the line should be / how long the header is (1:1 comparison)

        Returns: bool if this row is acceptable or not

        """
        # Check if the length of the row is the same as expected
        # This is independent of optional fields as we require optional fields to be empty, not non-existent.
        # Each row must have the same length
        if headlength != len(row):
            # if not -> instant err
            self.logger.info(f"Row {it-1} has {len(row)} elements but should have {headlength}")
            return False

        dictus: dict[str, str] = {col.name: col.type for col in self.column_reference}
        # Iterate over every item in the row and check if it matches the datatype described in the header
        for i, (name, value) in enumerate(row.items()):
            # Check for empty fields with optional-conditions
            if (value == "" or value == " ") and not self.meta.optional:
                # Field is empty
                self.logger.debug(f"Row {it-1} has an empty value for \"{name}\"")
                if self.column_reference[i].optional:
                    self.logger.info(f"Row {it-1} has an empty value for \"{name}\" but can be optional. Ok.")
                    return True
                # Field must not be optional -> bad row
                return False
            # CHECK THE VALUE FOR PLAUSIBILITY
            # Check if we know this name in the typeDict
            if typeDictPydantic.get(dictus[name]) is not None:
                # Type is known
                if typeDict.validate_value(dictus[name], value):
                    continue # there is no problem, value is as expected -> next field
                else:
                    # We had a problem wit the cast -> this field is not as we want it to be
                    self.logger.error(f"Element {i} of row {it - 1} has an invalid item. "
                                  f"Should be \"{name}\" but looks like \"{value}\"")
                    return False
            else:
                # This type is not in the typeDict -> error (should not be able to happen!)
                self.logger.error(f"The requested type {dictus[name]} is not in the TypeDict. This should "
                                  f"not be able to happen. Add all data-types of import-type {self.meta.type} to the typeDict!")
                return False

        # If no errors occurred -> return true
        return True

    def execute(self, data: DataContainer) -> DataContainer | None:
        """
        Main function from this class. unites all helper functions.

        Args:
            data: the raw DataContainer from the Decoding stage

        Returns: a new DataContainer

        """
        # Check if the import_table_scheme knows this import type
        if import_table_schemes.get(self.meta.type) is None:
            # table not known, stop import of this file
            self.logger.warning(f"Import type {self.meta.type} is not known in the table-dict. "
                             f"Stop import of file {self.meta.filepath}")
            self.meta.bad = True
            return None

        # Check each row of data for syntax problems / empty fields
        def internal_for_yield() -> Generator[dict[str, str]]:
            counter: int = 0  # how many good rows
            total_counter: int = 2  # total row-counter for logging in checkRow
            try:
                for row in data.rawData:
                    if not self.checkRow(row, total_counter, len(self.column_reference)):  # row has a problem
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

class AnalyzerRegistry:
    _registry = {}  # all Sub-Analyzers live here

    @classmethod
    def register(cls, import_type: str, analyzer_class: Analyzer) -> None:
        """
        registers a new decoder class in the decoder-registry
        needs to be done for every new decoder (that implements a new file type)

        Args:
            import_type: string that describes the import-type this Analyzer should be used with
            analyzer_class: class that contains the analyzing functionality for this import-type

        """
        cls._registry[import_type] = analyzer_class

    @classmethod
    def get_decomp(cls, ending):
        """
        factory method that gives you a specific decompressor-Object suitable for a specific file ending
        Args:
            ending: the file ending you want to decode

        Returns: a suitable decoder for this specific file ending

        """
        return cls._registry.get(ending)