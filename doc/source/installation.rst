
Installation
============


Run the installer and follow the configuration instructions below.


Current release version
-----------------------

Get the installer for the current installer at
https://pypi.python.org/pypi/pyreadline/

Follow the instructions for configuration below.

Development version
-------------------

The devopment is hosted at https://github.com/pyreadline/pyreadline

The current trunk version can be cloned with git, :command:`git clone
https://github.com/pyreadline/pyreadline.git`.

Install with the usual :command:`python setup.py install` from the pyreadline
folder.

Follow the instructions for configuration below.



Configuration files
-------------------

There are a few things that are not automatically installed.

* Copy pyreadlineconfig.ini from pyreadline/configuration to your HOME
  directory (usually c:/documents and settings/YOURNAME).
  

* add the code in pyreadline/configuration/startup.py to the startup file
  pointed to by environment variable PYTHONSTARTUP. This file is imported by
  python when started in interactive mode. However when using ipython
  pyreadline is imported by default by ipython.
  


