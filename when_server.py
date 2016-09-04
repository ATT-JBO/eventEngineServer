__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

#platform specific (server vs user) code for the 'When' functionality

import logging
import att_event_engine.att as att
from att_event_engine.timer import Timer
import att_event_engine.resources as resources
import redis
import settings

BUILD_ASSET_LIST = False
"""when true, the code is run in order to find out the list of assets (or filters) that have to be
monitored"""
MODULE_NAME = None
"""the name of the module in who's context we are currently running (set by sandbox).
Provides a unique name (together with callback-function-name) for redis
"""
TOPIC_CONTEXT = None
"""when running the rules, this contains the topic query that triggered the execution. Helps us in filtering which rules need to be run"""

TopicPaths =set()
_memStore = redis.StrictRedis(host=settings.redisHost, port=settings.redisPort, db=settings.redisDB, password=settings.redisPwd)

def registerMonitor(toMonitor, condition, callback):
    """
    depending on the current mode:
    - normal run: check if the condition is met, if so, execute
    - registration of asset: store the list of asset id's
    """

    try:
        global TopicPaths
        monitor = att.SubscriberData(resources.defaultconnection)
        for item in toMonitor:
            if isinstance(item, Timer):
                monitor.level = 'timer'
                topics = item.getTopics(divider='.', wildcard='*')
            else:
                topics = item.getTopics()
            for topic in topics:
                monitor.id = topic
                monitor.direction = 'in'
                topicStr = monitor.getTopic(divider='.', wildcard='*')
                if BUILD_ASSET_LIST:
                    TopicPaths.add(topicStr)
                elif topicStr == TOPIC_CONTEXT:
                    callbackName = "{}_{}".format(MODULE_NAME, callback.__name__)
                    if condition:
                        if condition():
                            if _memStore.get(callbackName) != 'True':           # we store the conditional value in memory, not yet in disk
                                _memStore.set(callbackName, True)
                                callback()
                        else:
                            _memStore.set(callbackName, False)
                    else:
                        callback()
                    return                                                   # once we matched a topic against the current callback, we are done for a regulr run (don't have to build the topics)
    except:
        logging.exception("when decorator failed to process")
