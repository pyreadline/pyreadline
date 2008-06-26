# -*- coding: utf-8 -*-
#*****************************************************************************
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************

""" Mockup of gui-use of pyreadline


"""

import Tkinter

class KeyEvent(object):
    def __init__(self, char, shift, control, meta, keyname):
        self.char=char
        self.shift=shift
        self.control=control
        self.meta=meta
        self.keyname=keyname


class DumbReadLine(object):
    def __init__(self):
        self._text=[]


    def ProcKeyEvent(self, event):
        char=event.char
        if event.keyname=="backspace":
            self._text=self._text[:-1]
        elif event.keyname=="return":
            return True
        elif len(event.char)==1:
            self._text.append(event.char)
        return False

    def get_line(self):
        return "".join(self._text)

    def new_line(self):
        self._text=[]

class App:
    def __init__(self, master):
        self.lines=["Hello"]
        self.RL=DumbReadLine()
        self.textvar = Tkinter.StringVar()
        self._update_line()
        self.text=Tkinter.Label(master, textvariable=self.textvar,width=50,height=40,justify=Tkinter.LEFT,anchor=Tkinter.NW)
        self.text.pack(side=Tkinter.LEFT)
        master.bind("<Key>",self.handler)
        
    def handler(self, event):
        if len(event.keysym)>1:
            keysym=event.keysym.lower()
        else:
            keysym=""
        keyevent=KeyEvent(event.char, False, False, False, keysym)
        result=self.RL.ProcKeyEvent(keyevent)
        if result:
            self.lines.append(self.RL.get_line())
            self.RL.new_line()
        self._update_line()
        
        
    def _update_line(self):
        self.textvar.set("\n".join(self.lines+[self.RL.get_line()]))
        
        
        
root=Tkinter.Tk()

display=App(root)
root.mainloop()