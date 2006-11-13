import sys

success=False
in_ironpython=sys.version.startswith("IronPython")

if in_ironpython:
    try:
        from ironpython_keysyms import *
        success=True
    except ImportError,x:
        pass
else:
    try:
        from keysyms import *
        success=True
    except ImportError,x:
        pass
    
if not success:
    raise ImportError("Could not import keysym for local pythonversion",x)