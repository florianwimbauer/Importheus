# Main File of my framework. This will be executed

# Libs
from tqdm import tqdm
from multiprocessing import Pool
from functools import partial

# my files
from core.clickhouse import ChAccess
from singleImport import singleImport
from util.dataclasses.Instruct import Instruct
from util.CLIutil import readCLI, read_input
from util.logsetup import setup_logging

# THIS NEEDS TO BE HERE in order for the cold swappable Plug-Ins to work properly
import Executors


def main() -> None:
    """
    main execution function of the lower framework. Reads directly from the CLI and orchestrates parallelism
    """
    # Get Arguments from CLI
    args = readCLI()

    # Init logging environment
    logger = setup_logging(args.verbose)
    logger.info("Importheus by F. Wimbauer")

    # Create Instruction List from JSON file
    logger.info("Read Instruction file...")
    to_import: list[Instruct] = read_input(args.JSON)

    if args.force:
        # force flag is set -> we force import the whole list
        logger.info("Force Import for all files set")
        for elem in to_import:
            elem.force = True

    # create database-access-object
    logger.info("Connect to Database...")
    database = ChAccess(username=args.clickhouse_user, password=args.clickhouse_password)

    # wrap singleImport to only one input (database is always the same, multiprocessing can only handle on arg)
    single_import_wrapper = partial(singleImport, database=database, batchsize=args.batchsize)

    logger.info("Setup SUCCESS. Starting file processing...")

    if args.parallelism != 1 and len(to_import) > 1:
        # we have conditions to multiprocess
        logger.info("Starting parallel import of multiple files...")
        with Pool(args.parallelism) as p:
            for _ in tqdm(p.imap(single_import_wrapper, to_import), total=len(to_import)):
                pass
        pass
    else:
        # we work sequentially
        logger.info("Start sequential import of file(s)...")
        it: int = 0
        elem: Instruct
        for elem in tqdm(to_import, desc="Process files"):
            singleImport(elem, database, args.batchsize)
            it += 1


# Declares main function from above as main function
if __name__ == "__main__":
    main()
