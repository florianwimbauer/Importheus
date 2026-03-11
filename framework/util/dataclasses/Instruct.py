from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional


class Instruct(BaseModel):
    """
    dataclass that gets all parameters needed for one execution
    derives from BaseModel for pydantic check / implementation
    """

    # Elements that are derived from the Instruct JSON in CLIUtil
    # those need to be there, otherwise a import is not possible

    filepath: str  # which file shall be imported
    type: str  # which type of import logic to use
    table: str  # in which table shall be imported

    # optional, if not given, we just add the current date
    date: Optional[str] = Field(default_factory=lambda: datetime.today().strftime("%Y-%m-%d")) # to add to each row

    force: bool = False # if set, this file will be imported without check for double imports

    # only for internal logic - not set by JSON
    bad: bool = False  # if set this file will be skipped by further pipeline stages
    # i once again tripped over variables vor all instances - stupid
    to_close: list = Field(default_factory=list) # elements that need to be closed

    def wind_down(self):
        """
        function that closes all the elements in the to_close list
        to be calles at the end of an execution to prevent dangling fd's
        """
        for elem in self.to_close:
            elem.close()