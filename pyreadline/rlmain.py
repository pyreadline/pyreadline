# -*- coding: utf-8 -*-
#*****************************************************************************
#       Copyright (C) 2003-2006 Gary Bishop.
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************
''' an attempt to implement readline for Python in Python using ctypes'''

import string
import math
import sys
from glob import glob
import os
import re
import traceback
import operator
import exceptions

import win32con as c32

import console
import clipboard
from   console import log
from   keysyms import key_text_to_keyinfo

import lineeditor.lineobj as lineobj
import lineeditor.history as history


def quote_char(c):
    if ord(c)>0:
        return c

class ReadlineError(exceptions.Exception):
    pass

def inword(buffer,point):
    return buffer[point:point+1] in [A-Za-z0-9]

class GetSetError(ReadlineError):
    pass

class Readline(object):
    def __init__(self):
        self.startup_hook = None
        self.pre_input_hook = None
        self.completer = None
        self.completer_delims = " \t\n\"\\'`@$><=;|&{("

        self.console = console.Console()
        self.size = self.console.size()
        self.prompt_color = None
        self.command_color = None
        self.key_dispatch = {}
        self.exit_dispatch = {}
        self.previous_func = None
        self.first_prompt = True
        self.next_meta = False # True to force meta on next character
        self.tabstop = 4

        self.emacs_editing_mode(None)
        self.begidx = 0
        self.endidx = 0

        # variables you can control with parse_and_bind
        self.show_all_if_ambiguous = 'off'
        self.mark_directories = 'on'
        self.bell_style = 'none'
        self.mark=-1
        self.read_inputrc()
        log("\n".join(self.rl_settings_to_string()))

        #Paste settings    
        #assumes data on clipboard is path if shorter than 300 characters and doesn't contain \t or \n
        #and replace \ with / for easier use in ipython
        self.enable_ipython_paste_for_paths=True

        #automatically convert tabseparated data to list of lists or array constructors
        self.enable_ipython_paste_list_of_lists=True
        self.enable_win32_clipboard=True

        self.paste_line_buffer=[]

