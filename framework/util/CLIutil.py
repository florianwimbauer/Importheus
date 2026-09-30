# Here lives everything util for reading the CLI and preparing the calls for multiple files

# Libs
import argparse
import json
from xmlrpc.client import DateTime

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

    parser.add_argument('-l', '--logfile', help='File where the logs should be stored', type=str)
    parser.add_argument('-v', '--verbose', action='store_true')

    subparsers = parser.add_subparsers(
        dest='mode',
        required=True,
        help='Importheus Usermodes'
    )

    """
    Import-Mode
    This mode is the standard mode that triggers the import-pipeline of the tool.
    Needs a preproduced JSON file as instructions to know which files to import
    """

    parser_import = subparsers.add_parser(
        name='import',
        help='Imports from JSON Configuration'
    )

    # All possible arguments that the import-mode may use
    parser_import.add_argument('JSON', help="JSON with files to import")
    parser_import.add_argument('-p', '--parallelism', help='How parallel you want your import', default=1, type=int)
    parser_import.add_argument('-chu', '--clickhouse_user', help='Clickhouse Username', type=str)
    parser_import.add_argument('-chp', '--clickhouse_password', help='Clickhouse Password', type=str)
    parser_import.add_argument('-b', '--batchsize', help='#lines should one CH-Import contain (memory!)',
                        default=1000, type=int)
    parser_import.add_argument('-f', '--force', help='Force import without Double-Import Check', type=bool)
    parser_import.add_argument('-chd', '--clickhouse_database',
                        help='Specific Database inside the ClickHouse Server', type=str, default='default')
    parser_import.add_argument('-r', '--retry', help='Amount of retries to import this file after CH-overflow. '
                                              'Default 5 times',type=int, default=5)
    parser_import.add_argument('-o', '--optional',
                               help='All fields are optional, Analyzer ignores empty values', type=bool, default=False)

    """
    Preparation Mode
    This mode is able to recusrively generate a Instruction-JSON for the Import-Mode by giving it a filepath and
    the other parameters needed for the JSON
    """

    parser_prepare = subparsers.add_parser(
        name='prepare',
        help='Generates JSON for import-mode from filepath'
    )

    # All possible arguments that the preparation-mode may use
    parser_prepare.add_argument('path', help="path to import-file(s) / directory ")
    parser_prepare.add_argument('type', help="Import-type of this directory or file")
    parser_prepare.add_argument('table', help="Destination table of this directory or file")
    parser_prepare.add_argument('date', help="Import Date YYYY-MM-DD", type=str, nargs='?',
                               default=None)
    parser_prepare.add_argument('output', help='desired output JSON', type=str, nargs='?'
                                , default='./instruct.json')
    parser_prepare.add_argument('-b', help="Batchsize for JSON elements per file", type=int, default=1000)

    return parser.parse_args()
