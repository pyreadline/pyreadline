pyreadline
==========

a python implementation of GNU readline
---------------------------------------



Overview
========

The pyreadline package is a python implementation of GNU readline. At the moment it is only available for the windows platform. The package is based on the readline package by Gary Bishop. The goal is to provide the functionality of the readline package. New features:

    * International characters

    * Cut and paste from clipboard

    paste
      Will paste first line from clipboard (multiple lines doesn't paste well).
    
    ipython_paste
      Smart paste paths, smart paste tab delimited data as list or array.

    multiline_paste
    	Will assume text on clipobard is python code, removes all empty lines. 

    * Bell is disabled by default

dependencies
------------

    * ctypes

Conflicts
---------

Unfortunately the module rlcompleter, the module that provides tab completion, imports readline which means there must be an alias from readline to pyreadline for things to work properly. This means pyreadline install a file under the name readline.py in site-packages containing:

.. literalinclude:: ../../readline.py

