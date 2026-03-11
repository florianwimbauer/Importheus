# Libs
import ijson
import io
from typing import Generator

# My Files
from util.dataclasses.dataContainer import DataContainer
from core.rowize import Rowize


class JSONrowize(Rowize):
    logic_type = "json"

    def transform_lines(self, data: io.TextIOWrapper) -> Generator[dict[str, str]]:
        """
        takes the raw file like pointer from decompression and converts it to suitable
        DataContainer Generator dict-objects
        Also adds the setDate from the Instruct for each row
        Args:
            data: Generator of str-lines

        Returns: insert ready iterator that can be given to the DataContainer for higher stages

        """
        # Transform all the normal data Lines
        for row in ijson.items(data, "item"):
            # row is directly a dict of one JSON line

            # Remove illegal chars in keys (clickhosue has problems with that
            valid_name_row = {k.replace("-", "_"): v for k, v in row.items()}

            # set header from dict if not already happened
            if not self.returner.head:
                self.returner.head = list(valid_name_row.keys())

            # insert the setDate from the Instruct for every line because Tim needs that :)
            valid_name_row.update({"setDate": self.meta.date})

            # Return Data Line
            yield valid_name_row

    def execute(self, file_stream: io.TextIOWrapper) -> DataContainer:
        """
        Transforms the file like object from the decompressor into a DataContainer Generator line by line.
        It expects that the file_stream yields valid .json lines (since this is the json-rowizer)
        Args:
            file_stream: file-like object from the decompressor

        Returns: dataContainer with rawData generator and header-list (when available)

        """
        if file_stream is None:
            # Decompression was unsuccessful, we need to open the file by ourselves
            file_stream = open(self.meta.filepath, "rb")
            self.meta.to_close.append(file_stream) # add to closing list

        # Give the rest of the stream to transform_lines
        self.returner.rawData = self.transform_lines(file_stream)
        return self.returner
