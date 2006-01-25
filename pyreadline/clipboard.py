# -*- coding: utf-8 -*-
#*****************************************************************************
#       Copyright (C) 2003-2006 Jack Trainor.
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************
###################################
#
# Based on recipe posted to ctypes-users
# see archive
# http://aspn.activestate.com/ASPN/Mail/Message/ctypes-users/1771866
#
#


###################################################################################
#
# The Python win32clipboard lib functions work well enough ... except that they
# can only cut and paste items from within one application, not across
# applications or processes.
#
# I've written a number of Python text filters I like to run on the contents of
# the clipboard so I need to call the Windows clipboard API with global memory
# for my filters to work properly.
#
# Here's some sample code solving this problem using ctypes.
#
# This is my first work with ctypes.  It's powerful stuff, but passing arguments
# in and out of functions is tricky.  More sample code would have been helpful,
# hence this contribution.
#
###################################################################################

from ctypes import *
from win32con import CF_TEXT, GHND

OpenClipboard = windll.user32.OpenClipboard
EmptyClipboard = windll.user32.EmptyClipboard
GetClipboardData = windll.user32.GetClipboardData
GetClipboardFormatName = windll.user32.GetClipboardFormatNameA
SetClipboardData = windll.user32.SetClipboardData
EnumClipboardFormats = windll.user32.EnumClipboardFormats
CloseClipboard = windll.user32.CloseClipboard
OpenClipboard.argtypes=[c_int]
EnumClipboardFormats.argtypes=[c_int]
CloseClipboard.argtypes=[]
GetClipboardFormatName.argtypes=[c_uint,c_char_p,c_int]
GetClipboardData.argtypes=[c_int]
SetClipboardData.argtypes=[c_int,c_int]

GlobalLock = windll.kernel32.GlobalLock
GlobalAlloc = windll.kernel32.GlobalAlloc
GlobalUnlock = windll.kernel32.GlobalUnlock
GlobalLock.argtypes=[c_int]
GlobalUnlock.argtypes=[c_int]
memcpy = cdll.msvcrt.memcpy

def enum():
    OpenClipboard(0)
    q=EnumClipboardFormats(0)
    while q:
        print q,
        q=EnumClipboardFormats(q)
    CloseClipboard()

def getformatname(format):
    buffer = c_buffer(" "*100)
    bufferSize = sizeof(buffer)
    OpenClipboard(0)
    GetClipboardFormatName(format,buffer,bufferSize)
    CloseClipboard()
    return buffer.value

def GetClipboardText():
    text = ""
    if OpenClipboard(0):
        hClipMem = GetClipboardData(CF_TEXT)
        if hClipMem:        
            GlobalLock.restype = c_char_p
            text = GlobalLock(hClipMem)
            GlobalUnlock(hClipMem)
        CloseClipboard()
    return text

def make_tab(lists):
    if hasattr(lists,"tolist"):
        lists=lists.tolist()
    ut=[]
    for rad in lists:
        if type(rad) in [list,tuple]:
            ut.append("\t".join(["%s"%x for x in rad]))
        else:
            ut.append("%s"%rad)
    return "\n".join(ut)            
    
def send_data(lists):
    SetClipboardText(make_tab(lists))
    
def SetClipboardText(text):
    buffer = c_buffer(text)
    bufferSize = sizeof(buffer)
    hGlobalMem = GlobalAlloc(c_int(GHND), c_int(bufferSize))
    GlobalLock.restype = c_void_p
    lpGlobalMem = GlobalLock(c_int(hGlobalMem))
    memcpy(lpGlobalMem, addressof(buffer), c_int(bufferSize))
    GlobalUnlock(c_int(hGlobalMem))
    if OpenClipboard(0):
        EmptyClipboard()
        SetClipboardData(c_int(CF_TEXT), c_int(hGlobalMem))
        CloseClipboard()


def set_clipboard_text(toclipboard):
    SetClipboardText(str(toclipboard))

def make_list_of_list(txt):
    def make_num(x):
        try:
            return int(x)
        except ValueError:
            try:
                return float(x)
            except ValueError:
                try:
                    return complex(x)
                except ValueError:
                    return x
        return x                
    ut=[]
    flag=False
    for rad in [x for x in txt.split("\r\n") if x!=""]:
        raden=[make_num(x) for x in rad.split("\t")]
        if str in map(type,raden):
            flag=True
        ut.append(raden)
    return ut,flag


def get_clipboard_text_and_convert(paste_list=False):
    """Get txt from clipboard. if paste_list==True the convert tab separated 
    data to list of lists. Enclose list of list in array() if all elements are 
    numeric"""
    txt=GetClipboardText()
    if txt:
        if paste_list and "\t" in txt:
            array,flag=make_list_of_list(txt)
            if flag:
                txt=repr(array)
            else:
                txt="array(%s)"%repr(array)
            txt="".join([c for c in txt if c not in " \t\r\n"])
    return txt

if __name__ == '__main__':
    txt=GetClipboardText()                            # display last text clipped
    print txt
     
     
     
     