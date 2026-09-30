from abc import ABC

from util.dataclasses.Instruct import Instruct
from util.dataclasses.baseclass import Base
import logging

from util.dataclasses.dataContainer import DataContainer


class Rowize(Base, ABC):
    """
    Abstract Mother Class
    Part of the pipeline. Takes file like TextIO Stream from decompression stage and converts it into a
    DataContainer (generator based)
    Newly created for each file that shall be imported.

    """

    logger = logging.getLogger("importheus.rowizer")

    logic_type = None  # overwritten from subclass

    # safety number if somewhere in the file is displayed how many data-lines it contains, overwritten in some subclass
    safety_number: int

    # globally create the DataContainer for this file because we prepare it in multiple functions
    returner: DataContainer

    # metadata for this file from the JSON (for the setDate Column)
    meta: Instruct = None

    def __init__(self, instruction: Instruct):
        self.meta = instruction
        self.returner = DataContainer()
        self.safety_number = -1

    def __init_subclass__(cls, **kwargs):
        """
        hook that registers subclasses on definition in the RowizerRegistry
        Args:
            **kwargs: debug
        """
        ext = cls.logic_type
        if ext:
            RowizerRegistry.register(ext, cls)


class RowizerRegistry:
    _registry = {}  # all Rowizers live here

    @classmethod
    def register(cls, logic_type: str, rowize_class: Rowize) -> None:
        """
        registers a new rowizer class in the decoder-registry
        needs to be done for every new rowize (that implements a new codec type)

        Args:
            logic_type: string that describes the content type of the file (to parse later)
            rowize_class: class that contains the decoding functionality for this class

        """
        cls._registry[logic_type] = rowize_class

    @classmethod
    def get_rowizer(cls, logic_type):
        """
        factory method that gives you a specific rowizer-Object suitable for a specific file codec
        Args:
            logic_type: the content type you want to convert into rows

        Returns: a suitable rowizer for this specific file ending

        """
        return cls._registry.get(logic_type)
