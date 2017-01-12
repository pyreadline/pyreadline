# -*- coding: utf-8 -*-

#*****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

import os
import sys
import glob
from distutils.core import setup
from platform import system

_S = system()
if 'windows' != _S.lower():
    raise RuntimeError('pyreadline is for Windows only, not {}.'.format(_S))

# BEFORE importing distutils, remove MANIFEST. distutils doesn't properly
# update it when the contents of directories change.
if os.path.exists('MANIFEST'): os.remove('MANIFEST')
#

exec(compile(open('pyreadline/release.py').read(), 'pyreadline/release.py', 'exec'))

try:
    import sphinx
    from sphinx.setup_command import BuildDoc
    cmd_class ={'build_sphinx': BuildDoc}
except ImportError:
    cmd_class = {}

packages = ['pyreadline','pyreadline.clipboard','pyreadline.configuration',
            'pyreadline.console','pyreadline.keysyms','pyreadline.lineeditor',
            'pyreadline.modes','pyreadline.test',
            ]

setup(name=name,
      version          = version,
      description      = description,
      long_description = long_description,
      author           = authors["Jorgen"][0],
      author_email     = authors["Jorgen"][1],
      maintainer       = authors["Adam"][0],
      maintainer_email = authors["Adam"][1],
      license          = license,
      classifiers      = classifiers,
      url              = url,
      download_url     = download_url,
      platforms        = platforms,
      keywords         = keywords,
      py_modules       = ['readline'],
      packages         = packages,
      package_data     = {'pyreadline':['configuration/*']},
      data_files       = [],
      cmdclass = cmd_class
      )

