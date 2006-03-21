# -*- coding: utf-8 -*-
#*****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************
import os
import pyreadline.logger as logger
from   pyreadline.logger import log
from   pyreadline.keysyms import key_text_to_keyinfo
import pyreadline.lineeditor.lineobj as lineobj
import pyreadline.lineeditor.history as history

class BaseMode(object):
    mode="base"
    def __init__(self,rlobj):
        self.rlobj=rlobj
        self.exit_dispatch = {}
        self.key_dispatch = {}
        self.startup_hook=None
        self.pre_input_hook=None
        
    def __repr__(self):
        return "<BaseMode>"

    def _gs(x):
        def g(self):
            return getattr(self.rlobj,x)
        def s(self,q):
            setattr(self.rlobj,x,q)
        return g,s
        
    def _g(x):
        def g(self):
            return getattr(self.rlobj,x)
        return g
        
    l_buffer=property(*_gs("l_buffer"))
    next_meta=property(*_gs("next_meta"))
    first_prompt=property(*_gs("first_prompt"))
    prompt=property(*_gs("prompt"))
    console=property(_g("console"))
    insert_text=property(_g("insert_text"))
    _print_prompt=property(_g("_print_prompt"))
    _update_line=property(_g("_update_line"))
    paste_line_buffer=property(_g("paste_line_buffer"))
    add_history=property(_g("add_history"))
    _bell=property(_g("_bell"))
    _clear_after=property(_g("_clear_after"))
    _set_cursor=property(_g("_set_cursor"))
    _print_prompt=property(_g("_print_prompt"))
    _update_prompt_pos=property(_g("_update_prompt_pos"))
    _update_line=property(_g("_update_line"))
    enable_win32_clipboard=property(_g("enable_win32_clipboard"))
    _bell=property(_g("_bell"))
    _history=property(_g("_history"))
    
    def _readline_from_keyboard(self):
        raise NotImplementedError

    def readline(self, prompt=''):
        raise NotImplementedError

    #Create key bindings:

    def _bind_key(self, key, func):
        '''setup the mapping from key to call the function.'''
        keyinfo = key_text_to_keyinfo(key)
#        print key,keyinfo,func.__name__
        self.key_dispatch[keyinfo] = func

    def _bind_exit_key(self, key):
        '''setup the mapping from key to call the function.'''
        keyinfo = key_text_to_keyinfo(key)
        self.exit_dispatch[keyinfo] = None

    def init_editing_mode(self, e): # (C-e)
        '''When in vi command mode, this causes a switch to emacs editing
        mode.'''

        raise NotImplementedError
