
Known issues
============

 * If you do not want pyreadline at the standard windows prompt. Delete readline.py
   from the install directory. This will not interfere with ipython usage, but you will
   not be able to use the rlcompleter module which requires the readline.py module.

 * Forward incremental search using ctrl-s is flaky because no keyrelease events are generated for ctrl-s
   we use keypress events instead. As a work around ctrl-shift-r is also bound to forward incremental search.

