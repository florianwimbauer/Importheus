# File the orchestrates the import of one file
from abc import ABC, abstractmethod

from tablecheck import TableCheck
# My files
from util import CHtools
from core.importer import Importer
from util.dataclasses.Instruct import Instruct
from core.decomp import DecompRegistry
from core.manipulator import Manipulator
from core.rowize import RowizerRegistry
from core.analyzer import Analyzer
from util.dataclasses.dataContainer import DataContainer

# THIS NEEDS TO BE HEERE for the imports & registrys to work properly
import core.Decompressor
import core.Rowizer

# Libs
import logging
import os

# list with handles that need to be closed after each file to prevent leaks and safe space
to_free: list = []

def singleImport(args: Instruct, chtool: CHtools, batchsize: int, retry: int) -> None:
    """
    gets called from the main functions. Chooses the correct Executor and starts its singleExec function
    Needs to be a seperate helper function
    Args:
        args: Instruction element for this file
        chtool: CHDB where we want to import
        batchsize: for the max. batch import size to CHDB
        retry: amount of import-retrys in case of ClickHouse Overflow

    Returns: nothing

    """
    logger = logging.getLogger("importheus.preexecutor")
    logger.info(f"--- Start of file {args.filepath} ---")

    # Test if this file exists / the path is valid
    if not os.path.exists(args.filepath):
        logger.error(f"File {args.filepath} does not exist. Skipping this file")
        args.bad = True
        return

    try:
        right_executor = ExecutorsRegistry.get_executor(import_type=args.type)
        executor = right_executor(chtool, args, batchsize)
        executor.single_exec()

        # There is a Merge-Tree Overflow and we need to reimport this file again
        while args.do_re_import and retry > 0:
            logger.warning("Re-Import-Flag set. Reimporting this file.")
            retry -= 1
            args.do_re_import = False  # will be put to True internally if another overflow occurs
            args.bad = False
            # Start Reimport
            executor.single_exec()
        # Catch cascading problems
        if args.do_re_import:
            logger.error("Re-Import of this file failed 5 times. Aborting")
            args.bad = True

        logger.info("--- End of file ---")
    except TypeError:
        logger.error(f"No import procedure for import_type \"{args.type}\" known! Skipping this file!")
        args.bad = True


class Execution(ABC):
    # String for plugin-feature. will be set in subclass
    import_type: str

    # the logger for this pipeline stage
    logger = logging.getLogger("importheus.executor")

    def __init__(self, chtool: CHtools, args: Instruct, batchsize: int):
        """
        Constructor
        Args:
            chtool: CHtool for accessing the connected ClickHouse database
            args: the Instruct Element for this file
            batchsize: max. size of batch that shall be imported
        """
        self.chtool = chtool # the CHtool Instance that we will use with the credentials
        self.instructions = args # the import instructions for this file
        self.batchsize = batchsize # site of import batch

    @abstractmethod
    def single_exec(self) -> None:
        """
        orchestrates the import of one file. optimized for parallel execution in multiple instances (not internally).
        Called from main for each file that needs to be imported.
        Needs full information for the import (gets it from the class instance)
        Implemented in subclasses for each specific import-type

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
            self.logger.warning(f"File-Ending \"{file_ending}\" can not be decompressed - no suitable decompressor known")
            return None  # go to next execution (skip this file)
            # execution of this file is not stopped here - maybe the rowizer can do something directly
            # if not, he sets it to bad in the Instruct -> then will be moved on

    def rowize_stage(self, data, file_ending: str = "") -> DataContainer | None:
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

    def tablecheck_stage(self, data) -> DataContainer | None:
        """
        Wrapper method for TableCheck stage. Call in subclass-Executors if this import-type needs a tablecheck
        Args:
            data: rowized DataContainer (either manually created or from rowizer)

        Returns: dataConatiner with filled header-fields with the guarantee that there is a suitable table for it
        in the desired database

        """
        if self.instructions.bad:
            return None

        self.logger.info("Check Table...")
        tablechecker = TableCheck(self.chtool, self.instructions)
        return tablechecker.execute(data)

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
        analyzer = Analyzer(chtool=self.chtool, meta=self.instructions)
        return analyzer.execute(data)

    def manipulator_stage(self, data: DataContainer) -> DataContainer | None:
        """
        Wrapper method for Manipulator stage. Call in subclass-Executor if this import-type needs a manipulator
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
        Importer(self.instructions, self.batchsize, self.chtool).execute(data)
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
