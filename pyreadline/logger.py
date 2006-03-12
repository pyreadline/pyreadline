# -*- coding: utf-8 -*-
#*****************************************************************************
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************


_logfile=False

def start_log(on,filename):
    global _logfile
    if on=="on":
        _logfile=open(filename,"w")
    else:
        _logfile=False
        
def log(s):
    if _logfile:
        print >>_logfile, s
        _logfile.flush()
