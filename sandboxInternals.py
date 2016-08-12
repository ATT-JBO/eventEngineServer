from RestrictedPython.PrintCollector import PrintCollector
from RestrictedPython.Guards import safe_builtins
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import full_write_guard
import sys
import os
import logging

def loader(path):
    class Loader(object):
        def load_module(self, name):
            if name not in sys.modules:
                #_mapper.LoadModule(path, name)
                #module = _mapper.GetModule(name)
                module  = __import__(name, fromlist=[''])
                module.__file__ = path
                sys.modules[name] = module
                if '.' in name:
                    parent_name, child_name = name.rsplit('.', 1)
                    setattr(sys.modules[parent_name], child_name, module)
            return sys.modules[name]
    return Loader()

class MetaImporter(object):
    def find_module(self, fullname, path=None):
        if fullname in ('_hashlib', 'ctypes'):
            raise ImportError('%s is not available in ironclad yet' % fullname)

        lastname = fullname.rsplit('.', 1)[-1]
        for d in (path or sys.path):
            pyd = os.path.join(d, lastname + '.pyd')
            if os.path.exists(pyd):
                return loader(pyd)

        return None


def minimal_import(name, _globals, _locals, names):
    if name not in ["att_event_engine.when", "att_event_engine.resources", "att_event_engine.factory", "att_event_engine.timer", "att_event_engine.attiotuserclient"]:
        raise ValueError, "unsupported library, not allowed to load {}".format(name)
    return __import__(name, _globals, _locals, names)


printed = []

class MyPrintCollector:
    '''Collect written text, and return it when called.'''
    #def __init__(self):
    #    self.txt = []
    def write(self, text):
        printed.append(text)
    def __call__(self):
        return ''.join(printed)


def execute(code):
    """run the specified code in a secure way"""
    sys.meta_path = [MetaImporter()]
    safe_builtins['__import__'] = minimal_import
    restricted_globals = {'__builtins__': safe_builtins, '_print_': MyPrintCollector, '_getattr_': getattr, "_write_": setattr}
    code = compile_restricted(code, '<string>', 'exec')
    try:
        exec(code) in restricted_globals
    except:
        logging.exception("failed to execute untrusted code")
    logging.info('outnput from module: ' + '\n'.join(printed))

    #rmodule = {'__builtins__': {'__import__': __import__, 'None': None, '__name__': 'restricted_module'}}

    #rmodule = {'__builtins__': {'__import__': minimal_import}}