#        self.line_buffer = []
#        self.line_cursor = 0
        self.l_buffer=lineobj.ReadLineTextBuffer("")
        self._history=history.LineHistory()

    def _g(x):
        def g(self):
            raise GetSetError("GET %s"%x)
        def s(self,q):
            raise GetSetError("SET %s"%x)
        return g,s
    line_buffer=property(*_g("line_buffer"))
    line_cursor=property(*_g("line_buffer"))
    undo_stack =property(*_g("undo_stack")) # each entry is a tuple with cursor_position and line_text
    history_length =property(*_g("history_length")) # each entry is a tuple with cursor_position and line_text
    history =property(*_g("history")) # each entry is a tuple with cursor_position and line_text
    history_cursor =property(*_g("history_cursor")) # each entry is a tuple with cursor_position and line_text


    def rl_settings_to_string(self):
        out=["%-20s: %s"%("show all if ambigous",self.show_all_if_ambiguous)]
        out.append("%-20s: %s"%("mark_directories",self.mark_directories))
        out.append("%-20s: %s"%("bell_style",self.bell_style))
        out.append("%-20s: %s"%("mark_directories",self.mark_directories))
        out.append("------------- key bindings ------------")
        out.append("%7s %7s %7s %7s %7s %7s"%("Control","Meta","Shift","Keycode","Character","Function"))
        bindings=[(k[0],k[1],k[2],k[3],repr(chr(k[3])),v.__name__)for k,v in self.key_dispatch.iteritems()]
        bindings.sort()
        for key in bindings:
            out.append("%7s %7s %7s %7d %7s %7s"%(key))
        return out
    
    def _bell(self):
        '''ring the bell if requested.'''
        if self.bell_style == 'none':
            pass
        elif self.bell_style == 'visible':
            raise exceptions.NotImplementedError("Bellstyle visible is not implemented yet.")
        elif self.bell_style == 'audible':
            self.console.bell()
        else:
            raise ReadlineError("Bellstyle %s unknown."%self.bell_style)

    def _clear_after(self):
        c = self.console
        x, y = c.pos()
        w, h = c.size()
        c.rectangle((x, y, w, y+1))
        c.rectangle((0, y+1, w, min(y+3,h)))

    def _set_cursor(self):
        c = self.console
        xc, yc = self.prompt_end_pos
        w, h = c.size()
        xc += self.l_buffer.visible_line_width()
        while(xc > w):
            xc -= w
            yc += 1
        c.pos(xc, yc)

    def _print_prompt(self):
        c = self.console
        log('prompt="%s"' % repr(self.prompt))
        x, y = c.pos()
        n = c.write_scrolling(self.prompt, self.prompt_color)
        self.prompt_begin_pos = (x, y - n)
        self.prompt_end_pos = c.pos()
        self.size = c.size()

    def _update_prompt_pos(self, n):
        if n != 0:
            bx, by = self.prompt_begin_pos
            ex, ey = self.prompt_end_pos
            self.prompt_begin_pos = (bx, by - n)
            self.prompt_end_pos = (ex, ey - n)

    def _update_line(self):
        c=self.console
        c.pos(*self.prompt_end_pos)
        ltext = self.l_buffer.quoted_text()
        n = c.write_scrolling(ltext, self.command_color)
        self._update_prompt_pos(n)
        self._clear_after()
        self._set_cursor()
        

    def _readline_from_keyboard(self):
        c=self.console
        while 1:
            self._update_line()
            event = c.getkeypress()
            if self.next_meta:
                self.next_meta = False
                control, meta, shift, code = event.keyinfo
                event.keyinfo = (control, True, shift, code)

            #Process exit keys. Only exit on empty line
            if event.keyinfo in self.exit_dispatch:
                if lineobj.EndOfLine(self.l_buffer) == 0:
                    raise EOFError

            dispatch_func = self.key_dispatch.get(event.keyinfo,self.self_insert)
            log("readline from keyboard:%s"%(event.keyinfo,))
            r = None
            if dispatch_func:
                r = dispatch_func(event)
                self.l_buffer.push_undo()

            self.previous_func = dispatch_func
            if r:
                self._update_line()
                break

    def readline(self, prompt=''):
        '''Try to act like GNU readline.'''
        # handle startup_hook
        if self.first_prompt:
            self.first_prompt = False
            if self.startup_hook:
                try:
                    self.startup_hook()
                except:
                    print 'startup hook failed'
                    traceback.print_exc()

        c = self.console
        self.l_buffer.reset_line()
        self.prompt = prompt
        self._print_prompt()

        if self.pre_input_hook:
            try:
                self.pre_input_hook()
            except:
                print 'pre_input_hook failed'
                traceback.print_exc()
                self.pre_input_hook = None

        log("in readline: %s"%self.paste_line_buffer)
        if len(self.paste_line_buffer)>0:
            self.l_buffer=lineobj.ReadlineTextBuffer(self.paste_line_buffer[0])
            self._update_line()
            self.paste_line_buffer=self.paste_line_buffer[1:]
            c.write('\r\n')
        else:
            self._readline_from_keyboard()
            c.write('\r\n')

        self.add_history(self.l_buffer.copy())

        log('returning(%s)' % self.l_buffer.get_line_text())
        return self.l_buffer.get_line_text() + '\n'

    def parse_and_bind(self, string):
        '''Parse and execute single line of a readline init file.'''
        try:
            log('parse_and_bind("%s")' % string)
            if string.startswith('#'):
                return
            if string.startswith('set'):
                m = re.compile(r'set\s+([-a-zA-Z0-9]+)\s+(.+)\s*$').match(string)
                if m:
                    var_name = m.group(1)
                    val = m.group(2)
                    try:
                        setattr(self, var_name.replace('-','_'), val)
                    except AttributeError:
                        log('unknown var="%s" val="%s"' % (var_name, val))
                else:
                    log('bad set "%s"' % string)
                return
            m = re.compile(r'\s*(.+)\s*:\s*([-a-zA-Z]+)\s*$').match(string)
            if m:
                key = m.group(1)
                func_name = m.group(2)
                py_name = func_name.replace('-', '_')
                try:
                    func = getattr(self, py_name)
                except AttributeError:
                    log('unknown func key="%s" func="%s"' % (key, func_name))
                    print 'unknown function to bind: "%s"' % func_name
                self._bind_key(key, func)
        except:
            log('error')
            traceback.print_exc()
            raise

    def get_line_buffer(self):
        '''Return the current contents of the line buffer.'''
        return self.l_buffer.get_line_text()

    def insert_text(self, string):
        '''Insert text into the command line.'''
        self.l_buffer.insert_text(string)
        
    def read_init_file(self, filename=None): 
        '''Parse a readline initialization file. The default filename is the last filename used.'''
        log('read_init_file("%s")' % filename)

    def read_history_file(self, filename=os.path.expanduser('~/.history')): 
        '''Load a readline history file. The default filename is ~/.history.'''
        self._history.read_history_file(filename)

    def write_history_file(self, filename=os.path.expanduser('~/.history')): 
        '''Save a readline history file. The default filename is ~/.history.'''
        self._history.write_history_file(filename)

    def get_history_length(self, ):
        '''Return the desired length of the history file.

        Negative values imply unlimited history file size.'''
        return self._history.get_history_length()

    def set_history_length(self, length): 
        '''Set the number of lines to save in the history file.

        write_history_file() uses this value to truncate the history file
        when saving. Negative values imply unlimited history file size.
        '''
        self._history.set_history_length(length)

    def set_startup_hook(self, function=None): 
        '''Set or remove the startup_hook function.

        If function is specified, it will be used as the new startup_hook
        function; if omitted or None, any hook function already installed is
        removed. The startup_hook function is called with no arguments just
        before readline prints the first prompt.

        '''
        self.startup_hook = function

    def set_pre_input_hook(self, function=None):
        '''Set or remove the pre_input_hook function.

        If function is specified, it will be used as the new pre_input_hook
        function; if omitted or None, any hook function already installed is
        removed. The pre_input_hook function is called with no arguments
        after the first prompt has been printed and just before readline
        starts reading input characters.

        '''
        self.pre_input_hook = function

    def set_completer(self, function=None): 
        '''Set or remove the completer function.

        If function is specified, it will be used as the new completer
        function; if omitted or None, any completer function already
        installed is removed. The completer function is called as
        function(text, state), for state in 0, 1, 2, ..., until it returns a
        non-string value. It should return the next possible completion
        starting with text.
        '''
        log('set_completer')
        self.completer = function

    def get_completer(self): 
        '''Get the completer function. 
        ''' 

        log('get_completer') 
        return self.completer 

    def get_begidx(self):
        '''Get the beginning index of the readline tab-completion scope.'''
        return self.begidx

    def get_endidx(self):
        '''Get the ending index of the readline tab-completion scope.'''
        return self.endidx

    def set_completer_delims(self, string):
        '''Set the readline word delimiters for tab-completion.'''
        self.completer_delims = string

    def get_completer_delims(self):
        '''Get the readline word delimiters for tab-completion.'''
        return self.completer_delims

    def add_history(self, line):
        '''Append a line to the history buffer, as if it was the last line typed.'''
        self._history.add_history(line)

    ### Methods below here are bindable functions

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
#########  History commands
    def previous_history(self, e): # (C-p)
        '''Move back through the history list, fetching the previous command. '''
        self._history.previous_history(self.l_buffer)

    def next_history(self, e): # (C-n)
        '''Move forward through the history list, fetching the next command. '''
        self._history.next_history(self.l_buffer)

    def beginning_of_history(self, e): # (M-<)
        '''Move to the first line in the history.'''
        self._history.beginning_of_history()

    def end_of_history(self, e): # (M->)
        '''Move to the end of the input history, i.e., the line currently
        being entered.'''
        self._history.end_of_history(self.l_buffer)

    def _i_search(self, searchfun, direction, init_event):
        c = self.console
        line = self.get_line_buffer()
        query = ''
        hc_start = self._history.history_cursor #+ direction
        while 1:
            x, y = self.prompt_end_pos
            c.pos(0, y)
            if direction < 0:
                prompt = 'reverse-i-search'
            else:
                prompt = 'forward-i-search'

            scroll = c.write_scrolling("%s`%s': %s" % (prompt, query, line))
            self._update_prompt_pos(scroll)
            self._clear_after()

            event = c.getkeypress()
            if event.keysym == 'BackSpace':
                if len(query) > 0:
                    query = query[:-1]
                    self._history.history_cursor = hc_start
                else:
                    self._bell()
            elif event.char in string.letters + string.digits + string.punctuation + ' ':
                self._history.history_cursor = hc_start
                query += event.char
            elif event.keyinfo == init_event.keyinfo:
                self._history.history_cursor += direction
                line=searchfun(query)                
                pass
            else:
                if event.keysym != 'Return':
                    self._bell()
                break
            line=searchfun(query)

        px, py = self.prompt_begin_pos
        c.pos(0, py)
        self.l_buffer.set_line(line)
        self._print_prompt()
        self._history.history_cursor=len(self._history.history)

    def reverse_search_history(self, e): # (C-r)
        '''Search backward starting at the current line and moving up
        through the history as necessary. This is an incremental search.'''
