# -*- coding: UTF-8 -*-
#this file is needed in site-packages to emulate readline
#necessary for rlcompleter since it relies on the existance
#of a readline module
from pyreadline.rlmain import Readline


# create a Readline object to contain the state
rl = Readline()

if rl.disable_readline:
    def dummy(completer=""):
        pass
    for funk in __all__:
        globals()[funk] = dummy
else:
    def GetOutputFile():
        u'''Return the console object used by readline so that it can be used for printing in color.'''
        return rl.console

    import pyreadline.console as console

    # make these available so this looks like the python readline module
    read_init_file = rl.read_init_file
    parse_and_bind = rl.parse_and_bind
    clear_history = rl.clear_history
    add_history = rl.add_history
    insert_text = rl.insert_text

    write_history_file = rl.write_history_file
    read_history_file = rl.read_history_file

    get_begidx = rl.get_begidx
    get_endidx = rl.get_endidx
    get_current_history_length = rl.get_current_history_length
    get_history_length = rl.get_history_length
    get_history_item = rl.get_history_item
    get_line_buffer = rl.get_line_buffer
    set_completer = rl.set_completer
    get_completer = rl.get_completer
    get_completer_delims = rl.get_completer_delims
    get_completion_type = rl.get_completion_type

    remove_history_item = rl.remove_history_item
    replace_history_item = rl.replace_history_item
    redisplay = rl.redisplay

    set_completer_delims = rl.set_completer_delims
    set_history_length = rl.set_history_length
    set_pre_input_hook = rl.set_pre_input_hook
    set_startup_hook = rl.set_startup_hook
    set_completion_display_matches_hook = rl.set_completion_display_matches_hook

    callback_handler_install=rl.callback_handler_install
    callback_handler_remove=rl.callback_handler_remove
    callback_read_char=rl.callback_read_char

    console.install_readline(rl.readline)

