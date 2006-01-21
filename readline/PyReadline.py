''' an attempt to implement readline for Python in Python using ctypes'''

import string
import math
import sys
from glob import glob
import os
import re
import traceback
import operator

import win32con as c32

import Console
from Console import log
from keysyms import key_text_to_keyinfo,printable_chars_in_codepage

def quote_char(c):
    if c in printable_chars_in_codepage:
        return c
    elif ' ' <= c <= '~':
        return c
    else:
        return repr(c)[1:-1]

class Readline:
    def __init__(self):
        self.startup_hook = None
        self.pre_input_hook = None
        self.completer = None
        self.completer_delims = " \t\n\"\\'`@$><=;|&{("
        self.history_length = -1
        self.history = [] # strings for previous commands
        self.history_cursor = 0
        self.undo_stack = [] # each entry is a tuple with cursor_position and line_text
        self.line_buffer = []
        self.line_cursor = 0
        self.console = Console.Console()
        self.size = self.console.size()
        self.prompt_color = None
        self.command_color = None
        self.key_dispatch = {}
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

    def _bell(self):
        '''ring the bell if requested.'''
        if self.bell_style == 'none':
            self.console.bell()

    def _quoted_text(self):
        quoted = [ quote_char(c) for c in self.line_buffer ]
        self.line_char_width = [ len(c) for c in quoted ]
        return ''.join(quoted)

    def _line_text(self):
        return ''.join(self.line_buffer)

    def _set_line(self, text, cursor=None):
        self.line_buffer = [ c for c in str(text) ]
        if cursor is None:
            self.line_cursor = len(self.line_buffer)
        else:
            self.line_cursor = cursor

    def _reset_line(self):
        self.line_buffer = []
        self.line_cursor = 0
        self.undo_stack = []

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
        xc += reduce(operator.add, self.line_char_width[0:self.line_cursor], 0)
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
        self._reset_line()
        self.prompt = prompt
        self._print_prompt()

        if self.pre_input_hook:
            try:
                self.pre_input_hook()
            except:
                print 'pre_input_hook failed'
                traceback.print_exc()
                self.pre_input_hook = None

        while 1:
            c.pos(*self.prompt_end_pos)
            ltext = self._quoted_text()
            n = c.write_scrolling(ltext, self.command_color)
            self._update_prompt_pos(n)
            self._clear_after()
            self._set_cursor()

            event = c.getkeypress()
            if self.next_meta:
                self.next_meta = False
                control, meta, shift, code = event.keyinfo
                event.keyinfo = (control, True, shift, code)

            try:
                dispatch_func = self.key_dispatch[event.keyinfo]
            except KeyError:
                c.bell()
                continue
            r = None
            if dispatch_func:
                r = dispatch_func(event)
                ltext = self._line_text()
                if self.undo_stack and ltext == self.undo_stack[-1][1]:
                    self.undo_stack[-1][0] = self.line_cursor
                else:
                    self.undo_stack.append([self.line_cursor, ltext])

            self.previous_func = dispatch_func
            if r:
                break

        c.write('\r\n')

        rtext = self._line_text()
        self.add_history(rtext)

        log('returning(%s)' % rtext)
        return rtext + '\n'

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
            log('before')
            m = re.compile(r'\s*(.+)\s*:\s*([-a-zA-Z]+)\s*$').match(string)
            log('here')
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
        log('return')

    def get_line_buffer(self):
        '''Return the current contents of the line buffer.'''
        return "".join(self.line_buffer)

    def insert_text(self, string):
        '''Insert text into the command line.'''
        for c in string:
            self.line_buffer.insert(self.line_cursor, c)
            self.line_cursor += 1

    def read_init_file(self, filename=None): 
        '''Parse a readline initialization file. The default filename is the last filename used.'''
        log('read_init_file("%s")' % filename)

    def read_history_file(self, filename=os.path.expanduser('~/.history')): 
        '''Load a readline history file. The default filename is ~/.history.'''
        try:
            for line in open(filename, 'rt'):
                self.add_history(line.rstrip())
        except IOError:
            self.history = []
            self.history_cursor = 0
            raise IOError

    def write_history_file(self, filename=os.path.expanduser('~/.history')): 
        '''Save a readline history file. The default filename is ~/.history.'''
        fp = open(filename, 'wb')
        for line in self.history:
            fp.write(line)
            fp.write('\n')
        fp.close()

    def get_history_length(self, ):
        '''Return the desired length of the history file.

        Negative values imply unlimited history file size.'''
        return self.history_length

    def set_history_length(self, length): 
        '''Set the number of lines to save in the history file.

        write_history_file() uses this value to truncate the history file
        when saving. Negative values imply unlimited history file size.
        '''
        self.history_length = length

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
        if not line:
            pass
        elif len(self.history) > 0 and self.history[-1] == line:
            pass
        else:
            self.history.append(line)
            if self.history_length > 0 and len(self.history) > self.history_length:
                self.history = self.history[-self.history_length:]
        self.history_cursor = len(self.history)

    ### Methods below here are bindable functions

    def beginning_of_line(self, e): # (C-a)
        '''Move to the start of the current line. '''
        self.line_cursor = 0

    def end_of_line(self, e): # (C-e)
        '''Move to the end of the line. '''
        self.line_cursor = len(self.line_buffer)

    def forward_char(self, e): # (C-f)
        '''Move forward a character. '''
        if self.line_cursor < len(self.line_buffer):
            self.line_cursor += 1
        else:
            self._bell()

    def backward_char(self, e): # (C-b)
        '''Move back a character. '''
        if self.line_cursor > 0:
            self.line_cursor -= 1
        else:
            self._bell()

    def forward_word(self, e): # (M-f)
        '''Move forward to the end of the next word. Words are composed of
        letters and digits.'''
        L = len(self.line_buffer)
        while self.line_cursor < L:
            self.line_cursor += 1
            if self.line_cursor == L:
                break
            if self.line_buffer[self.line_cursor] not in string.letters + string.digits:
                break

    def backward_word(self, e): # (M-b)
        '''Move back to the start of the current or previous word. Words are
        composed of letters and digits.'''
        while self.line_cursor > 0:
            self.line_cursor -= 1
            if self.line_buffer[self.line_cursor] not in string.letters + string.digits:
                break

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

    def previous_history(self, e): # (C-p)
        '''Move back through the history list, fetching the previous command. '''
        if self.history_cursor > 0:
            self.history_cursor -= 1
            line = self.history[self.history_cursor]
            self._set_line(line)
        else:
            self._bell()

    def next_history(self, e): # (C-n)
        '''Move forward through the history list, fetching the next command. '''
        if self.history_cursor < len(self.history) - 1:
            self.history_cursor += 1
            line = self.history[self.history_cursor]
            self._set_line(line)
        elif self.undo_stack:
            cursor, text = self.undo_stack[-1]
            self._set_line(text, cursor)
        else:
            self._bell()

    def beginning_of_history(self, e): # (M-<)
        '''Move to the first line in the history.'''
        self.history_cursor = 0
        if len(self.history) > 0:
            self._set_line(self.history[0])
        else:
            self._bell()

    def end_of_history(self, e): # (M->)
        '''Move to the end of the input history, i.e., the line currently
        being entered.'''
        if self.undo_stack:
            cursor, text = self.undo_stack[-1]
            self._set_line(text, cursor)
        else:
            self._bell()

    def _i_search(self, direction, init_event):
        c = self.console
        line = self._line_text()
        query = ''
        hc_start = self.history_cursor + direction
        hc = hc_start
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
                    hc = hc_start
                else:
                    c.bell()
            elif event.char in string.letters + string.digits + string.punctuation + ' ':
                query += event.char
                hc = hc_start
            elif event.keyinfo == init_event.keyinfo:
                hc += direction
            else:
                if event.keysym != 'Return':
                    c.bell()
                break

            while (direction < 0 and hc >= 0) or (direction > 0 and hc < len(self.history)):
                if self.history[hc].find(query) >= 0:
                    break
                hc += direction
            else:
                c.bell()
                continue
            line = self.history[hc]

        px, py = self.prompt_begin_pos
        c.pos(0, py)
        self._set_line(line)
        self._print_prompt()

    def reverse_search_history(self, e): # (C-r)
        '''Search backward starting at the current line and moving up
        through the history as necessary. This is an incremental search.'''
        self._i_search(-1, e)

    def forward_search_history(self, e): # (C-s)
        '''Search forward starting at the current line and moving down
        through the the history as necessary. This is an incremental search.'''
        self._i_search(1, e)

    def _non_i_search(self, direction):
        c = self.console
        line = self._line_text()
        query = ''
        while 1:
            c.pos(*self.prompt_end_pos)
            scroll = c.write_scrolling(":%s" % query)
            self._update_prompt_pos(scroll)
            self._clear_after()

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
                c.bell()

        if query:
            hc = self.history_cursor - 1
            while (direction < 0 and hc >= 0) or (direction > 0 and hc < len(self.history)):
                if self.history[hc].find(query) >= 0:
                    self._set_line(self.history[hc])
                    self.history_cursor = hc
                    return
                hc += direction
            else:
                c.bell()


    def non_incremental_reverse_search_history(self, e): # (M-p)
        '''Search backward starting at the current line and moving up
        through the history as necessary using a non-incremental search for
        a string supplied by the user.'''
        self._non_i_search(-1)

    def non_incremental_forward_search_history(self, e): # (M-n)
        '''Search forward starting at the current line and moving down
        through the the history as necessary using a non-incremental search
        for a string supplied by the user.'''
        self._non_i_search(1)

    def _search(self, direction):
        c = self.console

        if (self.previous_func != self.history_search_forward and
                self.previous_func != self.history_search_backward):
            self.query = ''.join(self.line_buffer[0:self.line_cursor])
        hc = self.history_cursor + direction
        while (direction < 0 and hc >= 0) or (direction > 0 and hc < len(self.history)):
            h = self.history[hc]
            if not self.query:
                self._set_line(h)
                self.history_cursor = hc
                return
            elif h.startswith(self.query) and h != self._line_text:
                self._set_line(h, len(self.query))
                self.history_cursor = hc
                return
            hc += direction
        else:
            self._set_line(self.query)
            c.bell()

    def history_search_forward(self, e): # ()
        '''Search forward through the history for the string of characters
        between the start of the current line and the point. This is a
        non-incremental search. By default, this command is unbound.'''
        self._search(1)

    def history_search_backward(self, e): # ()
        '''Search backward through the history for the string of characters
        between the start of the current line and the point. This is a
        non-incremental search. By default, this command is unbound.'''
        self._search(-1)

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
        if len(self.line_buffer) == 0:
            if self.previous_func != self.delete_char:
                raise EOFError
            self._bell()
        if self.line_cursor < len(self.line_buffer):
            del self.line_buffer[self.line_cursor]
        else:
            self._bell()

    def backward_delete_char(self, e): # (Rubout)
        '''Delete the character behind the cursor. A numeric argument means
        to kill the characters instead of deleting them.'''
        if self.line_cursor > 0:
            del self.line_buffer[self.line_cursor-1]
            self.line_cursor -= 1

    def forward_backward_delete_char(self, e): # ()
        '''Delete the character under the cursor, unless the cursor is at
        the end of the line, in which case the character behind the cursor
        is deleted. By default, this is not bound to a key.'''
        pass

    def quoted_insert(self, e): # (C-q or C-v)
        '''Add the next character typed to the line verbatim. This is how to
        insert key sequences like C-q, for example.'''
        e = self.console.getkeypress()
        self.line_buffer.insert(self.line_cursor, e.char)
        self.line_cursor += 1

    def tab_insert(self, e): # (M-TAB)
        '''Insert a tab character. '''
        ws = ' ' * (self.tabstop - (self.line_cursor%self.tabstop))
        self.insert_text(ws)

    def self_insert(self, e): # (a, b, A, 1, !, ...)
        '''Insert yourself. '''
        if ord(e.char)!=0: #don't insert null character in buffer, can happen with dead keys.
            self.line_buffer.insert(self.line_cursor, e.char)
            self.line_cursor += 1

    def transpose_chars(self, e): # (C-t)
        '''Drag the character before the cursor forward over the character
        at the cursor, moving the cursor forward as well. If the insertion
        point is at the end of the line, then this transposes the last two
        characters of the line. Negative arguments have no effect.'''
        pass

    def transpose_words(self, e): # (M-t)
        '''Drag the word before point past the word after point, moving
        point past that word as well. If the insertion point is at the end
        of the line, this transposes the last two words on the line.'''
        pass

    def upcase_word(self, e): # (M-u)
        '''Uppercase the current (or following) word. With a negative
        argument, uppercase the previous word, but do not move the cursor.'''
        pass

    def downcase_word(self, e): # (M-l)
        '''Lowercase the current (or following) word. With a negative
        argument, lowercase the previous word, but do not move the cursor.'''
        pass

    def capitalize_word(self, e): # (M-c)
        '''Capitalize the current (or following) word. With a negative
        argument, capitalize the previous word, but do not move the cursor.'''
        pass

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
        self.line_buffer[self.line_cursor:] = []

    def backward_kill_line(self, e): # (C-x Rubout)
        '''Kill backward to the beginning of the line. '''
        self.line_buffer[:self.line_cursor] = []
        self.line_cursor = 0

    def unix_line_discard(self, e): # (C-u)
        '''Kill backward from the cursor to the beginning of the current line. '''
        # how is this different from backward_kill_line?
        self.line_buffer[:self.line_cursor] = []
        self.line_cursor = 0

    def kill_whole_line(self, e): # ()
        '''Kill all characters on the current line, no matter where point
        is. By default, this is unbound.'''
        pass

    def kill_word(self, e): # (M-d)
        '''Kill from point to the end of the current word, or if between
        words, to the end of the next word. Word boundaries are the same as
        forward-word.'''
        begin = self.line_cursor
        self.forward_word(e)
        self.line_buffer[begin:self.line_cursor] = []
        self.line_cursor = begin

    def backward_kill_word(self, e): # (M-DEL)
        '''Kill the word behind point. Word boundaries are the same as
        backward-word. '''
        begin = self.line_cursor
        self.backward_word(e)
        self.line_buffer[self.line_cursor:begin] = []

    def unix_word_rubout(self, e): # (C-w)
        '''Kill the word behind point, using white space as a word
        boundary. The killed text is saved on the kill-ring.'''
        begin = self.line_cursor
        while self.line_cursor > 0:
            self.line_cursor -= 1
            if self.line_buffer[self.line_cursor] == ' ':
                break
        self.line_buffer[self.line_cursor:begin] = []

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
        self.begidx = self.line_cursor
        self.endidx = self.line_cursor
        if self.completer:
            # get the string to complete
            while self.begidx > 0:
                self.begidx -= 1
                if self.line_buffer[self.begidx] in self.completer_delims:
                    self.begidx += 1
                    break
            text = ''.join(self.line_buffer[self.begidx:self.endidx])
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
                if self.line_buffer[self.begidx] in ' \t\n':
                    self.begidx += 1
                    break
            text = ''.join(self.line_buffer[self.begidx:self.endidx])
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
            self.line_buffer[self.begidx:self.endidx] = rep
            self.line_cursor += len(rep) - (self.endidx - self.begidx)
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
            self.line_buffer[b:e] = rep
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
        log(self.undo_stack)
        if len(self.undo_stack) >= 2:
            self.undo_stack.pop()
            cursor, text = self.undo_stack.pop()
        else:
            cursor = 0
            text = ''
            self.undo_stack = []
        self._set_line(text, cursor)

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
        pass

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
        self.key_dispatch[keyinfo] = func

    def emacs_editing_mode(self, e): # (C-e)
        '''When in vi command mode, this causes a switch to emacs editing
        mode.'''
        #insert printable chars available from codepage
        for char in printable_chars_in_codepage:
                self._bind_key(char, self.self_insert)

        # make ' ' to ~ self insert
        for c in range(ord(' '), 127):
            self._bind_key('"%s"' % chr(c), self.self_insert)
        # I often accidentally hold the shift or control while typing space
        self._bind_key('Shift-space', self.self_insert)
        self._bind_key('Control-space', self.self_insert)
        self._bind_key('Return', self.accept_line)
        self._bind_key('Left', self.backward_char)
        self._bind_key('Control-b', self.backward_char)
        self._bind_key('Right', self.forward_char)
        self._bind_key('Control-f', self.forward_char)
        self._bind_key('BackSpace', self.backward_delete_char)
        self._bind_key('Home', self.beginning_of_line)
        self._bind_key('End', self.end_of_line)
        self._bind_key('Delete', self.delete_char)
        self._bind_key('Control-d', self.delete_char)
        self._bind_key('Clear', self.clear_screen)
        self._bind_key('Alt-f', self.forward_word)
        self._bind_key('Alt-b', self.backward_word)
        self._bind_key('Control-l', self.clear_screen)
        self._bind_key('Control-p', self.previous_history)
        self._bind_key('Up', self.history_search_backward)
        self._bind_key('Control-n', self.next_history)
        self._bind_key('Down', self.history_search_forward)
        self._bind_key('Control-a', self.beginning_of_line)
        self._bind_key('Control-e', self.end_of_line)
        self._bind_key('Alt-<', self.beginning_of_history)
        self._bind_key('Alt->', self.end_of_history)
        self._bind_key('Control-r', self.reverse_search_history)
        self._bind_key('Control-s', self.forward_search_history)
        self._bind_key('Alt-p', self.non_incremental_reverse_search_history)
        self._bind_key('Alt-n', self.non_incremental_forward_search_history)
        self._bind_key('Control-z', self.undo)
        self._bind_key('Control-_', self.undo)
        self._bind_key('Escape', self.prefix_meta)
        self._bind_key('Meta-d', self.kill_word)
        self._bind_key('Meta-Delete', self.backward_kill_word)
        self._bind_key('Control-w', self.unix_word_rubout)
        self._bind_key('Control-v', self.quoted_insert)

        # Add keybindings for numpad
        # first the number keys
        self._bind_key('NUMPAD0', self.self_insert)
        self._bind_key('NUMPAD1', self.self_insert)
        self._bind_key('NUMPAD2', self.self_insert)
        self._bind_key('NUMPAD3', self.self_insert)
        self._bind_key('NUMPAD4', self.self_insert)
        self._bind_key('NUMPAD5', self.self_insert)
        self._bind_key('NUMPAD6', self.self_insert)
        self._bind_key('NUMPAD7', self.self_insert)
        self._bind_key('NUMPAD8', self.self_insert)
        self._bind_key('NUMPAD9', self.self_insert)
        # then the others: / * - + 
        self._bind_key('Divide', self.self_insert)
        self._bind_key('Multiply', self.self_insert)
        self._bind_key('Add', self.self_insert)
        self._bind_key('Subtract', self.self_insert)
        # the decimal separator: '.' on US keyboards, ',' on DE one's
        self._bind_key('VK_DECIMAL', self.self_insert)


    def vi_editing_mode(self, e): # (M-C-j)
        '''When in emacs editing mode, this causes a switch to vi editing
        mode.'''
        pass

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
    Console.install_readline(rl.readline)

