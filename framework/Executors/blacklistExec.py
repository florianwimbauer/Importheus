# Executors for import_type=blacklist

# THIS NEEDS TO BE HERE in order for the cold swappable Plug-Ins to work properly
import core.Decompressor
import core.Rowizer
import core.Analyzer

from singleImport import Execution


class BlacklistExec(Execution):
    import_type = "blacklist"

    def single_exec(self) -> None:
        """
        function that orchestrates the pipeline for a blacklist import
        It is advised to use the wrapper methods from the super-class, but it is also possible to use
        own implementation for the pipeline.
        All that mattes is that in the end, the import-stage needs an import-ready dataContainer

        """
        # This Import type makes use of all stages
        handler = self.decode_stage()
        handler = self.rowize_stage(handler, "csv") # TODO dynamic from file ending
        handler = self.analyze_stage(handler)
        handler = self.manipulator_stage(handler)
        self.import_stage(handler)
