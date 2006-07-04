from common import *
success=False
try:
    from clipboard import GetClipboardText,SetClipboardText
    success=True
except ImportError:
    pass
    
try:
    from ironpython_clipboard import GetClipboardText,SetClipboardText
    success=True
except ImportError:
    pass
    
    
    
    