#        print "HEJ"
#        self.console.bell()
        self._i_search(self._history.reverse_search_history, -1, e)

    def forward_search_history(self, e): # (C-s)
        '''Search forward starting at the current line and moving down
        through the the history as necessary. This is an incremental search.'''
#        print "HEJ"
#        self.console.bell()
        self._i_search(self._history.forward_search_history, 1, e)


    def non_incremental_reverse_search_history(self, e): # (M-p)
        '''Search backward starting at the current line and moving up
        through the history as necessary using a non-incremental search for
        a string supplied by the user.'''
        self._history.non_incremental_reverse_search_history(self.l_buffer)

    def non_incremental_forward_search_history(self, e): # (M-n)
        '''Search forward starting at the current line and moving down
        through the the history as necessary using a non-incremental search
        for a string supplied by the user.'''
        self._history.non_incremental_reverse_search_history(self.l_buffer)

    def history_search_forward(self, e): # ()
        '''Search forward through the history for the string of characters
        between the start of the current line and the point. This is a
        non-incremental search. By default, this command is unbound.'''
        self.l_buffer=self._history.history_search_forward(self.l_buffer)

    def history_search_backward(self, e): # ()
        '''Search backward through the history for the string of characters
        between the start of the current line and the point. This is a
        non-incremental search. By default, this command is unbound.'''
        self.l_buffer=self._history.history_search_backward(self.l_buffer)

    def yank_nth_arg(self, e): # (M-C-y)
        '''Insert the first argument to the previous command (usually the
        second word on the previous line) at point. With an argument n,
        insert the nth word from the previous command (the words in the
        previous command begin with word 0). A negative argument inserts the
        nth word from the end of the previous command.'''
        pass

    def yank_last_arg(self, e): # (M-. or M-_)
        '''Insert last argument to the previous command (the last word of
        the previous history entry). With an argument, behave exactly like
        yank-nth-arg. Successive calls to yank-last-arg move back through
        the history list, inserting the last argument of each line in turn.'''
        pass

    def delete_char(self, e): # (C-d)
        '''Delete the character at point. If point is at the beginning of
        the line, there are no characters in the line, and the last
        character typed was not bound to delete-char, then return EOF.'''
        self.l_buffer.delete_char()

    def backward_delete_char(self, e): # (Rubout)
        '''Delete the character behind the cursor. A numeric argument means
        to kill the characters instead of deleting them.'''
        self.l_buffer.backward_delete_char()

    def forward_backward_delete_char(self, e): # ()
        '''Delete the character under the cursor, unless the cursor is at
        the end of the line, in which case the character behind the cursor
        is deleted. By default, this is not bound to a key.'''
        pass

    def quoted_insert(self, e): # (C-q or C-v)
        '''Add the next character typed to the line verbatim. This is how to
        insert key sequences like C-q, for example.'''
        e = self.console.getkeypress()
        self.insert_text(e.char)

    def tab_insert(self, e): # (M-TAB)
        '''Insert a tab character. '''
        ws = ' ' * (self.tabstop - (self.line_cursor%self.tabstop))
        self.insert_text(ws)

    def self_insert(self, e): # (a, b, A, 1, !, ...)
        '''Insert yourself. '''
        if ord(e.char)!=0: #don't insert null character in buffer, can happen with dead keys.
            self.insert_text(e.char)

    def transpose_chars(self, e): # (C-t)
        '''Drag the character before the cursor forward over the character
        at the cursor, moving the cursor forward as well. If the insertion
        point is at the end of the line, then this transposes the last two
        characters of the line. Negative arguments have no effect.'''
        self.l_buffer.transpose_chars()

    def transpose_words(self, e): # (M-t)
        '''Drag the word before point past the word after point, moving
        point past that word as well. If the insertion point is at the end
        of the line, this transposes the last two words on the line.'''
        self.l_buffer.transpose_words()

    def upcase_word(self, e): # (M-u)
        '''Uppercase the current (or following) word. With a negative
        argument, uppercase the previous word, but do not move the cursor.'''
        self.l_buffer.upcase_word()

    def downcase_word(self, e): # (M-l)
        '''Lowercase the current (or following) word. With a negative
        argument, lowercase the previous word, but do not move the cursor.'''
        self.l_buffer.downcase_word()

    def capitalize_word(self, e): # (M-c)
        '''Capitalize the current (or following) word. With a negative
        argument, capitalize the previous word, but do not move the cursor.'''
        self.l_buffer.capitalize_word()

    def overwrite_mode(self, e): # ()
        '''Toggle overwrite mode. With an explicit positive numeric
        argument, switches to overwrite mode. With an explicit non-positive
        numeric argument, switches to insert mode. This command affects only
        emacs mode; vi mode does overwrite differently. Each call to
        readline() starts in insert mode. In overwrite mode, characters
        bound to self-insert replace the text at point rather than pushing
        the text to the right. Characters bound to backward-delete-char
        replace the character before point with a space.'''
        pass
        
    def kill_line(self, e): # (C-k)
        '''Kill the text from point to the end of the line. '''
        self.l_buffer.kill_line()
        
    def backward_kill_line(self, e): # (C-x Rubout)
        '''Kill backward to the beginning of the line. '''
        self.l_buffer.backward_kill_line()

    def unix_line_discard(self, e): # (C-u)
        '''Kill backward from the cursor to the beginning of the current line. '''
        # how is this different from backward_kill_line?
        self.l_buffer.unix_line_discard()

    def kill_whole_line(self, e): # ()
        '''Kill all characters on the current line, no matter where point
        is. By default, this is unbound.'''
        self.l_buffer.kill_whole_line()

    def kill_word(self, e): # (M-d)
        '''Kill from point to the end of the current word, or if between
        words, to the end of the next word. Word boundaries are the same as
        forward-word.'''
        self.l_buffer.kill_word()

    def backward_kill_word(self, e): # (M-DEL)
        '''Kill the word behind point. Word boundaries are the same as
        backward-word. '''
        self.l_buffer.backward_kill_word()

    def unix_word_rubout(self, e): # (C-w)
        '''Kill the word behind point, using white space as a word
        boundary. The killed text is saved on the kill-ring.'''
        self.l_buffer.unix_word_rubout()

    def delete_horizontal_space(self, e): # ()
        '''Delete all spaces and tabs around point. By default, this is unbound. '''
        pass

    def kill_region(self, e): # ()
        '''Kill the text in the current region. By default, this command is unbound. '''
        pass

    def copy_region_as_kill(self, e): # ()
        '''Copy the text in the region to the kill buffer, so it can be
        yanked right away. By default, this command is unbound.'''
        pass

    def copy_region_to_clipboard(self, e): # ()
        '''Copy the text in the region to the windows clipboard.'''
        if self.enable_win32_clipboard:
                mark=min(self.l_buffer.mark,len(self.l_buffer.line_buffer))
                cursor=min(self.l_buffer.point,len(self.l_buffer.line_buffer))
                if self.l_buffer.mark==-1:
                        return
                begin=min(cursor,mark)
                end=max(cursor,mark)
                toclipboard="".join(self.l_buffer.line_buffer[begin:end])
                clipboard.SetClipboardText(str(toclipboard))

    def copy_backward_word(self, e): # ()
        '''Copy the word before point to the kill buffer. The word
        boundaries are the same as backward-word. By default, this command
        is unbound.'''
        pass

    def copy_forward_word(self, e): # ()
        '''Copy the word following point to the kill buffer. The word
        boundaries are the same as forward-word. By default, this command is
        unbound.'''
        pass

    def paste(self,e):
        '''Paste windows clipboard'''
        if self.enable_win32_clipboard:
                txt=clipboard.get_clipboard_text_and_convert(False)
                self.insert_text(txt)

    def paste_mulitline_code(self,e):
        '''Paste windows clipboard'''
        reg=re.compile("\r?\n")
        if self.enable_win32_clipboard:
                txt=clipboard.get_clipboard_text_and_convert(False)
                t=reg.split(txt)
                t=[row for row in t if row.strip()!=""] #remove empty lines
                if t!=[""]:
                    self.insert_text(t[0])
                    self.add_history(self.l_buffer.copy())
                    self.paste_line_buffer=t[1:]
                    log("multi: %s"%self.paste_line_buffer)
                    return True
                else:
                    return False
        
    def ipython_paste(self,e):
        '''Paste windows clipboard. If enable_ipython_paste_list_of_lists is 
        True then try to convert tabseparated data to repr of list of lists or 
        repr of array'''
        if self.enable_win32_clipboard:
                txt=clipboard.get_clipboard_text_and_convert(
                                                self.enable_ipython_paste_list_of_lists)
                if self.enable_ipython_paste_for_paths:
                        if len(txt)<300 and ("\t" not in txt) and ("\n" not in txt):
                                txt=txt.replace("\\","/").replace(" ",r"\ ")
                self.insert_text(txt)

    def yank(self, e): # (C-y)
        '''Yank the top of the kill ring into the buffer at point. '''
        pass

    def yank_pop(self, e): # (M-y)
        '''Rotate the kill-ring, and yank the new top. You can only do this
        if the prior command is yank or yank-pop.'''
        pass


    def digit_argument(self, e): # (M-0, M-1, ... M--)
        '''Add this digit to the argument already accumulating, or start a
        new argument. M-- starts a negative argument.'''
        pass

    def universal_argument(self, e): # ()
        '''This is another way to specify an argument. If this command is
        followed by one or more digits, optionally with a leading minus
        sign, those digits define the argument. If the command is followed
        by digits, executing universal-argument again ends the numeric
        argument, but is otherwise ignored. As a special case, if this
        command is immediately followed by a character that is neither a
        digit or minus sign, the argument count for the next command is
        multiplied by four. The argument count is initially one, so
        executing this function the first time makes the argument count
        four, a second time makes the argument count sixteen, and so on. By
        default, this is not bound to a key.'''
        pass


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

    def delete_char_or_list(self, e): # ()
        '''Deletes the character under the cursor if not at the beginning or
        end of the line (like delete-char). If at the end of the line,
        behaves identically to possible-completions. This command is unbound
        by default.'''
        pass

    def start_kbd_macro(self, e): # (C-x ()
        '''Begin saving the characters typed into the current keyboard macro. '''
        pass

    def end_kbd_macro(self, e): # (C-x ))
        '''Stop saving the characters typed into the current keyboard macro
        and save the definition.'''
        pass

    def call_last_kbd_macro(self, e): # (C-x e)
        '''Re-execute the last keyboard macro defined, by making the
        characters in the macro appear as if typed at the keyboard.'''
        pass

    def re_read_init_file(self, e): # (C-x C-r)
        '''Read in the contents of the inputrc file, and incorporate any
        bindings or variable assignments found there.'''
        pass

    def abort(self, e): # (C-g)
        '''Abort the current editing command and ring the terminals bell
             (subject to the setting of bell-style).'''
        self._bell()

    def do_uppercase_version(self, e): # (M-a, M-b, M-x, ...)
        '''If the metafied character x is lowercase, run the command that is
        bound to the corresponding uppercase character.'''
        pass

    def prefix_meta(self, e): # (ESC)
        '''Metafy the next character typed. This is for keyboards without a
        meta key. Typing ESC f is equivalent to typing M-f. '''
        self.next_meta = True

    def undo(self, e): # (C-_ or C-x C-u)
        '''Incremental undo, separately remembered for each line.'''
        self.l_buffer.pop_undo()

    def revert_line(self, e): # (M-r)
        '''Undo all changes made to this line. This is like executing the
        undo command enough times to get back to the beginning.'''
        pass

    def tilde_expand(self, e): # (M-~)
        '''Perform tilde expansion on the current word.'''
        pass

    def set_mark(self, e): # (C-@)
        '''Set the mark to the point. If a numeric argument is supplied, the
        mark is set to that position.'''
        self.l_buffer.set_mark()

    def exchange_point_and_mark(self, e): # (C-x C-x)
        '''Swap the point with the mark. The current cursor position is set
        to the saved position, and the old cursor position is saved as the
        mark.'''
        pass

    def character_search(self, e): # (C-])
        '''A character is read and point is moved to the next occurrence of
        that character. A negative count searches for previous occurrences.'''
        pass

    def character_search_backward(self, e): # (M-C-])
        '''A character is read and point is moved to the previous occurrence
        of that character. A negative count searches for subsequent
        occurrences.'''
        pass

    def insert_comment(self, e): # (M-#)
        '''Without a numeric argument, the value of the comment-begin
        variable is inserted at the beginning of the current line. If a
        numeric argument is supplied, this command acts as a toggle: if the
        characters at the beginning of the line do not match the value of
        comment-begin, the value is inserted, otherwise the characters in
        comment-begin are deleted from the beginning of the line. In either
        case, the line is accepted as if a newline had been typed.'''
        pass

    def dump_functions(self, e): # ()
        '''Print all of the functions and their key bindings to the Readline
        output stream. If a numeric argument is supplied, the output is
        formatted in such a way that it can be made part of an inputrc
        file. This command is unbound by default.'''
        pass

    def dump_variables(self, e): # ()
        '''Print all of the settable variables and their values to the
        Readline output stream. If a numeric argument is supplied, the
        output is formatted in such a way that it can be made part of an
        inputrc file. This command is unbound by default.'''
        pass

    def dump_macros(self, e): # ()
        '''Print all of the Readline key sequences bound to macros and the
        strings they output. If a numeric argument is supplied, the output
        is formatted in such a way that it can be made part of an inputrc
        file. This command is unbound by default.'''
        pass

    def _bind_key(self, key, func):
        '''setup the mapping from key to call the function.'''
        keyinfo = key_text_to_keyinfo(key)
