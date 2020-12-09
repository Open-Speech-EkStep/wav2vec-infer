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

from audio_grpc_client import RecognitionClient
from audio_to_text_pb2 import Message
from audio_to_text_pb2_grpc import RecognizeStub
# from vad_util import process_audio_by_vad

app = Flask(__name__)
socket_io = SocketIO(cors_allowed_origins="*")

client_buffers = {}
client_transcriptions = {}
client_current_language = {}
mc_counts = {}
mic_ids = []


def make_message(message, audio, _id, mic_flag="continue", language='en'):
    return Message(
        message=message,
        audio=audio,
        user=str(_id),
        mic_flag=mic_flag,
        language=language
    )


def delete_globals(sid):
    global client_buffers, client_transcriptions, client_current_language
    if sid in client_buffers:
        del client_buffers[sid]
    if sid in client_transcriptions:
        del client_transcriptions[sid]
    if sid in client_current_language:
        del client_current_language[sid]


def _run_client(grpc_ip, recognition_client):
    with grpc.insecure_channel(grpc_ip) as channel:
        print("connected to grpc")
        stub = RecognizeStub(channel)
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


# case 1: the whole chunk has voice
# case 2: the whole chunk has silence
# case 3: a bit of voice and most silence
# frames - aapaka naam kya hai -------- mera naam niresh hai --------
def preprocess(sid, chunk, is_speaking):
    global client_buffers, client_transcriptions
    if sid not in mc_counts:
        mc_counts[sid] = 1
    else:
        mc_counts[sid] += 1

    if sid not in client_buffers:
        client_buffers[sid] = chunk
    else:
        client_buffers[sid] = client_buffers[sid] + b'' + chunk
    buffer = client_buffers[sid]

    if not is_speaking:
        del client_buffers[sid]
    # prev_audio, new_audio = process_audio_by_vad(buffer)
    # client_buffers[sid] = new_audio
    # print(len(audio))
    # if len(audio) == 0:
    #     if sid in client_buffers:
    #         del client_buffers[sid]
    #     if sid in client_transcriptions:
    #         del client_transcriptions[sid]
    #     return None
    write_wave_to_file("{}_{}.wav".format(sid, mc_counts[sid]), buffer)
    return buffer


def post_process(response):
    global mic_ids, client_transcriptions, client_current_language
    message = json.loads(response.message)
    _id = message["id"]
    is_success = message["success"]
    if not is_success:
        return None, None
    if _id in mic_ids:
        return None, None
    mic_ids.append(_id)

    user = response.user

    if client_current_language[user] != response.language:
        if user in client_transcriptions:
            del client_transcriptions[user]
        return None, None

    if user not in client_transcriptions:
        client_transcriptions[user] = [message["transcription"]]
    else:
        if response.mic_flag == "end":
            client_transcriptions[user].append("")
        else:
            client_transcriptions[user][-1] = message["transcription"]
    # print(user, client_transcriptions[user])

    transcription = " ".join(
        [transcript for transcript in client_transcriptions[user] if len(transcript) != 0])

    return transcription, user


@socket_io.on('start')
def on_start_event():
    delete_globals(request.sid)


@socket_io.on('disconnect')
def on_disconnect_event():
    delete_globals(request.sid)


@socket_io.on('end')
def on_end_event():
    global client_buffers
    sid = request.sid
    if sid in client_buffers:
        del client_buffers[sid]


# identify chunk silence - not resolved
# prevent the tick sound - resolved
@socket_io.on('mic_data')
def on_mic_data_event(chunk, language, is_speaking):
    global recognition_client_mic, client_current_language
    sid = request.sid
    client_current_language[sid] = language
    mic_flag = "continuation"
    buffer = preprocess(sid, chunk, is_speaking)
    if buffer is None:
        mic_flag = "end"

    msg = make_message("mic", buffer, sid, mic_flag, language=language)
    msg_id = str(int(time.time() * 1000.0)) + str(sid)
    response = recognition_client_mic.recognize(msg, msg_id)

    transcription, user = post_process(response)
    if transcription is None or user is None:
        return

    emit('response', transcription, room=user)


@app.route("/")
def index():
    return render_template('index.html')


if __name__ == "__main__":
    recognition_client_mic = RecognitionClient()
    socket_io.init_app(app)
    mic_client_thread = threading.Thread(target=_run_client, args=('localhost:55102', recognition_client_mic))
    mic_client_thread.start()
    socket_io.run(app, host='0.0.0.0', port=9008)

# Flow 1:
#  complete chunk - response transcription show as it is
# Flow 2:
#  space separated chunks - keep appending the responses
# Flow 3:
#  split chunks - append to a buffer - keep replacing until space found
