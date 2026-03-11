from abc import ABC, abstractmethod


class base(ABC):
    """
    baseclass that every class that takes part in the pipeline derives from.
    makes sure that the execute() method exists.
    """

    @abstractmethod
    def execute(self, data):
        pass
