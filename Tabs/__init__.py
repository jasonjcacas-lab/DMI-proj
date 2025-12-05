# Tabs Package
# Each tool is a subpackage with its own __init__.py that exports build_tab()

# These imports make `from Tabs import Splitter` work as before
# Import with error handling so one failing tab doesn't break others
try:
    from . import Splitter
except Exception:
    Splitter = None

try:
    from . import MvrRunner
except Exception:
    MvrRunner = None

try:
    from . import OllamaTool
except Exception:
    OllamaTool = None

try:
    from . import DealerAppReader
except Exception:
    DealerAppReader = None

__all__ = ['Splitter', 'MvrRunner', 'OllamaTool', 'DealerAppReader']

