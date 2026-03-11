from typing import Iterator


class DataContainer:
    """
    This is the datatype that makes common ground for the analyzer, manipulator and clickhouse service
    All Decoders produce this file format to be used further down the pipeline.
    Because the nature of the content as well as the datatypes changes throughout the execution of the pipeline.
    """
    # Variables
    rawData: Iterator[dict[str, str]]  # list where the lines of the file lay directly (filled by the decoder)
    head: list[str]  # head ROW that contains the names of the columns (filed by the decoder)
    error: list[dict[str, str]]  # the rows where errors occurred (filled by the analyzer)

    def __init__(self):
        self.head = []
        self.error = []

    def showme_err(self) -> None:
        """
        debug method that nicely prints the error lines fo the DataContainer.
        rawData can't be printed here because it is a Generator
        """
        if len(self.error) != 0:
            print(f"These are the {len(self.error)} broken lines of the Datatainer: \nHead:\n {self.head}, \nLines:")
            for x in self.error:
                print(x)
        else:
            print("Nothing to print here. Container has no errors. RawData can not be displayed here")
