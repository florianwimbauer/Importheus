# Class that will talk to the ClickHouse Database for Importing

# Libs
import logging
from sqlalchemy import create_engine
from itertools import batched
import pandas as pd

# My Files
from util.dataclasses.Instruct import Instruct
from util.dataclasses.baseclass import Base
from util.CHtools import CHtools
from util.dataclasses.dataContainer import DataContainer



class Importer(Base):
    """
    Class that handles the interaction with ClickHouse. New object created for each file that shall be imported
    """

    # Setup SQL Engine
    alchemy_engine = create_engine("clickhouse+http://default:@localhost/default")

    # Setup logger
    logger = logging.getLogger("importheus.importer")

    # Save import instructions from JSON to know to which table to import
    meta: Instruct

    # Save how big a batch should be
    batchsize: int

    def __init__(self, meta: Instruct, batchsize: int, chtool: CHtools):
        """
        Constructor, connects this object with the desired ClickHouse server on localhost
        Connect to the database that is created in the setup script (always the same, only different tables)
        Args:
            meta: metadata of this import
            batchsize: amount of datalines that should be imported in one DataFrame into the database
            chtool: CHtools instance as this stage needs to communicate with the database
        """

        self.meta = meta
        self.batchsize = batchsize
        self.chTool = chtool

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

        if not self.chTool.table_exists(self.meta.table):
            self.logger.critical(f"Table {self.meta.table} did not exist on import but was expected to."
                                 f" Something went wrong internally in the analyzer!")
            return

        # Prepare batch insert - Itertools.batched() functionality
        try:
            for batch in batched(container.rawData, self.batchsize):
                # Iterate over all batches that shall be imported
                to_import = pd.DataFrame(list(batch))
                self.chTool.productiveInsert(self.meta.table, to_import)
        except Exception as e:
            self.logger.critical(f"Pipelined Batch insert went wrong:\n{e}")

            # TODO: WIP - Catch exception when import overflow -> reimport of this data
            self.logger.warning("Merge-Tree Overflow, re-starting this file")
            self.meta.wind_down()
            self.meta.do_re_import = True
