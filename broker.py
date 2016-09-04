__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

#connect to the broker and monitor the correct topics so that the required rules can be triggered.

import logging
import pika
import json
import sandbox
import settings
import threading

channel = None


class CallbackObj(object):
    """contains the references to all the code objects that have subsribed for the same topic"""

    def __init__(self, toAdd, topic):
        """

        :type toAdd: basestring
        :param toAdd: module name to add which should be called when this callback object is triggered
        """
        self.modules = [toAdd]
        self.topic = topic
        """list of module names that need to be executed"""


    def callback(self, ch, method, properties, body):
        """
        run the modules. This is the broker callback function.
        :param ch:
        :param method:
        :param properties:
        :param body:
        :return:
        """
        try:
            topicParts = method.routing_key.split('.')
            if topicParts[-1] != 'timer':
                value = json.loads(body)
                asset = value['Id']
                value = value['Value']
            else:
                asset = None
                value = None
            for module in self.modules:
                try:
                    sandbox.run(module, self.topic, asset, value) #-> module moet object zijn, bewaart laatst verwerkte asset/value/timestamp, enkel runnen indien die verschillend zijn.
                except:
                    logging.exception("failed to run module " + module)
        except:
            logging.exception("failed to start run of modules for " + str(properties))

def connect():
    """connect to the broker"""
    global channel
    credentials = pika.PlainCredentials(settings.brokerUser, settings.brokerPwd)
    connection = pika.BlockingConnection(pika.ConnectionParameters(settings.broker, credentials=credentials, virtual_host="att-vhost"))
    channel = connection.channel()
    #channel.exchange_declare(exchange='outbound',type='topic', durable=True)  already exists


def process():
    """consume messages from the queue and execute the rules
    Note: this starts a new thread, so it is a none blocking call.
    """
    print(' [*] Waiting for messages.')
    mq_recieve_thread = threading.Thread(target=channel.start_consuming)
    mq_recieve_thread.start()


def subscribeTo(topic, callbackObj):
    """
    subscribe to the topic so that the callback function in the callback object will be called.
    :param topic:
    :param callbackObj:
    :return:
    """
    callbackObj.queue = channel.queue_declare(exclusive=True)
    queue_name = callbackObj.queue.method.queue
    channel.queue_bind(exchange='outbound', queue=queue_name, routing_key=topic)
    channel.basic_qos(prefetch_count=1)  # make certain that we only receive 1 message at a time
    channel.basic_consume(callbackObj.callback, queue=queue_name, no_ack=True)
    logging.info("subscribed to {}".format(topic))