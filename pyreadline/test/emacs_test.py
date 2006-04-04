# -*- coding: utf-8 -*-
#*****************************************************************************
#       Copyright (C) 2006  Michael Graz. <mgraz@plan10.com>
#       Copyright (C) 2006  Michael Graz. <mgraz@plan10.com>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

import sys, unittest
import pdb
sys.path.append ('../..')
from pyreadline.modes.emacs import *
from pyreadline import keysyms
from pyreadline.lineeditor import lineobj

from common import *
#----------------------------------------------------------------------

class EmacsModeTest (EmacsMode):
    def __init__ (self):
        EmacsMode.__init__ (self, MockReadline())
        self.mock_console = MockConsole ()
        self.init_editing_mode (None)
        self.lst_completions = []
        self.completer = self.mock_completer
        self.completer_delims = ' '
        self.tabstop = 4

    def get_mock_console (self):
        return self.mock_console
    console = property (get_mock_console)

    def _set_line (self, text):
        self.l_buffer.set_line (text)

    def get_line (self):
        return self.l_buffer.get_line_text ()
    line = property (get_line)

    def get_line_cursor (self):
        return self.l_buffer.point
    line_cursor = property (get_line_cursor)

    def input (self, keytext):
        if keytext[0] == '"' and keytext[-1] == '"':
            lst_key = ['"%s"' % c for c in keytext[1:-1]]
        else:
            lst_key = [keytext]
        for key in lst_key:
            keyinfo, event = keytext_to_keyinfo_and_event (key)
            dispatch_func = self.key_dispatch.get(keyinfo,self.self_insert)
            dispatch_func (event)
            self.previous_func=dispatch_func
    def accept_line (self, e):
        if EmacsMode.accept_line (self, e):
            # simulate return
            # self.add_history (self.line)
            self.l_buffer.reset_line ()

    def mock_completer (self, text, state):
        return self.lst_completions [state]

#----------------------------------------------------------------------

class Tests (unittest.TestCase):

    def test_keyinfo (self):
        keyinfo, event = keytext_to_keyinfo_and_event ('"d"')
        self.assertEqual ('d', event.char)
        keyinfo, event = keytext_to_keyinfo_and_event ('"D"')
        self.assertEqual ('D', event.char)
        keyinfo, event = keytext_to_keyinfo_and_event ('"$"')
        self.assertEqual ('$', event.char)
        keyinfo, event = keytext_to_keyinfo_and_event ('Escape')
        self.assertEqual ('\x1b', event.char)


    def test_history_1 (self):
        r = EmacsModeTest ()
        r.add_history ('aa')
        r.add_history ('bbb')
        self.assertEqual (r.line, '')
        r.input ('Up')
        self.assertEqual (r.line, 'bbb')
        self.assertEqual (r.line_cursor, 3)
        r.input ('Up')
        self.assertEqual (r.line, 'aa')
        self.assertEqual (r.line_cursor, 2)
        r.input ('Up')
        self.assertEqual (r.line, 'aa')
        self.assertEqual (r.line_cursor, 2)
        r.input ('Down')
        self.assertEqual (r.line, 'bbb')
        self.assertEqual (r.line_cursor, 3)
        r.input ('Down')
        self.assertEqual (r.line, '')
        self.assertEqual (r.line_cursor, 0)

    def test_history_2 (self):
        r = EmacsModeTest ()
        r.add_history ('aaaa')
        r.add_history ('aaba')
        r.add_history ('aaca')
        r.add_history ('akca')
        r.add_history ('bbb')
        r.add_history ('ako')
        self.assertEqual (r.line, '')
        r.input ('"a"')
        r.input ('Up')
        self.assertEqual (r.line, 'ako')
        self.assertEqual (r.line_cursor, 1)
        r.input ('Up')
        self.assertEqual (r.line, 'akca')
        self.assertEqual (r.line_cursor, 1)
        r.input ('Up')
        self.assertEqual (r.line, 'aaca')
        self.assertEqual (r.line_cursor, 1)
        r.input ('Up')
        self.assertEqual (r.line, 'aaba')
        self.assertEqual (r.line_cursor, 1)
        r.input ('Up')
        self.assertEqual (r.line, 'aaaa')
        self.assertEqual (r.line_cursor, 1)
        r.input ('Right')
        self.assertEqual (r.line, 'aaaa')
        self.assertEqual (r.line_cursor, 2)
        r.input ('Down')
        self.assertEqual (r.line, 'aaba')
        self.assertEqual (r.line_cursor, 2)
        r.input ('Down')
        self.assertEqual (r.line, 'aaca')
        self.assertEqual (r.line_cursor, 2)
        r.input ('Down')
        self.assertEqual (r.line, 'aaca')
        self.assertEqual (r.line_cursor, 2)
        r.input ('Left')
        r.input ('Left')
        r.input ('Down')
        r.input ('Down')
        self.assertEqual (r.line, 'bbb')
        self.assertEqual (r.line_cursor, 3)
        r.input ('Left')
        self.assertEqual (r.line, 'bbb')
        self.assertEqual (r.line_cursor, 2)
        r.input ('Down')
        self.assertEqual (r.line, 'bbb')
        self.assertEqual (r.line_cursor, 2)
        r.input ('Up')
        self.assertEqual (r.line, 'bbb')
        self.assertEqual (r.line_cursor, 2)

#----------------------------------------------------------------------
# utility functions

#----------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()