#        print key,keyinfo,func.__name__
        self.key_dispatch[keyinfo] = func

    def _bind_exit_key(self, key):
        '''setup the mapping from key to call the function.'''
        keyinfo = key_text_to_keyinfo(key)
        self.exit_dispatch[keyinfo] = None

    def emacs_editing_mode(self, e): # (C-e)
        '''When in vi command mode, this causes a switch to emacs editing
        mode.'''

        self._bind_exit_key('Control-d')
        self._bind_exit_key('Control-z')

        # I often accidentally hold the shift or control while typing space
        self._bind_key('Shift-space',       self.self_insert)
        self._bind_key('Control-space',     self.self_insert)
        self._bind_key('Return',            self.accept_line)
        self._bind_key('Left',              self.backward_char)
        self._bind_key('Control-b',         self.backward_char)
        self._bind_key('Right',             self.forward_char)
        self._bind_key('Control-f',         self.forward_char)
        self._bind_key('BackSpace',         self.backward_delete_char)
        self._bind_key('Home',              self.beginning_of_line)
        self._bind_key('End',               self.end_of_line)
        self._bind_key('Delete',            self.delete_char)
        self._bind_key('Control-d',         self.delete_char)
        self._bind_key('Clear',             self.clear_screen)
        self._bind_key('Alt-f',             self.forward_word)
        self._bind_key('Alt-b',             self.backward_word)
        self._bind_key('Control-l',         self.clear_screen)
        self._bind_key('Control-p',         self.previous_history)
        self._bind_key('Up',                self.history_search_backward)
        self._bind_key('Control-n',         self.next_history)
        self._bind_key('Down',              self.history_search_forward)
        self._bind_key('Control-a',         self.beginning_of_line)
        self._bind_key('Control-e',         self.end_of_line)
        self._bind_key('Alt-<',             self.beginning_of_history)
        self._bind_key('Alt->',             self.end_of_history)
        self._bind_key('Control-r',         self.reverse_search_history)
        self._bind_key('Control-s',         self.forward_search_history)
        self._bind_key('Alt-p',             self.non_incremental_reverse_search_history)
        self._bind_key('Alt-n',             self.non_incremental_forward_search_history)
        self._bind_key('Control-z',         self.undo)
        self._bind_key('Control-_',         self.undo)
        self._bind_key('Escape',            self.prefix_meta)
        self._bind_key('Meta-d',            self.kill_word)
        self._bind_key('Meta-Delete',       self.backward_kill_word)
        self._bind_key('Control-w',         self.unix_word_rubout)
        #self._bind_key('Control-Shift-v',   self.quoted_insert)
        self._bind_key('Control-v',         self.paste)
        self._bind_key('Alt-v',             self.ipython_paste)
        self._bind_key('Control-y',         self.paste)
        self._bind_key('Control-k',         self.kill_line)
        self._bind_key('Control-m',         self.set_mark)
        self._bind_key('Control-q',         self.copy_region_to_clipboard)
