# -*- coding: UTF-8 -*-
# Example snippet to use in a PYTHONSTARTUP file
try:
    import pyreadline,atexit
except ImportError:
    print "Module readline not available."
else:
    #import tab completion functionality
    import rlcompleter
    #activate tab completion
    pyreadline.parse_and_bind("tab: complete")
    pyreadline.rl.read_history_file()
    atexit.register(pyreadline.rl.write_history_file)
    del pyreadline,rlcompleter,atexit
