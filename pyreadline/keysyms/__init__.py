import glob

success=False
try:
    from keysyms import *
    success=True
except ImportError,x:
    pass

try:
    from ironpython_keysyms import *
    success=True
except ImportError,x:
    pass
    
if not success:
    raise ImportError("Could not import keysym for local pythonversion",x)