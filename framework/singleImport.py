# File the orchestrates the import of one file
from abc import ABC, abstractmethod
from typing import Any

# My files
from core.clickhouse import ChAccess, ClickHouse
from util.dataclasses.Instruct import Instruct
from core.analyzer import AnalyzeRegistry
from core.decomp import DecompRegistry
from core.manipulator import Manipulator
from core.rowize import RowizerRegistry
from util.dataclasses.dataContainer import DataContainer

# Libs
import logging
import os

# list with handles that need to be closed after each file to prevent leaks and safe space
to_free: list = []

def singleImport(args: Instruct, database: ChAccess, batchsize: int) -> None:
    """
    gets called from the main functions. Chooses the correct Executor and starts its singleExec function
    Needs to be a seperate helper function
    Args:
        args: Instruction element for this file
        database: CHDB where we want to import
        batchsize: for the max. batch import size to CHDB

    Returns: nothing

    """
    logger = logging.getLogger("importheus.preexecutor")
    try:
        right_executor = ExecutorsRegistry.get_executor(import_type=args.type)
        executor = right_executor(database, args, batchsize)
        logger.info(f"--- Start of file {args.filepath} ---")
        executor.single_exec()
        logger.info("--- End of file ---")
    except TypeError:
        logger.error(f"No import procedure for import_type \"{args.type}\" known! Skipping this file!")
        args.bad = True


class Execution(ABC):
    # String for plugin-feature. will be set in subclass
    import_type: str

    # The ClickHouse Pipeline Instance that we will use with the credentials
    clickhouse: ClickHouse

    # The import instructions for this file
    instructions: Instruct

    # the logger for this pipeline stage
    logger = logging.getLogger("importheus.executor")

    def __init__(self, database: ChAccess, args: Instruct, batchsize: int):
        """
        Constructor
        Args:
            database: the ChAccess element to the ClickHouse Database
            args: the Instruct Element for this file
            batchsize: max. size of batch that shall be imported
        """
        self.clickhouse = ClickHouse(database, args, batchsize)
        self.instructions = args

    @abstractmethod
    def single_exec(self) -> None:
        """
        orchestrates the import of one file. optimized for parallel execution in multiple instances (not internally)
        called from main for each file that needs to be imported
        needs full information for the import (gets it from the class instance)
        Implemented in subclasses for each specific import type

        """
        pass

    def __init_subclass__(cls, **kwargs):
        """
        hook that registers subclasses on definition in the ExecutorsRegistry
        Args:
            **kwargs: debug
        """
        ext = cls.import_type
        if ext:
            ExecutorsRegistry.register(ext, cls)

    def decode_stage(self):
        """
        Wrapper method for Decoding stage. Call in subclass-Executors if this import-type needs a decoder
        Gets file from self. instructions
        Returns: decoded stream

        """
        if self.instructions.bad:
            return None

        self.logger.info("Decoding...")
        file_ending = os.path.splitext(self.instructions.filepath)[1]  # extract the file ending from filepath
        try:
            right_decompressor = DecompRegistry.get_decomp(file_ending)  # get decompressor for this file-ending
            decompressor = right_decompressor()  # instantiate the suitable decompressor for the file type
            return decompressor.execute(self.instructions)  # decompressing
        except TypeError:
            self.logger.error(f"File-Ending \"{file_ending}\" can not be decompressed - no suitable decompressor known")
            return None  # go to next execution (skip this file)
            # execution of this file is not stopped here - maybe the rowizer can do something directly
            # if not, he sets it to bad in the instruct -> then will be moved on

    def rowize_stage(self, data, file_ending: str = None) -> DataContainer | None:
        """
        Wrapper method for Rowizing stage. Call in subclass-Executors if this import-type needs a rowizer
        Args:
            data: iterable raw-data Stream (either from decoder or from a file directly)
            file_ending: optional str that describes the format of the decoded file (e.g. "csv")

        Returns: rowized DataContainer

        """
        if self.instructions.bad:
            return None

        self.logger.info("Rowize...")
        try:
            right_rowizer = RowizerRegistry.get_rowizer(file_ending)
            rowizer = right_rowizer(self.instructions)
            return rowizer.execute(data)
        except TypeError:
            self.instructions.bad = True # analyzer won't be able to do something in this case
            return None  # go to next execution (skip this file)

    def analyze_stage(self, data: DataContainer) -> DataContainer | None:
        """
        Wrapper method for Analyzing stage. Call in sublclass-Executor if this import-type needs an analyzer
        Args:
            data: crafted dataContainer (can not take raw file-stream data!)

        Returns: analyzed DataContainer

        """
        if self.instructions.bad:
            return None

        self.logger.info("Analyzing...")
        try:
            right_analyzer = AnalyzeRegistry.get_analyzer(self.instructions.type)
            analyzer = right_analyzer(database=self.clickhouse, meta=self.instructions)
            return analyzer.execute(data)
        except TypeError:
            self.logger.error(
                f"Import Type \"{self.instructions.type}\" can not be analyzed - no suitable analyzer known")
            return data

    def manipulator_stage(self, data: DataContainer) -> DataContainer:
        """
        Wrapper method for Manipulator stage. Call in subclass-Executor if this import-type needs an manipulator
        Args:
            data: dataContainer (can not take raw file-stream data!)

        Returns: manipulated DataContainer ready for import

        """
        if self.instructions.bad:
            return None

        self.logger.info("Manipulating...")
        manipulator = Manipulator()
        return manipulator.execute(data)

    def import_stage(self, data: DataContainer) -> None:
        """
        Wrapper method for Importing stage. Call in subclass-Executor always - otherwise no import!
        Args:
            data: refined ready-to-import dataContainer

        """
        if self.instructions.bad:
            return None

        self.logger.info("Importing to ClickHouse...")
        self.clickhouse.execute(data)
        self.instructions.wind_down() # close all files (executed after the stream is consumed)
        return None


class ExecutorsRegistry:
    _registry = {}  # all Executors live here

    @classmethod
    def register(cls, import_type: str, execution_class: Execution) -> None:
        """
        registers a new executor class in the executors-registry
        needs to be done for every new executor (that implements a new import type)

        Args:
            import_type: string that describes the content type of the file (to parse later)
            execution_class: class that contains the execution-functionality for this class

        """
        cls._registry[import_type] = execution_class

    @classmethod
    def get_executor(cls, import_type):
        """
        factory method that gives you a specific executor-Object suitable for a specific import-type
        Args:
            import_type: the recipy name for which you want import this file

        Returns: a suitable executor for this specific import-type

        """
        return cls._registry.get(import_type)
