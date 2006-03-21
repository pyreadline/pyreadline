# -*- coding: utf-8 -*-
"""Release data for the pyreadline project.

$Id$"""

#*****************************************************************************
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

# Name of the package for release purposes.  This is the name which labels
# the tarballs and RPMs made by distutils, so it's best to lowercase it.
name = 'pyreadline'

# For versions with substrings (like 0.6.16.svn), use an extra . to separate
# the new substring.  We have to avoid using either dashes or underscores,
# because bdist_rpm does not accept dashes (an RPM) convention, and
# bdist_deb does not accept underscores (a Debian convention).

branch = 'refactor'

version = 'refactor'

revision = '$Revision$'

description = "A python implmementation of GNU readline."

long_description = \
"""
The pyreadline package is a python implementation of GNU readline functionality
it is based on the ctypes based UNC readline package by Gary Bishop. 
It is not complete. It has been tested for use with windows 2000 and windows xp.

Features:
 *  Copy and paste using the clipboard
 *  Smart paste for convenient use with ipython. Converting tab separated data 
    to python list or numpy array. Converting file paths to use / and escaping 
    any spaces using \\\\ .
 *  Configuration file
 
 The latest development version is always available at the IPython subversion
 repository_.

.. _repository: http://ipython.scipy.org/svn/ipython/pyreadline/trunk#egg=pyreadline-dev
 """

license = 'BSD'

authors = {'Jorgen' : ('Jorgen Stenarson','jorgen.stenarson@bostream.nu'),
           'Gary':    ('Gary Bishop', ''),         
           'Jack':    ('Jack Trainor', ''),         
           }

url = 'http://projects.scipy.org/ipython/ipython/wiki/PyReadline/Intro'

download_url = ''

platforms = ['Windows XP/2000/NT','Windows 95/98/ME']

keywords = ['readline','pyreadline']

classifiers = ['Development Status :: 4 - Beta',
               'Environment :: Console',
               'Operating System :: Microsoft :: Windows',]
               
               
