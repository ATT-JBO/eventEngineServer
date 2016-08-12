__author__ = 'Jan Bogaerts'
__copyright__ = "Copyright 2016, AllThingsTalk"
__credits__ = []
__maintainer__ = "Jan Bogaerts"
__email__ = "jb@allthingstalk.com"
__status__ = "Prototype"  # "Development", or "Production"

##############################
# replace when_platform with the server version. (see: http://stackoverflow.com/questions/3012473/how-do-i-override-a-python-import)
##############################

import logging
logging.getLogger().setLevel(logging.INFO)
import sys
import att_event_engine.when_platform
del sys.modules['att_event_engine.when_platform']
sys.modules['att_event_engine.when_platform'] = __import__('when_server')
import att_event_engine.when_platform


import json
from flask import Flask, render_template, Response, request
from flask.ext.api import status



from eventEngine import EventEngine

app = Flask(__name__)
engine = EventEngine()


@app.route('/event', methods=['PUT'])
def addEvent():
    data = json.loads(request.data)
    error = engine.addDefinition(data)
    if error:      # there was an error
        return error, status.HTTP_405_METHOD_NOT_ALLOWED
    else:
        return 'ok', status.HTTP_200_OK


if __name__ == '__main__':
    engine.run()                                                    #none blocking
    app.run(host='0.0.0.0', debug=True, threaded=True, port=1000, use_reloader=False)   #blocking
