# set the project root directory as the static folder, you can set others.
import json
import os
import threading
import time
import wave

import grpc
from flask import Flask, request
from flask import render_template
from flask_socketio import SocketIO, emit

from audio_grpc_client import StreamRecognitionClient, EventClient
from audio_to_text_pb2 import Message
from audio_to_text_pb2_grpc import RecognizeStub

# creates a Flask application, named app
app = Flask(__name__)
socket_io = SocketIO(app, cors_allowed_origins="*")


def _run_client(address, recognition_client, event_client):
    with grpc.insecure_channel(address) as channel:
        print("connected to grpc")
        stub = RecognizeStub(channel)
        event_client.set_stub(stub)
        responses = stub.recognize_audio(recognition_client)
        for resp in responses:
            recognition_client.add_response(resp)


def write_wave_to_file(file_name, audio):
    with wave.open(file_name, 'wb') as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(16000.0)
        file.writeframes(audio)
    return os.path.join(os.getcwd(), file_name)


mic_ids = []


def make_message(audio, user, speaking, language='en'):
    print(user, speaking, language)
    return Message(
        audio=audio,
        user=str(user),
        language=language,
        speaking=speaking
    )


@socket_io.on('mic_data')
def mic_data(chunk, language, speaking):
    global mic_ids
    sid = request.sid

    msg = make_message(chunk, sid, speaking, language)
    print(sid, "message sent to grpc", speaking)
    msg_id = str(int(time.time() * 1000.0)) + str(sid)
    response = recognition_client_mic.recognize(msg, msg_id)
    message = json.loads(response.transcription)
    _id = message["id"]
    if _id in mic_ids:
        return
    mic_ids.append(_id)
    is_success = message["success"]
    if not is_success:
        return

    emit('response', message['transcription'], room=response.user)
    print(response)


@socket_io.on('start')
def start_event():
    event_client.emit_start(request.sid)

@socket_io.on('language_reset')
def language_reset():
    event_client.emit_language_reset(request.sid)

@socket_io.on('end')
def end_event():
    event_client.emit_end(request.sid)


@socket_io.on('disconnect')
def test_disconnect():
    event_client.emit_disconnect(request.sid)

@socket_io.on('connect')
def connect():
    emit('id', request.sid, room=request.sid)


@app.route("/")
def index():
    return render_template('index.html')


if __name__ == "__main__":
    recognition_client_mic = StreamRecognitionClient()
    event_client = EventClient()
    address="localhost:55102"
    mic_client_thread = threading.Thread(target=_run_client, args=(address, recognition_client_mic, event_client))
    mic_client_thread.start()
    socket_io.run(app, host='0.0.0.0', port=9008)
