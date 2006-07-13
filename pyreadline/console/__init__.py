import glob

success=False

try:
    from console import *
    success=True
except ImportError:

    try:
        from ironpython_console import *
        success=True
    except ImportError:
        pass


if not success:
    raise ImportError("Could not find a console implementation for your platform")
