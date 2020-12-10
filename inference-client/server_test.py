# set the project root directory as the static folder, you can set others.
import audioop
import json
import math
import os
import time
import wave
from collections import deque

import grpc
import pyaudio
from flask import Flask, request
from flask import render_template
from flask_socketio import SocketIO, emit

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


LANG_CODE = 'en-US'  # Language to use
# CHUNK = 1024
# Microphone stream config.
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
THRESHOLD = 2500  # The threshold intensity that defines silence
# and noise signal (an int. lower than THRESHOLD is silence).

SILENCE_LIMIT = 1  # Silence limit in seconds. The max ammount of seconds where
# only silence is recorded. When this time passes the
# recording finishes and the file is delivered.

PREV_AUDIO = 0.5  # Previous audio (in seconds) to prepend. When noise


def listen_for_speech(chunk, threshold=THRESHOLD, num_phrases=-1):
    audio2send = []
    chunk_size = len(chunk)
    print("chunk_size", chunk_size)
    cur_data = ''  # current chunk  of audio data
    rel = RATE / chunk_size
    slid_win = deque(maxlen=int(SILENCE_LIMIT * rel)+1)
    # Prepend audio from 0.5 seconds before noise was detected
    prev_audio = deque(maxlen=int(PREV_AUDIO * rel)+1)
    started = False
    n = num_phrases
    response = []
    print("starting")

    while num_phrases == -1 or n > 0:
        cur_data = chunk  # stream.read(chunk_size)
        slid_win.append(math.sqrt(abs(audioop.avg(cur_data, 4))))
        print('slide', slid_win)
        if sum([x > THRESHOLD for x in slid_win]) > 0:
            if not started:
                print("Starting record of phrase")
                started = True
            audio2send.append(cur_data)
        elif started is True:
            print("Finished")
            # The limit was reached, finish capture and deliver.
            filename = save_speech(list(prev_audio) + audio2send)
            # Send file to Google and get response
            r = stt(filename)
            if num_phrases == -1:
                print("Response", r)
            else:
                response.append(r)
            # Remove temp file. Comment line to review.
            os.remove(filename)
            # Reset all
            started = False
            slid_win = deque(maxlen=int(SILENCE_LIMIT * rel)+1)
            prev_audio = deque(maxlen=int(0.5 * rel)+1)
            audio2send = []
            n -= 1
            print("Listening ...")
        else:
            prev_audio.append(cur_data)

    print("* Done recording")
    # stream.close()
    # p.terminate()

    return response


def save_speech(data):
    """ Saves mic data to temporary WAV file. Returns filename of saved
        file """

    filename = 'output_' + str(int(time.time()))
    # writes data to WAV file
    data = ''.join(data)
    wf = wave.open(filename + '.wav', 'wb')
    wf.setnchannels(1)
    wf.setframerate(16000.0)  # TODO make this value a function parameter?
    wf.writeframes(data)
    wf.close()
    return filename + '.wav'


def stt(filename):
    return filename


def preprocess(sid, chunk, is_speaking):
    listen_for_speech(chunk)


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
    print("emitted")
    global recognition_client_mic, client_current_language
    sid = request.sid
    client_current_language[sid] = language
    mic_flag = "continuation"
    preprocess(sid, chunk, is_speaking)
    # if buffer is None:
    #     mic_flag = "end"
    #
    # msg = make_message("mic", buffer, sid, mic_flag, language=language)
    # msg_id = str(int(time.time() * 1000.0)) + str(sid)
    # response = recognition_client_mic.recognize(msg, msg_id)
    #
    # transcription, user = post_process(response)
    # if transcription is None or user is None:
    #     return

    emit('response', "hello", room=sid)


@app.route("/")
def index():
    return render_template('index.html')


if __name__ == "__main__":
    # recognition_client_mic = RecognitionClient()
    socket_io.init_app(app)
    # mic_client_thread = threading.Thread(target=_run_client, args=('localhost:55102', recognition_client_mic))
    # mic_client_thread.start()
    socket_io.run(app, host='0.0.0.0', port=9008)

# Flow 1:
#  complete chunk - response transcription show as it is
# Flow 2:
#  space separated chunks - keep appending the responses
# Flow 3:
#  split chunks - append to a buffer - keep replacing until space found
