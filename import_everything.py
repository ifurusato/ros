#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Searches for all import statements from within the current directory tree,
# then attempts to import each module, producing a report indicating success
# or failure. This lets you know which modules you'll need to manually import
# via pip3.
#
# Note that during the imports an exception handler may call sys.exit(); in
# this case the script may terminate prior to finishing. If you don't see the
# "EOF" message the script did not finish.
#
# author:   Murray Altheim
# created:  2021-02-10
# modified: 2021-02-10
#

import sys, traceback, itertools, importlib, re, subprocess
try:
    from colorama import init, Fore, Style
    init()
except ImportError:
    sys.exit("This script requires the colorama module.\n"\
           + "Install with: sudo pip3 install colorama")

# settings ................
INCLUDE_IMPORTS = True    # if True query on imports of the form "import xxx"
INCLUDE_FROMS   = True    # if True query on imports of the form "from xxx import yyy"
IGNORE_LIB      = True    # if true ignore imports of the form "from lib.xxx" or "import lib.xxx"
LIB_DIR         = 'lib'   # the name of the local module directory (e.g., "./lib")
GENERATE_SCRIPT = False   # if true print an installer script to the console

# ..............................................................................
def _find_in_files(regex):
    '''
    Search through all *.py files within the directory tree, returning all
    lines containing the regular expression term.
    '''
    _lib_dir_regex = '{}\.'.format(LIB_DIR)
    _tuples = []
    _list   = []
    print(Fore.CYAN + Style.BRIGHT + '\n-- searching for \"{}\"...'.format(regex) + Style.RESET_ALL)
    command = 'find . -name "*.py" -exec grep -EH \"{}\" {{}} \;'.format(regex)
    print(Fore.CYAN + Style.DIM + '-- command: \"{}\"...'.format(command) + Style.RESET_ALL)
    proc = subprocess.Popen([command], stdout=subprocess.PIPE,universal_newlines=True, shell=True)
    count = 0
    for line in proc.stdout:
        _line = str(line).strip()
        _info = _line.split(':', 1)
        _filename     = _info[0]
        _library_name = _info[1]
#       if _info[1] not in _list:
        if _library_name not in _list and not( IGNORE_LIB and re.match(_lib_dir_regex, _library_name) ):
            count += 1
            _list.append(_info[1])
            _tuples.append(tuple([_library_name, _filename]))
            print(Fore.YELLOW + '-- found [%d]\r'%count + Style.RESET_ALL, end="")
        else:
#           print(Fore.YELLOW + '-- ignoring {} in {}'.format(_library_name, _filename) + Style.RESET_ALL)
            pass
    _list.sort()
    _tuples.sort()
    return _tuples

# ..............................................................................
def test_imports(froms, imports):
    '''
    Loop through all the imports.
    '''
    print(Fore.CYAN + '\n-- testing imports...' + Style.RESET_ALL)
    _processed = 0
    _successes = []
    _failures  = []
    _libraries = []
    for _library in itertools.chain(froms, imports):
        if _library not in _libraries:
            _processed += 1
            if _do_import(_library, False):
                _successes.append(_library)
            else:
                _failures.append(_library)
        _libraries.append(_library)

    for _library in _successes:
        print(Fore.GREEN + '   library available:\t{}'.format(_library) + Style.RESET_ALL)
    if GENERATE_SCRIPT:
        print(Fore.CYAN + '\n-- generate install script:' + Style.RESET_ALL)
        print('\n')
        print('#!/bin/sh')
        print('#')
        for _library in _failures:
#           print(Fore.RED   + '   library not found:\t{}'.format(_library) + Style.RESET_ALL)
            print('sudo pip3 install {}'.format(_library))
        print('#EOF')
    else: # just print failure
        for _library in _failures:
            print(Fore.RED   + '   library not found:\t{}'.format(_library) + Style.RESET_ALL)

    print(Fore.CYAN + '\n-- processed: {:d} of {:d} unique imports; {:d} successes, {:d} failures.'.format(\
            _processed, len(_libraries), len(_successes), len(_failures)) + Style.RESET_ALL)

