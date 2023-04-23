import time
from flask import Flask, Response, jsonify, stream_with_context
from flask_cors import CORS, cross_origin
from queue import Queue
from main import EEG_Processor, EEG_Recorder
from threading import Event
import math

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

p_value_queue = Queue()
p_value_event = Event()
p_value_event.clear()

deviceName = None

@app.route('/blockTrading')
@cross_origin()
def blockTrading():
    # with app.app_context():
    blockTrading = p_value_event.is_set()
    print(blockTrading)
    return Response(str(blockTrading), mimetype='text/plain')
    

@app.route('/device')
@cross_origin()
def device():
    # with app.app_context():
        # print(str(device))
    return Response(str(deviceName), mimetype='text/plain')


if __name__ == "__main__":
    EEG_data_queue = Queue()

    recorder = EEG_Recorder(EEG_data_queue, bufferLength=250, device=deviceName)
    processor = EEG_Processor(EEG_data_queue, path="calibration.npy", p_value_event=p_value_event, threshold=(10 * math.pow(math.e, -10)))

    recorder.start()
    processor.start()

    app.run(host='0.0.0.0', port=96)