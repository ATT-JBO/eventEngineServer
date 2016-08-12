#this Module contains the interface to communicate with the pypy runtime. It provides the callbacks for supported
#modules. (security features)

import logging
import os
import sys
import traceback
from multiprocessing import Process, Manager
from threading import Timer
import pickle
import sandboxInternals
import settings
import when_server as when
import att_event_engine.resources as resources
import att_event_engine.attiotuserclient as iot

MAIN_FILE_NAME = 'rules.py'
"""The name of the file that stores the compiled code."""
CREDENTIALS_FILE_NAME = 'credentials.dat'
"""The name of the file that stores the credentials of."""

PARAMETERS_FILE_NAME = 'params.dat'
"""The name of the file that stores the parameter values"""

LOADED_MODULES_NAME = 'loaded.dat'
"""The name of the file that stores the compiled code."""

MAX_RUN = 3.0
"""the maximum time that an unssecure module is allowed to run"""

LoadedModules = set()
"""the location of all the dynamic modules that are currently loaded
This is stored in a file, so that it can easily be reloaded when the server restarts.
"""


def buildPath(pathDef):
    return os.path.join("uploaded", pathDef['username'], pathDef['name'].replace('.', '_'), pathDef['version'].replace('.', '_'))

def getModulePath(root):
    """return the name and path of the module that forms the entry point for the micro service."""
    return os.path.join(root, MAIN_FILE_NAME)

def getCredentialsPath(root):
    """return the name and path of the module that forms the entry point for the micro service."""
    return os.path.join(root, CREDENTIALS_FILE_NAME)

def getParametersPath(root):
    """return the name and path of the module that forms the entry point for the micro service."""
    return os.path.join(root, PARAMETERS_FILE_NAME)


def _killSubProcess(process):
    """kills the specified process
    This is called from a timer to make certain that the unsecure code doesn't run too long
    :param process: the Process object to kill
    :type process: Process
    """
    if process.is_alive() == True:
        process.terminate()

def queryTopics(app_to_run):
    """runs the specified code to find out which asset (topics) should be monitored.
    :param app_to_run: root path of the app to execute.
    :returns a list of topic paths that should be subscribed to for the specified micro-service.

    see: https://docs.python.org/2/library/multiprocessing.html#module-multiprocessing
         https://pypi.python.org/pypi/RestrictedPython/
    """
    manager = Manager()
    return_dict = manager.dict()
    app_to_run = str(os.path.join(settings.pluginDir, app_to_run))
    p = Process(target=_runSandbox, args=(app_to_run, return_dict, True))
    p.start()
    #don't wait until it is done, we can start another one. Just make certain that this one stops in time.
    t = Timer(MAX_RUN, _killSubProcess, args=[p])
    #t.start()
    p.join()        # for debugging
    #p.join(MAX_RUN)                            #wait untill the other process is done, then we can get the topics that need to be subscribed to.
    if 'error' in return_dict:  # if the subprocess caused an error, let the caller know
        raise Exception(return_dict['error'])
    if 'topics' in return_dict:
        return return_dict['topics']
    else:
        return None



def run(app_to_run, topicContext, assetId, value):
    """runs the specified code
    :type app_to_run: basestring
    :param app_to_run: root path of the app to execute.
    :param topicContext: the topic (routing-key) that the sysetem is subscribed to, which triggered this event. helps with filtering which rules must be run

    see: https://docs.python.org/2/library/multiprocessing.html#module-multiprocessing
         https://pypi.python.org/pypi/RestrictedPython/
    """
    manager = Manager()
    return_dict = manager.dict()
    app_to_run = str(os.path.join(settings.pluginDir, app_to_run))
    p = Process(target=_runSandbox, args=(app_to_run, return_dict, False, assetId, value, topicContext))
    p.start()
    # don't wait until it is done, we can start another one. Just make certain that this one stops in time.
    #t = Timer(MAX_RUN, _killSubProcess)
    #t.start()
    p.join(MAX_RUN)                 # wait untill done
    if 'error' in return_dict:                  # if the subprocess caused an error, let the caller know
        raise Exception(return_dict['error'])

def store(toStore):
    """stores the code on a local directory so that it can be run in a restricted environment
    The directory is based on clientId, app name and version
    """
    relDir = buildPath(toStore)
    directory = str(os.path.join(settings.pluginDir, relDir)) # os.path.abspath(relDir)
    if not os.path.exists(directory):
        os.makedirs(directory)
    code = toStore['code']
    with open(getModulePath(directory), 'w') as f:
        f.write(code)
    LoadedModules.add(relDir)  # also store the module as loaded, so we can reload it automatically when server restarts.
    with open(str(os.path.join(settings.pluginDir, LOADED_MODULES_NAME)), 'wb') as f:
        pickle.dump(LoadedModules, f)

    credentials = {'username': toStore['username'], 'password': toStore['password']}
    file = getCredentialsPath(directory)
    with open(file, 'wb') as f:
        pickle.dump(credentials, f)
    if 'parameters' in toStore:
        with open(getParametersPath(directory), 'wb') as f:
            pickle.dump(toStore['parameters'], f)

def loadModules():
    """load all the known module names from disk and store in the loadedmodules list.
    Called when the app starts up."""
    file = str(os.path.join(settings.pluginDir, LOADED_MODULES_NAME))
    if os.path.isfile(file):                 # if we haven't loaded any modules yet, then there is no file.
        global LoadedModules
        with open(file, 'rb') as f:
            LoadedModules = pickle.load(f)

def _runSandbox(app_path, return_dict, buildTopicList = False, assetId = None, value = None, topicContext=None):
    """run the specified compiled code file.
    see: https://pypi.python.org/pypi/RestrictedPython/
    :param app_path: the root path of the app that should be run (known file name contains the code to execute).
    :param buildTopicList: When true, the code will be called for querying the assets that should be monitored for the specified app.
    """
    try:
        file = getCredentialsPath(app_path)
        with open(file, 'rb') as f:
            credentials = pickle.load(f)
        iot.connect(str(credentials['username']), str(credentials['password']), settings.httpServer, settings.broker)

        file = getParametersPath(app_path)                          # load the parameter values
        if os.path.isfile(file):
            with open(file, 'rb') as f:
                resources.parameters = pickle.load(f)

        when.BUILD_ASSET_LIST = buildTopicList
        when.TOPIC_CONTEXT = topicContext
        file = getModulePath(app_path)
        when.MODULE_NAME = app_path
        with open(file, 'r') as f:
            code = f.read()
        if assetId:                                         # could be for a timer, in that case there is no asset
            resources.valueStore[assetId] = value
            resources.trigger = resources.Asset(assetId)
        sandboxInternals.execute(code)
        if buildTopicList:
            return_dict['topics'] = when.TopicPaths
    except Exception as e:
        return_dict['error'] = "traceback: {},\nerror: {}".format(repr(traceback.format_stack()), str(e))
        logging.exception("failed to run in sandbox mode")