# ..............................................................................
def _do_import(name, display_result):
    '''
    Attempt to import the named module. If 'display_result' is true,
    print the result to the console. Returns True if successful.
    '''
    try:
        importlib.import_module(name, package=None)
        if display_result:
            print(Fore.GREEN + '-- success imported library \'{}\''.format(name) + Style.RESET_ALL)
        return True
    except ImportError as e:
        if display_result:
            print(Fore.RED   + '-- failed to import library \'{}\': {}'.format(name, e) + Style.RESET_ALL)
        return False
    except Exception as e:
        if display_result:
            print(Fore.RED   + '-- exception importing library \'{}\': {}'.format(name, e) + Style.RESET_ALL)
        return False

# ..............................................................................
def search_froms():
    '''
    Search for unique "from xxx import yyy" statements, returning a sorted list.
    '''
    _froms = []
    _lib_dir_regex = '{}\.'.format(LIB_DIR)
    _regex = '^[ ]*from '
    print(Fore.GREEN + '\nimport list contents:' + Style.RESET_ALL)
    for _items in _find_in_files('^[ ]*from.*import.*'):
        _item = _items[0]
        _filename = _items[1]
        _library_name = re.sub(' import.*', '', _item)
        _library_name = re.sub(_regex, '', _library_name).strip()
#       print(Fore.BLACK + Style.BRIGHT + 'processing library name: \'{}\'.'.format(_library_name) + Style.RESET_ALL)
        if IGNORE_LIB and re.match(_lib_dir_regex, _library_name):
#           print(Fore.BLUE + Style.DIM + 'ignoring library name: \'{}\''.format(_library_name) + Style.RESET_ALL)
            pass
        elif len(_library_name) > 1 and _library_name not in _froms:
#           print(Fore.BLUE + Style.BRIGHT + 'adding library name: \'{}\'.'.format(_library_name) + Style.RESET_ALL)
            _froms.append(_library_name)
    _froms.sort()
    print(Fore.CYAN + '\n-- complete: {:d} instances of \'{}\' found.'.format(len(_froms), _regex) + Style.RESET_ALL)
    return _froms

# ..............................................................................
def search_imports():
    '''
    Search for unique "import xxx" statements, returning a sorted list.
    '''
    _imports = []
    _regex = '^[ ]*import '
    for _items in _find_in_files(_regex):
        _item = _items[0]
        _line = re.sub('^[ ]*import ','',_item)
        for _item in _line.split(','):
            _library_name = re.sub(' as.*','', _item)
            _library_name = re.sub('\#.*','', _library_name).strip()
            _library_name = re.sub('^lib\.','', _library_name)
            if IGNORE_LIB and _library_name.startswith('lib\.'):
                print(Fore.WHITE + Style.BRIGHT + 'ignoring library name: {}.'.format(_library_name) + Style.RESET_ALL)
                pass
            elif _library_name not in _imports:
                _imports.append(_library_name)
    _imports.sort()
    print(Fore.CYAN + '\n-- complete: {:d} instances of \'{}\' found.'.format(len(_imports), _regex) + Style.RESET_ALL)
    return _imports

# main .........................................................................
def main(argv):
    try:

        _froms   = search_froms() if INCLUDE_FROMS else []
        _imports = search_imports() if INCLUDE_IMPORTS else []
        test_imports(_froms, _imports)

    except Exception as e:
        print(Fore.RED + Style.BRIGHT + 'error: {}\n{}'.format(e, traceback.format_exc()) + Style.RESET_ALL)
    finally:
        print(Fore.CYAN + '-- finally.' + Style.RESET_ALL)

# call main ....................................................................
if __name__== "__main__":
    main(sys.argv[1:])

#EOF
