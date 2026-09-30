# *Importheus*
by. F. Wimbauer, 2026, florian.wimbauer@tum.de
Chair of Network Architecture and Services, TUM I8

This tool is intended to simplify the import process of 
internet Measurement data of various types into a ClickHouse
database for analysis purposes.

*Importheus* has the following features:
- decompression of files
- handling of multiple data-types (e.g. json, xml, csv, ...)
- checks each file and each data-line for plausibility and compatibility
- checks for double imports
- logs all it's activity in a log-file as well as in the database
- imports all data that meets the requirements directly into ClickHouse
- modularity: new import-types can easily be added

... providing an all-in-one import solution from raw-data to a deduplicated database that only contains valid lines
that passed the rules of their import-type while logging past import activity.

### 1. Execution

The tool is CLI controlled. Use ```importheus --help``` to see all 
possible flags.
Make sure you're running a suitable ```python``` environment with all necessary dependencies that are stated in 
the ```requirements.txt```.

The tool currently has two modes of operation:
- **import**: imports files that are given in a ```.json``` file (see Control-JSON Syntax)
- **prepare** creates a ```.json``` file for the import mode from a path to a directory or file.

If you want to import data with *Importheus* you need a control ```.json``` that houses all the information 
(e.g. which files should be imported in which table with what configuration, etc.).
If you already have one, you can directly use the *import* mode, if not, you can either write it manually or use the
*prepare* mode. See ```importheus prepare --help```.

### 2. Prepare Mode
To generate an import-ready instruction file, provide a path to the files that should be imported. This can be:
- a directory (the directory will be scraped recursively all files in it and its subfolders will be considered)
- a singular file

The additional mandatory flags are for the other fields and are always set for all elements in this execution.

> Note that if the output ```.json``` already exists, *Importheus* will append data in following executions. 
> This is useful when aiming to generate large files with different import-conditions. Just use multiple executions of 
> the prepare-mode into the same file

### 3. Control-JSON Syntax

The imported files need to be give in a Control JSON as first argument. 
The structure of this file can be taken from the exemplary file ```sampleInstructions/sample.json```.
It contains a list of files while every element has certain properties:
- ```filepath```: (str) path to the file that should be imported
- ```type```: (str) import type for this specific file (needs to be defined in the import_table_schemes
in ```framework/util/Dicts/import_types.py```)
- ```table```: (str) the name of the table in which the lines of the file should be imported into *ClickHouse*. 
If the table does not exist at the time of execution, it will be created
- ```date```: (optional, date:<YYY-MM-DD>). Date of import can be set manually and gets added to every row as a separate data-column.
If no value is given, the current systemdate is used
- ```force```: (optional, boolean) If set to ```True```, the analyzer will ignore a potential double import case and 
import anyway. This is on a file level (for the whole JSON it can be given as ```-f``` flag as argument). If nothing 
is given, it is implicitly set to ```False``` and Importheus will skip the file if it detects a potential double import.

### 4. Logging
Importheus will create a ```importheus.log``` file, where it will log everything it does. It might be useful for 
debugging. Note that the file won't get overwritten on multiple executions but extend.
You can give a custom log-destination with the ```-l``` flag

### 5. Expansions 
Importheus is designed in a way that allows for easy expansion of own import types and new functionality.
It will automatically detect the new modules and use them if necessary. 
Currently, the program supports user-expansion of the following features.

> Please note that all of *Importheus* is generator based. Your extensions must be designed in a way that
> they do not require to load complete files into memory at any given time!

#### 5.1 Decompression Expansions
If your files are compressed in a way that isn't currently supported by *Importheus*, you can write a new Decompressor. 
To do so, create a new ```.py``` file in ```framework/core/Decompressor``` and make sure that your Class derives 
Your implementation must handle the FD in a way that it returns a decompressed stream to the file to the next 
stages.

#### 5.2 Rowizer Types
If your files are stored in a way that isn't currently supported by *Importheus*, you can write a new Rowizer.
To do so, create a new ```.py``` file in ```framework/core/Rowizer``` and make sure that your class derives from
the Rowizer class. 
Your implementation must handle a file stream in a way that it extracts single data lines into a ```dataContainer```.

#### 5.3 Import Types
If you want to add new import-types the program has to be extended in two ways:
- add the table-structure with a arbitrary name to the ```import_table_scheme``` in ```/util/dicts/import_types.py```.
This name can then be used in the type field during execution
- If your import-type introduces *ClickHouse* data-types that are not yet supported by the framework, add them to the 
```typeDictPydantic in``` in ```/util/dicts/typeDict.py```.

### TODO and future work
The project is far from finished. However, I'm no longer at TUM for time being. Here are some of the ideas that are still
unimplemented:
- REST-API control support and Webinterface in combination with automated imports. Possibly a wrapper for this framework
that executes itself regularly (e.g. watching a directory, etc.)
- Manipulator. The currently empty pipeline stage that is ment to repair basic errors of individual fields 
(e.g. ill-formated Timestamps)
- Merge existing import tooling
- JSON Deduplication. When appending to a JSON in prepare mode, it is possible to introduce duplicates. While the
analyzer detects this on a import-file-level (thus not affecting the database)
, it would be useful to eliminate those duplicates directly.
- Debugging & Testing
