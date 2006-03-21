# -*- coding: utf-8 -*-
#*****************************************************************************
#       Copyright (C) 2006  Jorgen Stenarson. <jorgen.stenarson@bostream.nu>
#
#  Distributed under the terms of the BSD License.  The full license is in
#  the file COPYING, distributed as part of this software.
#*****************************************************************************
import re,operator

import wordmatcher
import pyreadline.clipboard as clipboard

class NotAWordError(IndexError):
    pass

def quote_char(c):
    if ord(c)>0:
        return c



############## Line positioner ########################

class LinePositioner(object):
    def __call__(self,line):
        NotImplementedError("Base class !!!")

class NextChar(LinePositioner):
    def __call__(self,line):
        if line.point<len(line.line_buffer):
            return line.point+1
        else:
            return line.point
NextChar=NextChar()

class PrevChar(LinePositioner):
    def __call__(self,line):
        if line.point>0:
            return line.point-1
        else:
            return line.point
PrevChar=PrevChar()

class NextWordStart(LinePositioner):
    def __call__(self,line):
        return line.next_start_segment(line.line_buffer,line.is_word_token)[line.point]
NextWordStart=NextWordStart()

class NextWordEnd(LinePositioner):
    def __call__(self,line):
        return line.next_end_segment(line.line_buffer,line.is_word_token)[line.point]
NextWordEnd=NextWordEnd()

class PrevWordStart(LinePositioner):
    def __call__(self,line):
        return line.prev_start_segment(line.line_buffer,line.is_word_token)[line.point]
PrevWordStart=PrevWordStart()


class WordStart(LinePositioner):
    def __call__(self,line):
        if line.is_word_token(line.get_line_text()[Point(line):Point(line)+1]):
            if Point(line)>0 and line.is_word_token(line.get_line_text()[Point(line)-1:Point(line)]):
                return PrevWordStart(line)
            else:
                return line.point
        else:   
            raise NotInWord
WordStart=WordStart()

class WordEnd(LinePositioner):
    def __call__(self,line):
        if line.is_word_token(line.get_line_text()[Point(line):Point(line)+1]):
            if line.is_word_token(line.get_line_text()[Point(line)+1:Point(line)+2]):
                return NextWordEnd(line)
            else:
                return line.point
        else:   
            raise NotAWordError("Point is not in a word")
WordEnd=WordEnd()

class PrevWordEnd(LinePositioner):
    def __call__(self,line):
        return line.prev_end_segment(line.line_buffer,line.is_word_token)[line.point]
PrevWordEnd=PrevWordEnd()

class StartOfLine(LinePositioner):
    def __call__(self,line):
        return 0
StartOfLine=StartOfLine()

class EndOfLine(LinePositioner):
    def __call__(self,line):
        return len(line.line_buffer)
EndOfLine=EndOfLine()

class Point(LinePositioner):
    def __call__(self,line):
        return line.point
Point=Point()

class Mark(LinePositioner):
    def __call__(self,line):
        return line.mark
Mark=Mark()

all_positioners=[(value.__class__.__name__,value) for key,value in globals().items() if isinstance(value,LinePositioner)]
all_positioners.sort()

############### LineSlice #################

class LineSlice(object):
    def __call__(self,line):
        NotImplementedError("Base class !!!")


class CurrentWord(LineSlice):
    def __call__(self,line):
        return slice(WordStart(line),WordEnd(line),None)
CurrentWord=CurrentWord()

class NextWord(LineSlice):
    def __call__(self,line):
        work=TextLine(line)
        work.point=NextWordStart
        start=work.point
        stop=NextWordEnd(work)
        return slice(start,stop)
NextWord=NextWord()

class PrevWord(LineSlice):
    def __call__(self,line):
        work=TextLine(line)
        work.point=PrevWordEnd
        stop=work.point
        start=PrevWordStart(work)
        return slice(start,stop)
PrevWord=PrevWord()

class PointSlice(LineSlice):
    def __call__(self,line):
        return slice(Point(line),Point(line)+1,None)
PointSlice=PointSlice()


###############  TextLine  ######################

