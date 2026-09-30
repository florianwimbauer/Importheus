import sys
from pathlib import Path
from typing import List, Generator
import logging
from pydantic import BaseModel


class JSON_Template(BaseModel):
    """
    Pydantic Template for a single JSON Element
    """
    filepath:str
    type:str
    table:str
    date:str

class ImportConfig(BaseModel):
    """
    Pydantic Template for a complete JSON File
    based on a list of single JSON Elements
    """
    version: str = "1.0"
    created_by: str = "Importheus generator mode"
    data: List[JSON_Template]

class JSONGenerator:
    """
    This class handles the control flow of the JSON generator mode of Importheus
    """

    logger = logging.getLogger("importheus-generator")
    deault_outname = "instruct.json"

    def __init__(self, path:str, type:str, table:str, date:str, dest:str):
        self.path:Path = Path(path) # path to the dir / file we work with (potentially recusrive!)
        self.type = type # import type, const for a specific import
        self.table = table # table we want to import, const for a specific import
        self.date = date # date we want to add to each line, const for a specific import
        self.destination = Path(dest) # destination for the JSON-File

    def _yieldFile(self) -> Generator[Path, None, None]:
        """
        Helper function that yields files that lie in the given path
        Returns: Generator to files
        """

        if not self.path.exists():
            self.logger.critical(f"Path {self.path} doesn't exist. Aborting")
            sys.exit(1)

        if self.path.is_file():
            # The given path is only one file -> we only yield this
            yield self.path
            return

        # Get stream that (recursively) gets all files in this dir
        file_stream = self.path.rglob('*')

        for file in file_stream:
            if file.is_file():
                # yield all those files
                yield file.resolve()

    def _getData(self) -> ImportConfig:
        """
        Helper function that wraps all the data into pydantic-elements that are ready for insertion.
        This consumes the file-generator into memory.
        Returns:

        """
        # TODO Batching for 1000
        data: List[JSON_Template] = []
        for file in self._yieldFile():
            data.append(JSON_Template(filepath=str(file), type=self.type, table=self.table, date=self.date))
        return ImportConfig(data=data)

    def mergeJSON(self) -> None:
        """
        Helper Fucntion for generateJSON. Is called when the destiantion file is already existent and not empty.
        Handles merging of the new JSON elements with the old ones
        TODO Deduplication check
        Returns: nothing

        """
        # parse existing JSON file
        old_data_raw = self.destination.read_text(encoding="utf-8")
        existing_config = ImportConfig.model_validate_json(old_data_raw)

        # merge lists (no duplicate filepaths!)
        existing_paths = {item.filepath for item in existing_config.data}

        for new_item in self._getData().data:
            if new_item.filepath not in existing_paths:
                existing_config.data.append(new_item)
                existing_paths.add(new_item.filepath)

        # Write back of merged data into the file
        self.destination.write_text(
            existing_config.model_dump_json(indent=2),
            encoding="utf-8"
        )

    def generateJSON(self) -> None:
        """
        main function that calls all the helpers. Creates the JSON
        Returns:

        """

        mergeNeeded:bool = self.destination.exists() and self.destination.is_file()
        try:
            if self.destination.is_dir():
                # it is a directory -> we append our standard destination
                self.destination = self.destination / self.deault_outname
                mergeNeeded = self.destination.exists()

            self.destination.touch(exist_ok=True)
        except (FileNotFoundError, PermissionError, IsADirectoryError) as e:
            self.logger.error(f"Cannot write to {self.destination} ({e}). Falling back to default.")
            self.destination = Path("./" + self.deault_outname)
            self.destination.touch(exist_ok=True)
            mergeNeeded = False

        if mergeNeeded:
            # We have a file that is already existing and need to merge new data into it.
            self.mergeJSON()
        else:
            # File was not existent before -> we can write directly
            self.destination.write_text(self._getData().model_dump_json(indent=2), encoding="utf-8")