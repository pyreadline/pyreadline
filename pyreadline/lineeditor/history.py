# -*- coding: utf-8 -*-
#*****************************************************************************
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************
import re,operator,string,sys,os

#import wordmatcher
#import pyreadline.clipboard as clipboard
if "pyreadline" in sys.modules:
    pyreadline= sys.modules["pyreadline"]
else:
    import pyreadline

import lineobj

import exceptions

class EscapeHistory(exceptions.Exception):
    pass

class LineHistory(object):
    def __init__(self):
        self.history=[]
        self.history_length=100
        self.history_cursor=0
        self.history_filename=os.path.expanduser('~/.history')

    def get_history_length(self):
        return self.history_length

    def set_history_length(self,value):
        self.history_length=value

    def read_history_file(self, filename=None): 
        '''Load a readline history file.'''
        if filename is None:
            filename=self.history_filename
        try:
            for line in open(filename, 'rt'):
                self.add_history(lineobj.ReadLineTextBuffer(line.rstrip()))
        except IOError:
            self.history = []
            self.history_cursor = 0

    def write_history_file(self, filename=None): 
        '''Save a readline history file.'''
        if filename is None:
            filename=self.history_filename
        fp = open(filename, 'wb')
        for line in self.history[-self.history_length:]:
            fp.write(line.get_line_text())
            fp.write('\n')
        fp.close()


    def add_history(self, line):
        '''Append a line to the history buffer, as if it was the last line typed.'''
        if not line.get_line_text():
            pass
        elif len(self.history) > 0 and self.history[-1].get_line_text() == line.get_line_text():
            pass
        else:
            self.history.append(line)
        self.history_cursor = len(self.history)

    def previous_history(self,current): # (C-p)
        '''Move back through the history list, fetching the previous command. '''
        if self.history_cursor==len(self.history):
            self.history.append(current.copy()) #do not use add_history since we do not want to increment cursor
            
        if self.history_cursor > 0:
            self.history_cursor -= 1
            current.set_line(self.history[self.history_cursor].get_line_text())

    def next_history(self,current): # (C-n)
        '''Move forward through the history list, fetching the next command. '''
        if self.history_cursor < len(self.history)-1:
            self.history_cursor += 1
            current.set_line(self.history[self.history_cursor].get_line_text())

    def beginning_of_history(self): # (M-<)
        '''Move to the first line in the history.'''
        self.history_cursor = 0
        if len(self.history) > 0:
            self.l_buffer = self.history[0]

    def end_of_history(self,current): # (M->)
        '''Move to the end of the input history, i.e., the line currently
        being entered.'''
        self.history_cursor=len(self.history)
        current.set_line(self.history[-1].get_line_text())

    def reverse_search_history(self,searchfor):
        res=[(idx,line)  for idx,line in enumerate(self.history[self.history_cursor:0:-1]) if searchfor in line]
        if res:
            self.history_cursor-=res[0][0]
            return res[0][1].get_line_text()
        return ""
        
    def forward_search_history(self,searchfor):
        res=[(idx,line) for idx,line in enumerate(self.history[self.history_cursor:]) if searchfor in line]
        if res:
            self.history_cursor+=res[0][0]
            return res[0][1].get_line_text()
        return ""

    def _non_i_search(self, direction, current):
        c = pyreadline.rl.console
        line = current.get_line_text()
        query = ''
        while 1:
            c.pos(*pyreadline.rl.prompt_end_pos)
            scroll = c.write_scrolling(":%s" % query)
            pyreadline.rl._update_prompt_pos(scroll)
            pyreadline.rl._clear_after()

            event = c.getkeypress()
            if event.keysym == 'BackSpace':
                if len(query) > 0:
                    query = query[:-1]
                else:
                    break
            elif event.char in string.letters + string.digits + string.punctuation + ' ':
                query += event.char
            elif event.keysym == 'Return':
                break
            else:
                pyreadline.rl._bell()

        if query:
            hc = self.history_cursor - 1
            while (direction < 0 and hc >= 0) or (direction > 0 and hc < len(self.history)):
                if self.history[hc].startswith(query) >= 0:
                    current=self.history[hc]
                    self.history_cursor = hc
                    return
                hc += direction
            else:
                pyreadline.rl._bell()


    def non_incremental_reverse_search_history(self,current): # (M-p)
        '''Search backward starting at the current line and moving up
        through the history as necessary using a non-incremental search for
        a string supplied by the user.'''
        self._non_i_search(-1,current)

    def non_incremental_forward_search_history(self,current): # (M-n)
        '''Search forward starting at the current line and moving down
        through the the history as necessary using a non-incremental search
        for a string supplied by the user.'''
        self._non_i_search(1,current)

    def _search(self, direction,partial):
        query = partial[0:partial.point].get_line_text()
        hc = self.history_cursor + direction
        while (direction < 0 and hc >= 0) or (direction > 0 and hc < len(self.history)):
            h = self.history[hc]
            if not query:
                self.history_cursor = hc
                result=lineobj.ReadLineTextBuffer(h,point=partial.point)
                return result
            elif h.get_line_text().startswith(query) and h != partial.get_line_text():
                self.history_cursor = hc
                result=lineobj.ReadLineTextBuffer(h,point=partial.point)
                return result
            hc += direction
        else:
            return lineobj.ReadLineTextBuffer(query,point=partial.point)

    def history_search_forward(self,partial): # ()
        '''Search forward through the history for the string of characters
        between the start of the current line and the point. This is a
        non-incremental search. By default, this command is unbound.'''
        return self._search(1,partial)

    def history_search_backward(self,partial): # ()
        '''Search backward through the history for the string of characters
        between the start of the current line and the point. This is a
        non-incremental search. By default, this command is unbound.'''
        return self._search(-1,partial)
if __name__=="__main__":
    q=LineHistory()
    RL=lineobj.ReadLineTextBuffer
    q.add_history(RL("apan"))
    q.add_history(RL("apbn"))
    q.add_history(RL("apcn"))
    q.add_history(RL("apdn"))
    q.add_history(RL("apen"))