#        self._bind_key('Control-shift-k',  self.kill_whole_line)
        self._bind_key('Control-Shift-v',   self.paste_mulitline_code)


    def vi_editing_mode(self, e): # (M-C-j)
        '''When in emacs editing mode, this causes a switch to vi editing
        mode.'''
        pass

    def read_inputrc(self,inputrcpath=os.path.expanduser("~/pyreadlineconfig.ini")):
        def bind_key(key,name):
            if hasattr(self,name):
                self._bind_key(key,getattr(self,name))
        def un_bind_key(key):
            keyinfo = key_text_to_keyinfo(key)
            if keyinfo in self.key_dispatch:
                del self.key_dispatch[keyinfo]

        def bind_exit_key(key):
            self._bind_exit_key(key)
        def un_bind_exit_key(key):
            keyinfo = key_text_to_keyinfo(key)
            if keyinfo in self.exit_dispatch:
                del self.exit_dispatch[keyinfo]

        def setbellstyle(mode):
            self.bell_style=mode
        def setbellstyle(mode):
            self.bell_style=mode
        def show_all_if_ambiguous(mode):
            self.show_all_if_ambiguous=mode
        def mark_directories(mode):
            self.mark_directories=mode
        def completer_delims(mode):
            self.completer_delims=mode
        loc={"bind_key":bind_key,
             "bind_exit_key":bind_exit_key,
             "un_bind_key":un_bind_key,
             "un_bind_exit_key":un_bind_exit_key,
             "bell_style":setbellstyle,
             "mark_directories":mark_directories,
             "show_all_if_ambiguous":show_all_if_ambiguous,
             "completer_delims":completer_delims,}
        if os.path.isfile(inputrcpath): 
            try:
                execfile(inputrcpath,loc,loc)
            except:
                #Or should we force output otherwise python -v is necessary?
                #print >>sys.stderr, "Error reading .pyinputrc" 
                raise ReadlineError("Error reading .pyinputrc")



