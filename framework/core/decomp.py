from abc import ABC, abstractmethod

from util.dataclasses.baseclass import Base
import logging


class Decomp(Base, ABC):
    """
    abstract Decompressor class where every specific File-Decompressor derives from
    """

    logger = logging.getLogger("importheus.decompressor")  # Get logger (is propagated to all deriving classes)

    file_ending = None  # overwritten from subclass

    def __init_subclass__(cls, **kwargs):
        """
        hook that registers subclasses on definition in the DecompRegistry
        Args:
            **kwargs: debug
        """
        ext = cls.file_ending
        if ext:
            DecompRegistry.register(ext, cls)

    @staticmethod
    @abstractmethod
    def showme(file: str):
        """
        abstract function that prints the decoded file content
        to be implemented from every specific File-Decompressor subclass
        Args:
            file: the file to be printed (since it is abstract)

        """
        pass


class DecompRegistry:
    _registry = {}  # all Decoders live here

    @classmethod
    def register(cls, ending: str, decomp_class: Decomp) -> None:
        """
        registers a new decoder class in the decoder-registry
        needs to be done for every new decoder (that implements a new file type)

        Args:
            ending: string that describes the file ending (to parse later)
            decomp_class: class that contains the decoding functionality for this class

        """
        cls._registry[ending] = decomp_class

    @classmethod
    def get_decomp(cls, ending):
        """
        factory method that gives you a specific decompressor-Object suitable for a specific file ending
        Args:
            ending: the file ending you want to decode

        Returns: a suitable decoder for this specific file ending

        """
        return cls._registry.get(ending)