class TextLine(object):
    def __init__(self,txtstr,point=None,mark=None):
        self.line_buffer=[]
        self._point=0
        self.mark=-1
        self.undo_stack=[]
        self.overwrite=False
        if isinstance(txtstr,TextLine): #copy 
            if point is None:
                self.point=txtstr.point
            else:                
                self.point=point
            if mark is None:
                self.mark=txtstr.mark
            else:
                self.mark=mark
            self.line_buffer=txtstr.line_buffer[:]
        else:            
            self._insert_text(txtstr)
            if point is None:
                self.point=0
            else:
                self.point=point
            if mark is None:
                self.mark=-1
            else:
                self.mark=mark

        self.is_word_token=wordmatcher.is_word_token
        self.next_start_segment=wordmatcher.next_start_segment
        self.next_end_segment=wordmatcher.next_end_segment
        self.prev_start_segment=wordmatcher.prev_start_segment
        self.prev_end_segment=wordmatcher.prev_end_segment
        
    def push_undo(self):
        ltext = self.get_line_text()
        if self.undo_stack and ltext == self.undo_stack[-1].get_line_text():
            self.undo_stack[-1].point = self.point
        else:
            self.undo_stack.append(self.copy())

    def pop_undo(self):
        if len(self.undo_stack) >= 2:
            self.undo_stack.pop()
            self.set_top_undo()
            self.undo_stack.pop()
        else:
            self.reset_line()
            self.undo_stack = []

    def set_top_undo(self):
        if self.undo_stack:
            undo=self.undo_stack[-1]
            self.line_buffer=undo.line_buffer
            self.point=undo.point
            self.mark=undo.mark
        else:
            pass
        
    def __repr__(self):
        return 'TextLine("%s",point=%s,mark=%s)'%(self.line_buffer,self.point,self.mark)

    def copy(self):
        return self.__class__(self)

    def set_point(self,value):
        if isinstance(value,LinePositioner):
            self._point=value(self)
        else:
            self._point=value
    def get_point(self):
        return self._point
    point=property(get_point,set_point)


    def visible_line_width(self,position=Point):
        """Return the visible width of the text in line buffer up to position."""
        return len(self[:position].quoted_text())

    def quoted_text(self):
        quoted = [ quote_char(c) for c in self.line_buffer ]
        self.line_char_width = [ len(c) for c in quoted ]
        return ''.join(quoted)

    def get_line_text(self):
        return ''.join(self.line_buffer)

    def set_line(self, text, cursor=None):
        self.line_buffer = [ c for c in str(text) ]
        if cursor is None:
            self.point = len(self.line_buffer)
        else:
            self.point = cursor

    def reset_line(self):
        self.line_buffer = []
        self.point = 0

    def _insert_text(self, text):
        if self.overwrite:
            for c in text:
                #if self.point:
                self.line_buffer[self.point]= c
                self.point += 1
        else:            
            for c in text:
                self.line_buffer.insert(self.point, c)
                self.point += 1
    
    def __getitem__(self,key):
        #Check if key is LineSlice, convert to regular slice
        #and continue processing
        if isinstance(key,LineSlice): 
            key=key(self)
        if isinstance(key,slice):
            if key.step is None:
                pass
            else:
                raise Error
            if key.start is None:
                start=StartOfLine(self)
            elif isinstance(key.start,LinePositioner):
                start=key.start(self)
            else:
                start=key.start
            if key.stop is None:                   
                stop=EndOfLine(self)
            elif isinstance(key.stop,LinePositioner):
                stop=key.stop(self)
            else:
                stop=key.stop
            return TextLine(self.line_buffer[start:stop])
        elif isinstance(key,LinePositioner):
            return self.line_buffer[key(self)]
        elif isinstance(key,tuple):
            raise IndexError("Cannot use step in line buffer indexing") #Multiple slice not allowed
        else:
            return TextLine(self.line_buffer[key])

    def __delitem__(self,key):
        if isinstance(key,LineSlice):
            key=key(self)
        if isinstance(key,slice):
            start=key.start
            stop=key.stop
            if isinstance(start,LinePositioner):
                start=start(self)
            if isinstance(stop,LinePositioner):
                stop=stop(self)
        elif isinstance(key,LinePositioner):
            start=key(self)
            stop=start+1
        else:
            start=key
            stop=key+1
        if self.point>stop:
            self.point=self.point-(stop-start)
        elif self.point>=start and self.point <=stop:
            self.point=start
        prev=self.line_buffer[:start]
        rest=self.line_buffer[stop:]
        self.line_buffer=prev+rest

    def __setitem__(self,key,value):
        if isinstance(key,LineSlice):
            key=key(self)
        if isinstance(key,slice):
            start=key.start
            stop=key.stop
            prev=self.line_buffer[:start]
            rest=self.line_buffer[stop:]
        elif isinstance(key,LinePositioner):
            start=key(self)
            stop=start+1
        else:
            start=key
            stop=key+1
        value=TextLine(value).line_buffer
        self.line_buffer=prev+value+rest       

    def __len__(self):
        return len(self.line_buffer)

    def upper(self):
        self.line_buffer=[x.upper() for x in self.line_buffer]

    def lower(self):
        self.line_buffer=[x.lower() for x in self.line_buffer]

    def startswith(self,txt):
        return self.get_line_text().startswith(txt)

    def endswith(self,txt):
        return self.get_line_text().endswith(txt)

    def __contains__(self,txt):
        return txt in self.get_line_text()