def CTRL(c):
    '''make a control character'''
    assert '@' <= c <= '_'
    return chr(ord(c) - ord('@'))

# make it case insensitive
def commonprefix(m):
    "Given a list of pathnames, returns the longest common leading component"
    if not m: return ''
    prefix = m[0]
    for item in m:
        for i in range(len(prefix)):
            if prefix[:i+1].lower() != item[:i+1].lower():
                prefix = prefix[:i]
                if i == 0: return ''
                break
    return prefix

# create a Readline object to contain the state
rl = Readline()

def GetOutputFile():
    '''Return the console object used by readline so that it can be used for printing in color.'''
    return rl.console

# make these available so this looks like the python readline module
parse_and_bind = rl.parse_and_bind
get_line_buffer = rl.get_line_buffer
insert_text = rl.insert_text
read_init_file = rl.read_init_file
read_history_file = rl.read_history_file
write_history_file = rl.write_history_file
get_history_length = rl.get_history_length
set_history_length = rl.set_history_length
set_startup_hook = rl.set_startup_hook
set_pre_input_hook = rl.set_pre_input_hook
set_completer = rl.set_completer
get_completer = rl.get_completer
get_begidx = rl.get_begidx
get_endidx = rl.get_endidx
set_completer_delims = rl.set_completer_delims
get_completer_delims = rl.get_completer_delims
add_history = rl.add_history

if __name__ == '__main__':
    res = [ rl.readline('In[%d] ' % i) for i in range(3) ]
    print res
else:
    #import wingdbstub
    console.install_readline(rl.readline)
    pass
