__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

from threading import Lock

import sandbox
import broker
import logging


class EventEngine(object):
    """loads all the event handlers, manages the connections, subscribes to the correct topic
        and starts the processing of the events.

        engine concept:
        - needs to run in pypy sandbox for safety. Can also run entire module
        - user loads module with api call.
          module example:
            from when import *
            from resources import Sensor, Actuator
            motionHallway = Sensor('id')
            luxHallway = Sensor('id')
            lightHallway = Actuator('id')

            @When([motionHallway, luxHallway], motionHallway == True and luxHallway < 150)
            def controlHallwayLights():
                lightHallway.value = True

        - engine runs module and sets switch to identify;
            - first load; 'when' stores list of assets in module field so that engine can retrieve
            - upon regular call: if condition == true call function
    """

    def __init__(self):
        self._rulesToRun = {}
        self.lock = Lock()

    def run(self):
        """"entry point of the event engine"""
        broker.connect()
        sandbox.loadModules()               # load all the known modules, so we can init things properly
        for moduleName in sandbox.LoadedModules:
            try:
                topics = sandbox.queryTopics(moduleName)
                self.setup(moduleName, topics)
            except:
                logging.exception("failed to load module at start")
        broker.process()

    def setup(self, file_to_run, topics):
        """
        store the app in the db.
        :param definition: the definition of the app: clientId, clientKey + code + name
        """
        # todo: add implementation that saves to db?.
        if topics:
            self.lock.acquire()
            try:
                for topic in topics:
                    if not topic in self._rulesToRun:
                        result = broker.CallbackObj(file_to_run, topic)
                        self._rulesToRun[topic] = result
                        broker.subscribeTo(topic, result)
                    else:
                        self._rulesToRun[topic].append(file_to_run)
            finally:
                self.lock.release()

    def addDefinition(self, data):
        """adds a new definition to the engine
        :type data: json dictionary
        :param data: the defintion to add. Should contain the following fields:
            - name of the app/definition
            - version of the app/definition
            - username & password: specifies for which user and his credentials (for creating the http/mqtt connection)
            - code: code to execute, in python.
        """
        #store the data in the rules db.
        #run the code block with parameter set to build the asset id list.
        #get the assets, link them to this definition and store them in the db
        try:
            sandbox.store(data)
            modulePath = sandbox.buildPath(data)
            topics = sandbox.queryTopics(modulePath)
            dispatcher.setup(modulePath, topics)       # when we receive a value, it's a new calback object that has to be registered with the broker.
        except Exception as e:
            logging.exception("failed to add definition")
            return str(e)
        return None
