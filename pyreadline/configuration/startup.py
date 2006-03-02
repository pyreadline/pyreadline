# -*- coding: UTF-8 -*-
# Example snippet to use in a PYTHONSTARTUP file
# 

try:
    import pyreadline
except ImportError:
    print "Module pyreadline not available."
else:
    import rlcompleter
    pyreadline.parse_and_bind("tab: complete")


