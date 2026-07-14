# *Importheus* User Manual
by. F. Wimbauer, 2026, florian.wimbauer@tum.de
Bachelor's Thesis for the B.Sc. Informatik at the Technical University of Munich
Chair of Network Architecture and Services, Prof. Dr.-Ing. Georg Carle

This tool is intended to simplify the import process of 
internet Measurement data of various types into a ClickHouse
database for analysis purposes.

### 1. Execution

The tool is CLI controlled. Use ```importheus --help``` to see all 
possible flags.
Make sure you're running a suitable ```python``` environment with all necessary dependencies

### 2. Control-JSON Syntax

The imported files need to be give in a Control JSON as first argument. 
The structure of this file can be taken from the examplary file ```sampleInstructions/sample.json```.
It contains a list of files while every element has certain properties:
- ```filepath```: (str) path to the file that should be imported
- ```type```: (str) import type for this specific file (needs to be defined as an analyzer 
subclass in ```framework/core/Analyter/<type>.py```)
- ```table```: (str) the name of the table in which the lines of the file should be imported in ClickHouse. 
If the table does not exist at the time of execution, it gets created
- ```date```: (optional, date:<YYY-MM-DD>). Date of import can be set maually and gets added to every row as a separate data-column.
If no value is given, the current systemdate is used
- ```force```: (optional, boolean) If set to ```True```, the analyzer will ignore a potential double import case and 
import anway. This is on a file level (for the whole JSON it can be given as ```-f``` flag as argument). If nothing 
is given, it is implicitly set to ```False``` and Importheus will skip the file if it detects a potential double import.

### 3. Logging
Importheus will create a ```importheus.log``` file, where it will log everything it does. It might be useful for 
debugging. Note that the file won't get overwritten on multiple executions but extend.

### 4. Expansions 
Importheus is designed in a way that allows for easy expansion of own import types and new functionality.
Currently, the programm supports expansion of the following features:

> Please note that all of *Importheus* is generator based. Your extensions must be designed in a way that
> they do not require to load complete files into memory at any given time!

#### 4.1 Decompression Expansions
If your files are compressed ina way that isn't curently supported by *Importheus*, you can write a new Decompressor. 
To do so, create a new ```.py``` file in ```framework/core/Decompressor``` and make sure that your Class derives 
from the Decompressor baseclass. It is advised to copy an existing Decompressor and adjust functionality.
The Decompressor-Registry will automatically detect the new module and use it if necessary.
Your implementation must handle the FD in a way that it returns a decompressed stream to the file to the next 
stages.

#### 4.2 Rowizer Types
If your files are stored in a way that isn't currently supported by *Importheus*, you can write a new Rowizer.
To do so, create a new ```.py``` file in ```framework/core/Rowizer``` and make sure that your class derives from
the Rowizer baseclass. It is advised to copy an existing Rowizer and adjust functionality.
The Rowizer-Registry will automatically detect the new module and use it if necessary.
Your implementation must handle a file stream in a way that it extracts single data lines into a ```dataContainer```

### 4.3 Import Types
To implement a new import type (e.g. ```blocklists```, ```apnic-aspop```, ```bgpdump```, etc.) it is
required to create two new files:
-  A new analyzer in ```framework/core/Analyzer```.
It is advised to copy an existing Analyzer and adjust functionality.
The Rowizer-Registry will automatically detect the new module and use it if necessary.
The intended use of the analyzer is to sort out broken lines and check if the data of the file that should be imported is in the
expected format that is needed for the desired table.
    > It is possible to use an empty Analyzer without any functionality, although it is strongly advised not to
    > as this might lead to unexpected import-errors in case of broken lines, etc.

- A new Executor in ```framework/core/Executors```.
It is advised to copy an existing Executor and adjust functionality.
The Executor-Registry will automatically detect the new module and use it if necessary.
The intended use of the Executor is to orchestrate the pipeline for this specific import type. This may be
particularly useful if a certain type does not require all stages. In this case, one could skip e.g. the manipulator,
the decompressor, etc.
