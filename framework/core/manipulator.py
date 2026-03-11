# My files
from util.dataclasses.baseclass import base
from util.dataclasses.dataContainer import DataContainer

# Libs
import logging


class Manipulator(base):
    """
    
    """
    # Get logger for this stage
    logger = logging.getLogger("importheus.manipulator")

    def execute(self, data: DataContainer) -> DataContainer:
        """
        Main logic of this class

        Args:
            data: the dataContainer from the analyzer

        Returns: I don't know yet

        """
        # TODO Mainpulation logic
        return data