#completion commands    
    
    def _get_completions(self):
       
        '''Return a list of possible completions for the string ending at the point.

        Also set begidx and endidx in the process.'''
        completions = []
        self.begidx = self.l_buffer.point
        self.endidx = self.l_buffer.point
        buf=self.l_buffer.line_buffer
        if self.completer:
            # get the string to complete
            while self.begidx > 0:
                self.begidx -= 1
                if buf[self.begidx] in self.completer_delims:
                    self.begidx += 1
                    break
            text = ''.join(buf[self.begidx:self.endidx])
            log('complete text="%s"' % text)
            i = 0
            while 1:
                try:
                    r = self.completer(text, i)
                except:
                    break
                i += 1
                if r and r not in completions:
                    completions.append(r)
                else:
                    break
            log('text completions=%s' % completions)
        if not completions:
            # get the filename to complete
            while self.begidx > 0:
                self.begidx -= 1
                if buf[self.begidx] in ' \t\n':
                    self.begidx += 1
                    break
            text = ''.join(buf[self.begidx:self.endidx])
            log('file complete text="%s"' % text)
            completions = glob(os.path.expanduser(text) + '*')
            if self.mark_directories == 'on':
                mc = []
                for f in completions:
                    if os.path.isdir(f):
                        mc.append(f + os.sep)
                    else:
                        mc.append(f)
                completions = mc
            log('fnames=%s' % completions)
        return completions

       
    def _display_completions(self, completions):
        if not completions:
            return
        self.console.write('\n')
        wmax = max(map(len, completions))
        w, h = self.console.size()
        cols = max(1, int((w-1) / (wmax+1)))
        rows = int(math.ceil(float(len(completions)) / cols))
        for row in range(rows):
            s = ''
            for col in range(cols):
                i = col*rows + row
                if i < len(completions):
                    self.console.write(completions[i].ljust(wmax+1))
            self.console.write('\n')
        self._print_prompt()

    def complete(self, e): # (TAB)
        '''Attempt to perform completion on the text before point. The
        actual completion performed is application-specific. The default is
        filename completion.'''
        completions = self._get_completions()
        if completions:
            cprefix = commonprefix(completions)
            rep = [ c for c in cprefix ]
            self.l_buffer[self.begidx:self.endidx] = rep
            self.l_buffer.point += len(rep) - (self.endidx - self.begidx)
            if len(completions) > 1:
                if self.show_all_if_ambiguous == 'on':
                    self._display_completions(completions)
                else:
                    self._bell()
        else:
            self._bell()

    def possible_completions(self, e): # (M-?)
        '''List the possible completions of the text before point. '''
        completions = self._get_completions()
        self._display_completions(completions)

    def insert_completions(self, e): # (M-*)
        '''Insert all completions of the text before point that would have
        been generated by possible-completions.'''
        completions = self._get_completions()
        b = self.begidx
        e = self.endidx
        for comp in completions:
            rep = [ c for c in comp ]
            rep.append(' ')
            self.l_buffer[b:e] = rep
            b += len(rep)
            e = b
        self.line_cursor = b    

    def menu_complete(self, e): # ()
        '''Similar to complete, but replaces the word to be completed with a
        single match from the list of possible completions. Repeated
        execution of menu-complete steps through the list of possible
        completions, inserting each match in turn. At the end of the list of
        completions, the bell is rung (subject to the setting of bell-style)
        and the original text is restored. An argument of n moves n
        positions forward in the list of matches; a negative argument may be
        used to move backward through the list. This command is intended to
        be bound to TAB, but is unbound by default.'''
        pass

    ### Methods below here are bindable emacs functions

    def beginning_of_line(self, e): # (C-a)
        '''Move to the start of the current line. '''
        self.l_buffer.beginning_of_line()

    def end_of_line(self, e): # (C-e)
        '''Move to the end of the line. '''
        self.l_buffer.end_of_line()

    def forward_char(self, e): # (C-f)
        '''Move forward a character. '''
        self.l_buffer.forward_char()

    def backward_char(self, e): # (C-b)
        '''Move back a character. '''
        self.l_buffer.backward_char()

    def forward_word(self, e): # (M-f)
        '''Move forward to the end of the next word. Words are composed of
        letters and digits.'''
        self.l_buffer.forward_word()

    def backward_word(self, e): # (M-b)
        '''Move back to the start of the current or previous word. Words are
        composed of letters and digits.'''
        self.l_buffer.backward_word()

    def clear_screen(self, e): # (C-l)
        '''Clear the screen and redraw the current line, leaving the current
        line at the top of the screen.'''
        self.console.page()

    def redraw_current_line(self, e): # ()
        '''Refresh the current line. By default, this is unbound.'''
        pass

    def accept_line(self, e): # (Newline or Return)
        '''Accept the line regardless of where the cursor is. If this line
        is non-empty, it may be added to the history list for future recall
        with add_history(). If this line is a modified history line, the
        history line is restored to its original state.'''
        return True


    def delete_char(self, e): # (C-d)
        '''Delete the character at point. If point is at the beginning of
        the line, there are no characters in the line, and the last
        character typed was not bound to delete-char, then return EOF.'''
        self.l_buffer.delete_char()

    def backward_delete_char(self, e): # (Rubout)
        '''Delete the character behind the cursor. A numeric argument means
        to kill the characters instead of deleting them.'''
        self.l_buffer.backward_delete_char()

    def self_insert(self, e): # (a, b, A, 1, !, ...)
        '''Insert yourself. '''
        if ord(e.char)!=0: #don't insert null character in buffer, can happen with dead keys.
            self.insert_text(e.char)

