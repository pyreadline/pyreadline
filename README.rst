==========
pyreadline
==========


The pyreadline package is a python implementation of GNU readline functionality
it is based on the ctypes based UNC readline package by Gary Bishop. 
It is not complete. It has been tested for use with windows 2000 and windows xp.

Version 2.0 runs on Python 2.6, 2.7, and >3.2 using the same code.

Features:
 *  keyboard text selection and copy/paste
 *  Shift-arrowkeys for text selection
 *  Control-c can be used for copy activate with allow_ctrl_c(True) in config file
 *  Double tapping ctrl-c will raise a KeyboardInterrupt, use ctrl_c_tap_time_interval(x)
    where x is your preferred tap time window, default 0.3 s.
 *  paste pastes first line of content on clipboard. 
 *  ipython_paste, pastes tab-separated data as list of lists or numpy array if all data is numeric
 *  paste_mulitline_code pastes multi line code, removing any empty lines.
 
 
 The latest development version is always available at the pyreadline git 
 repository_.

.. _repository: https://github.com/pyreadline/pyreadline.git
