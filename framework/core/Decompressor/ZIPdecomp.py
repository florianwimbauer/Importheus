# Import of other files
from core.decomp import Decomp
from util.dataclasses.Instruct import Instruct
from util.dataclasses.dataContainer import DataContainer

# Import std Libs
from zipfile import ZipFile
import io


class ZSTDecoder(Decomp):
    """
    Decompression logic for .zst files, derives from Decompressor Abstract Baseclass

    """

    file_ending = ".zip"  # Defines the file ending for the registry in motherclass

    @staticmethod
    def showme(file) -> None:
        """
        static Method that prints an uncompressed .zst file for debugging

        Args:
            file: path to file that should be decoded and printed
        """
        # Decompression of the .zst file
        print("\n\nThis is the direct read of the file <", file, "> via the showme()-function:\n\n")

        with ZipFile(file, 'r') as zfh:
            infolist = zfh.infolist()
            # Use the first file
            with zfh.open(infolist[0], 'r') as f:
                Decomp.logger.debug(f.read())

    def execute(self, meta: Instruct) -> io.TextIOWrapper | None:
        """
        MAIN FUNCTION of this Class
        implements the abstract Function from Decompressor Base Class
        takes a path to a .zip file and returns a dataContainer with the content
        prepares a raw .zip file (first file in zip) for further pipeline use as a dataContainer

        Args:
            meta: Instruct object of the .zip file that shall be decoded (only first file in zip)

        Returns: dataContainer for the given file

        """
        try:
            zfh = ZipFile(meta.filepath, 'r')
            f = zfh.open(zfh.infolist()[0], 'r')
            text_stream: io.TextIOWrapper = io.TextIOWrapper(f, encoding="utf-8")
            meta.to_close.append(f)
            meta.to_close.append(zfh)
            return text_stream  # return the finished container
        except FileNotFoundError as e:
            self.logger.error(f"File not found!: {e}")
            return None