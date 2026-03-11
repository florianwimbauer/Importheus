import io
from typing import Generator
from core.rowize import Rowize
import csv
from util.dataclasses.dataContainer import DataContainer


class CSVrowize(Rowize):
    logic_type = "csv"

    def _cut_header(self, stream: io.TextIOWrapper) -> Generator[str]:
        """
        function that cuts headers and empty lines from the content of download data
        tested with abuse_ch_feodo.ip.zst
        every line with # and ' ' will gets cut
        then the first data-line gets returned
        uses iterator

        Args:
            stream: text stream from the zstd Decompressor (Generator)

        Returns: first data-element of the file

        """
        seek_header: bool = True
        for line in stream:
            if not (line.lstrip().startswith("#") or line.strip() == ""):
                if seek_header:
                    # This is the first non commentary line -> save to header
                    header_as_csv = csv.reader([line])  # convert stream to csv
                    self.returner.head = next(header_as_csv)  # save as head in DataContainer
                    seek_header = False
                yield line

    def transform_lines(self, data: Generator[str]) -> Generator[dict[str, str]]:
        """
        takes the raw file like pointer from decompression (after header-comment removal) and converts it to suitable
        DataContainer Generator dict-objects
        Also adds the setDate from the Instruct for each row
        Args:
            data: Generator of str-lines that is freed from commentary-lines and header

        Returns: insert ready iterator that can be given to the DataContainer for higher stages

        """
        # Transform all the normal data Lines
        for row in csv.reader(data):
            # merge the header list and the value list into a dict for the DataContainer
            returner: dict[str, str] = dict(zip(self.returner.head, row))
            # insert the setDate from the Instruct for every line because Tim needs that :)
            returner.update({"setDate": self.meta.date})
            yield returner

    def execute(self, file_stream: io.TextIOWrapper) -> DataContainer:
        """
        Transforms the file like object from the decompressor into a DataContainer Generator line by line.
        It expects that the file_stream yields valid .csv lines (since this is the csv-rowizer)
        Args:
            file_stream: file-like object from the decompressor

        Returns: dataContainer with rawData generator and header-list (when available)

        """
        if file_stream is None:
            # Decompression was unsuccessful, try to open file by ourselves
            file_stream = open(self.meta.filepath, "rb")
            self.meta.to_close.append(file_stream) # add to closing list

        # Delete commentary lines - first non commentary assumed as Column-Header
        first_gen: Generator[str] = self._cut_header(file_stream)

        # Give the rest of the stream to transform_lines
        final_gen2: Generator[dict[str, str]] = self.transform_lines(first_gen)
        self.returner.rawData = final_gen2
        return self.returner
