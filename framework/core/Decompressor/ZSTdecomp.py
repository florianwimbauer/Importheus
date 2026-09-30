# Import of other files
from core.decomp import Decomp
from util.dataclasses.Instruct import Instruct

# Import std Libs
import zstandard as zstd
import io

class ZSTDecoder(Decomp):
    """
    Decompression logic for .zst files, derives from Decompressor Abstract Baseclass

    """

    file_ending = ".zst"  # Defines the file ending for the registry in motherclass

    @staticmethod
    def showme(file) -> None:
        """
        static Method that prints an uncompressed .zst file for debugging

        Args:
            file: path to file that should be decoded and printed
        """
        # Decompression of the .zst file
        print("\n\nThis is the direct read of the file <", file, "> via the showme()-function:\n\n")
        with open(file, "rb") as comp:
            doc = zstd.ZstdDecompressor()
            with doc.stream_reader(comp) as reader:
                dat = reader.read()
                text = dat.decode("utf-8")
                Decomp.logger.debug(text)

    def execute(self, meta: Instruct) -> io.TextIOWrapper | None:
        """
        MAIN FUNCTION of this Class
        implements the abstract Function from Decompressor Base Class
        takes a path to a .zstd file and returns a dataContainer with the content
        prepares a raw .zstd file for further pipeline use as a dataContainer

        Args:
            meta: Instruct object of the .zst file that shall be decoded

        Returns: dataContainer for the given file

        """
        try:
            comp = open(meta.filepath, "rb")  # Decompression of the .zst file
            meta.to_close.append(comp) # add to closing list

            doc = zstd.ZstdDecompressor()

            reader = doc.stream_reader(comp)  # Opening of the stream
            meta.to_close.append(reader) # add to closing list

            text_stream: io.TextIOWrapper = io.TextIOWrapper(reader, encoding="utf-8")

            return text_stream  # return the finished container
        except FileNotFoundError as e:
            self.logger.error(f"File not found!: {e}")
            return None
