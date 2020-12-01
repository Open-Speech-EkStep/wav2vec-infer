# set the project root directory as the static folder, you can set others.
import grpc
import threading
import json
from flask import Flask, request
from flask import render_template

from audio_to_text_pb2_grpc import RecognizeStub
from audio_to_text_pb2 import Message
from flask_socketio import SocketIO, emit
from audio_grpc_client import RecognitionClient
import time
import requests
# creates a Flask application, named app
app = Flask(__name__)
socketio = SocketIO(app,cors_allowed_origins="*",resource="ssocket.io")
client_buffers = {}
client_transcriptions = {}
client_curr_langs= {}
client_zoom_url = {}

def make_message(message,audio, id, mic_flag = "continue", language = 'en'):
    return Message(
        message=message,
        audio=audio,
        user=str(id),
        mic_flag=mic_flag,
        language=language
    )

def send_to_zoom(sid, url, seq, transcription):
    x = requests.post("{}&seq={}".format(url,seq), data = transcription, headers={
        'Content-Type':'text/plain'
    })
    print(sid, x.text)

def _run_client(address, recognition_client):
    with grpc.insecure_channel("localhost:55102") as channel:
        print("connected to grpc")
        stub = RecognizeStub(channel)
        responses = stub.recognize_audio(recognition_client)
        for resp in responses:
            recognition_client.add_response(resp)


@app.route("/")
def index():
        return render_template('index.html')

def delete_globals(sid):
    global client_buffers, client_transcriptions, client_curr_langs, client_zoom_url
    if sid in client_buffers:
        del client_buffers[sid]
    if sid in client_transcriptions:
        del client_transcriptions[sid]
    if sid in client_curr_langs:
        del client_curr_langs[sid]
    if sid in client_zoom_url:
        del client_zoom_url[sid]

@socketio.on('disconnect')
def test_disconnect():
    delete_globals(request.sid)

@socketio.on('end')
def end_event(json):
    global client_buffers
    sid = request.sid
    if sid in client_buffers:
        del client_buffers[sid]

@socketio.on('zoom_url')
def zoom_url_event(url):
    global client_zoom_url
    sid = request.sid
    client_zoom_url[sid] = {"url":url, "seq":1}
        

@socketio.on('start')
def start_event(json):
    delete_globals(request.sid)

mic_ids = []

@socketio.on('mic_data')
def mic_data(chunk, speaking, language):
    global client_buffers, client_curr_langs
    sid = request.sid
    client_curr_langs[sid] = language
    mic_flag = "replace"
    if(sid not in client_buffers):
        client_buffers[sid] = chunk
    else:
        client_buffers[sid] = client_buffers[sid]+b''+chunk[100:]
    buffer = client_buffers[sid]

    if (not speaking) or (len(client_buffers[sid]) >= 102400):
        if sid in client_buffers:
            del client_buffers[sid]
        mic_flag = "append"

    msg = make_message("mic",buffer, sid, mic_flag, language= language)
    print(sid, "message sent to grpc")
    msg_id = str(int(time.time()*1000.0))+str(sid)
    response = recognition_client_mic.recognize(msg, msg_id)
    message = json.loads(response.message)
    id = message["id"]
    if id in mic_ids:
        return
    mic_ids.append(id)
    is_success = message["success"]
    if not is_success:
        # emit('unidentified', "Sentence not recognized by model", room=response.user)
        return
    # emit('unidentified', "", room=response.user)
    if response.user not in client_transcriptions: client_transcriptions[response.user] = ""
    print(response.user, message["transcription"])
    if client_curr_langs[response.user] != response.language:
        if response.user in client_transcriptions:
            del client_transcriptions[response.user]
        return
    transcription = client_transcriptions[response.user] +" "+message["transcription"]
    if response.mic_flag == "append":
        client_transcriptions[response.user] = transcription      
      
    #emit('response', {"language": response.language, "transcription":transcription}, room=sid)

    if response.user in client_zoom_url:
        global client_zoom_url
        values = client_zoom_url[response.user]
        url = values["url"]
        seq = values["seq"]
        values["seq"] = seq+1
        client_zoom_url = values
        send_to_zoom(response.user,url,seq, transcription)
    emit('response', transcription, room=response.user)    
id_dict = []

@socketio.on('file_data')
def file_data(chunk, language):
    global id_dict
    sid = request.sid
    msg_id = str(int(time.time()*1000.0))+str(sid)
    msg = make_message("file",chunk[100:], sid, "append", language=language)
    print(sid, "received chunk")
    response = recognition_client_file.recognize(msg, msg_id)
    message = json.loads(response.message)
    print(sid, "respons received")
    id = message["id"]
    is_success = message["success"]
    if id in id_dict or not is_success:
        print("id already present", is_success)
        return
    id_dict.append(id)
    transcription = message["transcription"]
    print(sid, "emitted res")
    emit('file_upload_response', transcription, room=sid)


if __name__ == "__main__":
    global recognition_client_mic, recognition_client_file
    # recognition_client_mic = RecognitionClient()
   #recognition_client_file = RecognitionClient()
    # mic_client_thread = threading.Thread(target=_run_client, args=('localhost:55102', recognition_client_mic))
    # mic_client_thread.start()
   #file_client_thread = threading.Thread(target=_run_client, args=('localhost:55102', recognition_client_file))
   #file_client_thread.start()
    socketio.run(app, host='0.0.0.0', port=9008)
        

