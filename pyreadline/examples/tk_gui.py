# -*- coding: utf-8 -*-
#*****************************************************************************
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

""" Mockup of gui-use of pyreadline


"""
from pyreadline.rlmain import BaseReadline
from pyreadline.keysyms.common import KeyPress
import pyreadline.logger as log
log.sock_silent=False
import Tkinter,sys


def KeyPress_from_event(event):
    if len(event.keysym)>1:
        keysym=event.keysym.lower()
        char=event.char
    else:
        keysym=""
        char=event.keysym
    return KeyPress(char, event.state&1!=0, event.state&4!=0, event.state&(131072)!=0, keysym)


class App:
    def __init__(self, master):
        self.frame=frame=Tkinter.Frame(master)
        frame.pack()
        self.lines=["Hello"]
        self.RL=BaseReadline()
        self.RL.read_inputrc()
        self.prompt=">>>"
        self.readline_setup(self.prompt)
        self.textvar = Tkinter.StringVar()
        self._update_line()
        self.text=Tkinter.Label(frame, textvariable=self.textvar,width=50,height=40,justify=Tkinter.LEFT,anchor=Tkinter.NW)
        self.text.pack(side=Tkinter.LEFT)
        master.bind("<Key>",self.handler)
        
    def handler(self, event):
        keyevent=KeyPress_from_event(event)
        try:
            result=self.RL.process_keyevent(keyevent)
        except EOFError:
            self.frame.quit()
            return
        if result:
            self.lines.append(self.RL.get_line_buffer())
            self.readline_setup(self.prompt)
        self._update_line()
        

    def readline_setup(self, prompt=''):
        self.RL.readline_setup(prompt)
        
    def _update_line(self):
        self.textvar.set("\n".join(self.lines+[self.prompt+" "+self.RL.get_line_buffer()]))
        
        
        
root=Tkinter.Tk()

display=App(root)
root.mainloop()