lines=[TextLine("abc"),
       TextLine("abc def"),
       TextLine("abc def  ghi"),
       TextLine("  abc  def  "),
      ]
l=lines[2]
l.point=5



class ReadLineTextBuffer(TextLine):
    def __init__(self,txtstr,point=None,mark=None):
        super(ReadLineTextBuffer,self).__init__(txtstr,point,mark)
        self.enable_win32_clipboard=True

    def insert_text(self,char):
        self._insert_text(char)

######### Movement

    def beginning_of_line(self):
        self.point=StartOfLine
        
    def end_of_line(self):
        self.point=EndOfLine
        
    def forward_char(self):
        self.point=NextChar
        
    def backward_char(self):
        self.point=PrevChar
        
    def forward_word(self):
        self.point=NextWordStart
       
    def backward_word(self):
        self.point=PrevWordStart

######### delete       

    def delete_char(self):
        del self[Point]
        
    def backward_delete_char(self):
        self.backward_char()
        self.delete_char()

    def delete_current_word(self):
        del self[CurrentWord]
        
    def delete_horizontal_space(self):
        pass
######### Case

    def upcase_word(self):
        try:
            self[CurrentWord]=self[CurrentWord].line_buffer.upper()
        except NotAWordError:
            pass
        
    def downcase_word(self):
        try:
            self[CurrentWord]=self[CurrentWord].line_buffer.lower()
        except NotAWordError:
            pass
        
    def  capitalize_word(self):
        try:
            self[CurrentWord]=self[CurrentWord].line_buffer.capitalize()
        except NotAWordError:
            pass
########### Transpose
    def transpose_chars(self):
        pass

    def transpose_words(self):
        pass

############ Kill

    def kill_line(self):
        if self.enable_win32_clipboard:
                toclipboard="".join(self.line_buffer[self.point:])
                clipboard.set_clipboard_text(toclipboard)
        self.line_buffer[self.point:] = []
    
    def backward_kill_line(self):
        del self[StartOfLine:Point]
        
    def unix_line_discard(self):
        pass

    def kill_word(self):
        """Kills to next word ending"""
        del self[Point:NextWordEnd]

    def backward_kill_word(self):
        """Kills to next word ending"""
        pass

    def unix_word_rubout(self): 
        pass

    def kill_region(self):
        pass

    def copy_region_as_kill(self):
        pass

    def copy_backward_word(self):
        pass

    def copy_forward_word(self):
        pass
        

    def yank(self):
        pass

    def yank_pop(self):
        pass


##############  Mark 

    def set_mark(self):
        self.mark=self.point
        
    def exchange_point_and_mark(self):
        pass


    def copy_region_to_clipboard(self): # ()
        '''Copy the text in the region to the windows clipboard.'''
        if self.enable_win32_clipboard:
                mark=min(self.mark,len(self.line_buffer))
                cursor=min(self.point,len(self.line_buffer))
                if self.mark==-1:
                        return
                begin=min(cursor,mark)
                end=max(cursor,mark)
                toclipboard="".join(self.line_buffer[begin:end])
                clipboard.SetClipboardText(str(toclipboard))

##############  Paste


##################################################################
q=ReadLineTextBuffer("asff asFArw  ewrWErhg",point=8)
q=TextLine("asff asFArw  ewrWErhg",point=8)

def show_pos(buff,pos,chr="."):
    l=len(buff.line_buffer)
    def choice(bool):
        if bool:
            return chr
        else:
            return " "
    return "".join([choice(pos==idx) for idx in range(l+1)])


def test_positioner(buff,points,positioner):
    print (" %s "%positioner.__class__.__name__).center(40,"-")
    buffstr=buff.line_buffer
    
    print '"%s"'%(buffstr)
    for point in points:
        b=TextLine(buff,point=point)
        out=[" "]*(len(buffstr)+1)
        pos=positioner(b)
        if pos==point:
            out[pos]="&"
        else:
            out[point]="."
            out[pos]="^"
        print '"%s"'%("".join(out))
    
if __name__=="__main__":


    print '%-15s "%s"'%("Position",q.get_line_text())
    print '%-15s "%s"'%("Point",show_pos(q,q.point))


    for name,positioner in all_positioners:
        pos=positioner(q)
        []
        print '%-15s "%s"'%(name,show_pos(q,pos,"^"))

    l=TextLine("kjjk")
