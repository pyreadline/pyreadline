Pyreadline
==========

A python implementation of GNU readline
---------------------------------------

Pyreadline is a package inspired by GNU readline which aims to improve the 
command line editing experience. In most UNIX based pythons GNU readline is 
available and used by python but on windows this is not the case. A readline
like python library can also be useful when implementing commandline like 
interfaces in GUIs. The use of pyreadline for anything but the windows 
console is still under development.


Dependencies
------------

    * ctypes


Conflicts
---------

Unfortunately the module rlcompleter, the module that provides tab completion, imports readline which means there must be an alias from readline to pyreadline for things to work properly. This means pyreadline install a file under the name readline.py in site-packages containing:

.. literalinclude:: ../../readline.py

