import win32con as c32
from ctypes import windll
import ctypes
# table for translating virtual keys to X windows key symbols
code2sym_map = {c32.VK_CANCEL: 'Cancel',
                c32.VK_BACK: 'BackSpace',
                c32.VK_TAB: 'Tab',
                c32.VK_CLEAR: 'Clear',
                c32.VK_RETURN: 'Return',
                c32.VK_SHIFT:'Shift_L',
                c32.VK_CONTROL: 'Control_L',
                c32.VK_MENU: 'Alt_L',
                c32.VK_PAUSE: 'Pause',
                c32.VK_CAPITAL: 'Caps_Lock',
                c32.VK_ESCAPE: 'Escape',
                c32.VK_SPACE: 'space',
                c32.VK_PRIOR: 'Prior',
                c32.VK_NEXT: 'Next',
                c32.VK_END: 'End',
                c32.VK_HOME: 'Home',
                c32.VK_LEFT: 'Left',
                c32.VK_UP: 'Up',
                c32.VK_RIGHT: 'Right',
                c32.VK_DOWN: 'Down',
                c32.VK_SELECT: 'Select',
                c32.VK_PRINT: 'Print',
                c32.VK_EXECUTE: 'Execute',
                c32.VK_SNAPSHOT: 'Snapshot',
                c32.VK_INSERT: 'Insert',
                c32.VK_DELETE: 'Delete',
                c32.VK_HELP: 'Help',
                c32.VK_F1: 'F1',
                c32.VK_F2: 'F2',
                c32.VK_F3: 'F3',
                c32.VK_F4: 'F4',
                c32.VK_F5: 'F5',
                c32.VK_F6: 'F6',
                c32.VK_F7: 'F7',
                c32.VK_F8: 'F8',
                c32.VK_F9: 'F9',
                c32.VK_F10: 'F10',
                c32.VK_F11: 'F11',
                c32.VK_F12: 'F12',
                c32.VK_F13: 'F13',
                c32.VK_F14: 'F14',
                c32.VK_F15: 'F15',
                c32.VK_F16: 'F16',
                c32.VK_F17: 'F17',
                c32.VK_F18: 'F18',
                c32.VK_F19: 'F19',
                c32.VK_F20: 'F20',
                c32.VK_F21: 'F21',
                c32.VK_F22: 'F22',
                c32.VK_F23: 'F23',
                c32.VK_F24: 'F24',
                c32.VK_NUMLOCK: 'Num_Lock,',
                c32.VK_SCROLL: 'Scroll_Lock',
                c32.VK_APPS: 'VK_APPS',
                c32.VK_PROCESSKEY: 'VK_PROCESSKEY',
                c32.VK_ATTN: 'VK_ATTN',
                c32.VK_CRSEL: 'VK_CRSEL',
                c32.VK_EXSEL: 'VK_EXSEL',
                c32.VK_EREOF: 'VK_EREOF',
                c32.VK_PLAY: 'VK_PLAY',
                c32.VK_ZOOM: 'VK_ZOOM',
                c32.VK_NONAME: 'VK_NONAME',
                c32.VK_PA1: 'VK_PA1',
                c32.VK_OEM_CLEAR: 'VK_OEM_CLEAR',
                c32.VK_NUMPAD0: 'NUMPAD0',
                c32.VK_NUMPAD1: 'NUMPAD1',
                c32.VK_NUMPAD2: 'NUMPAD2',
                c32.VK_NUMPAD3: 'NUMPAD3',
                c32.VK_NUMPAD4: 'NUMPAD4',
                c32.VK_NUMPAD5: 'NUMPAD5',
                c32.VK_NUMPAD6: 'NUMPAD6',
                c32.VK_NUMPAD7: 'NUMPAD7',
                c32.VK_NUMPAD8: 'NUMPAD8',
                c32.VK_NUMPAD9: 'NUMPAD9',
                c32.VK_DIVIDE: 'Divide',
                c32.VK_MULTIPLY: 'Multiply',
                c32.VK_ADD: 'Add',
                c32.VK_SUBTRACT: 'Subtract',
                c32.VK_DECIMAL: 'VK_DECIMAL'
               }

# function to handle the mapping
def make_keysym(keycode):
    try:
        sym = code2sym_map[keycode]
    except KeyError:
        sym = ''
    return sym

sym2code_map = {}
for code,sym in code2sym_map.iteritems():
    sym2code_map[sym.lower()] = code

def key_text_to_keyinfo(keytext):
    '''Convert a GNU readline style textual description of a key to keycode with modifiers'''
    if keytext.startswith('"'): # "
        return keyseq_to_keyinfo(keytext[1:-1])
    else:
        return keyname_to_keyinfo(keytext)

VkKeyScan = windll.user32.VkKeyScanA

def char_to_keyinfo(char, control=False, meta=False, shift=False):
    vk = VkKeyScan(ord(char))
    if vk & 0xffff == 0xffff:
        print 'VkKeyScan("%s") = %x' % (char, vk)
        raise ValueError, 'bad key'
    if vk & 0x100:
        shift = True
    if vk & 0x200:
        control = True
    if vk & 0x400:
        meta = True
    return (control, meta, shift, vk & 0xff)

def keyname_to_keyinfo(keyname):
    control = False
    meta = False
    shift = False

    while 1:
        lkeyname = keyname.lower()
        if lkeyname.startswith('control-'):
            control = True
            keyname = keyname[8:]
        elif lkeyname.startswith('meta-'):
            meta = True
            keyname = keyname[5:]
        elif lkeyname.startswith('alt-'):
            meta = True
            keyname = keyname[4:]
        elif lkeyname.startswith('shift-'):
            shift = True
            keyname = keyname[6:]
        else:
            if len(keyname) > 1:
                return (control, meta, shift, sym2code_map[keyname.lower()])
            else:
                return char_to_keyinfo(keyname, control, meta, shift)

def keyseq_to_keyinfo(keyseq):
    res = []
    control = False
    meta = False
    shift = False

    while 1:
        if keyseq.startswith('\\C-'):
            control = True
            keyseq = keyseq[3:]
        elif keyseq.startswith('\\M-'):
            meta = True
            keyseq = keyseq[3:]
        elif keyseq.startswith('\\e'):
            res.append(char_to_keyinfo('\033', control, meta, shift))
            control = meta = shift = False
            keyseq = keyseq[2:]
        elif len(keyseq) >= 1:
            res.append(char_to_keyinfo(keyseq[0], control, meta, shift))
            control = meta = shift = False
            keyseq = keyseq[1:]
        else:
            return res[0]

def make_keyinfo(keycode, state):
    control = (state & (4+8)) != 0
    meta = (state & (1+2)) != 0
    shift = (state & 0x10) != 0
    return (control, meta, shift, keycode)
