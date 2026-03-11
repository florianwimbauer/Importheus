import importlib
import pkgutil
import sys


def load_all_executors():
    """
    imports all files in this directory so that new importers can be added on the fly

    """
    package = sys.modules[__name__]
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        importlib.import_module(f"{package.__name__}.{module_name}")


load_all_executors()  # call on import of this directory