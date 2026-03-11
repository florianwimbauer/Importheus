# Here lives everything util for reading the CLI and preparing the calls for multiple files

# Libs
import argparse
import json
import yaml
import logging
import sys
import os
from pydantic import ValidationError

# my files
from util.dataclasses.Instruct import Instruct
from extension.samplejson import sample

logger = logging.getLogger("importheus.CLI")


def validate(file_pointer: list[dict]) -> list[Instruct]:
    """
    function that takes the reader of the JSON or YAML file and validates it with pydantic
    Args:
        file_pointer: to the JSON / YAML we want to read

    Returns: a list of valid instructions that can orchestrate the pipeline

    """
    returner: list[Instruct] = []  # prepare the return object
    for i, item in enumerate(file_pointer):
        try:
            instruct = Instruct.model_validate(item)
            returner.append(instruct)
        except ValidationError:
            logger.error(f"Instruction {i} faulty, will be skipped")

    if not returner:
        # If we could not a single usable instruction -> kill
        logger.critical(f"No usable instruction found in Instruction File. Stop.\n"
                        f"JSON should look like this - take Notes:\n{json.dumps(sample, indent=4)}")
        sys.exit(1)
    return returner


def read_input(file) -> list[Instruct]:
    """
    helper function for main that reads given JSON or YAML and gives back data or writes error and sys.exit() when
    File is not there or cannot be read.

    Args:
        file: path to JSON or YAML file from CLI args

    Returns: data from the JSON or YAML file as list of dataclass Instruct

    """
    try:
        if os.path.splitext(file)[1] == ".json":
            # JSON handling
            with open(file, "r") as data:
                json_data = json.load(data)
                return validate(json_data)
        elif os.path.splitext(file)[1] == ".yml" or os.path.splitext(file)[1] == ".yaml":
            # YAML handling
            with open(file, "r") as data:
                yaml_data = yaml.safe_load(data)
                return validate(yaml_data)
        else:
            # Error handling
            logger.critical("Instruction File is not a JSON or a YAML file. Stop")
            sys.exit(1)

    # exception handling
    except FileNotFoundError:
        logger.error("Path to Instruction-JSON does not exists. Stop")
    except json.JSONDecodeError:
        logger.error(f"Opening the instruction JSON failed. Stop")
    sys.exit(1)  # kills the program if there is an error -> without proper JSON, we can't continue


def readCLI() -> argparse.Namespace:
    """
    Function that read all the parameters from the CLI with argparse library.
    definition of the CLI lives here

    Returns: the argparse Namespace to be used in the main function to decide which modules to call
             arguments can be extracted with .<name_of_argument>

    """
    parser = argparse.ArgumentParser(
        prog='importheus',
        description='An efficient Data Importer for Internet Measurement Data into ClickHouse Databases',
        epilog='by F. Wimbauer')
    # All possible arguments that can be displayed
    parser.add_argument('JSON', help="JSON with files to import")
    parser.add_argument('-l', '--logfile', help='File where the logs should be stored', type=str)
    parser.add_argument('-p', '--parallelism', help='How parallel you want your import', default=1, type=int)
    parser.add_argument('-v', '--verbose', action='store_true')
    parser.add_argument('-chu', '--clickhouse_user', help='Clickhouse Username', type=str)
    parser.add_argument('-chp', '--clickhouse_password', help='Clickhouse Password', type=str)
    parser.add_argument('-b', '--batchsize', help='#lines should one CH-Import contain (memory!)',
                        default=1000, type=int)
    parser.add_argument('-f', '--force', help='Force import without Double-Import Check', type=bool)

    args = parser.parse_args()
    return args
