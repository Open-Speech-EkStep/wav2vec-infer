import json
import os
import wave
from concurrent import futures
import time
import grpc

from audio_to_text_pb2 import Response, EventResponse 
from audio_to_text_pb2_grpc import add_RecognizeServicer_to_server, RecognizeServicer
from inference_service import InferenceService, Wav2VecCtc, W2lViterbiDecoder, W2lDecoder, W2lKenLMDecoder

class RecognizeAudioServicer(RecognizeServicer):
    def __init__(self):
        cwd = os.getcwd()
        if not os.path.exists(cwd+"/utterances"):
            os.system('mkdir utterances')
        self.inference = InferenceService(cwd + "/model_dict.json")
        print('Model Loaded Successfully')
        self.count = 0
        self.client_buffers = {}
        self.client_transcription = {}

    def recognize_audio(self, request_iterator, context):
        for data in request_iterator:
            self.count += 1
            print(data.user, "received")
            buffer, append_result, local_file_name = self.preprocess(data)
            transcription = self.transcribe(buffer, str(self.count), data, append_result, local_file_name)
            yield Response(transcription=transcription, user=data.user, action=str(append_result),
                           language=data.language)

    def clear_buffers(self, user):
        if user in self.client_buffers:
            del self.client_buffers[user]

    def clear_transcriptions(self, user):
        if user in self.client_transcription:
            del self.client_transcription[user]

    def clear_states(self, user):
        self.clear_buffers(user)
        self.clear_transcriptions(user)
        

    def disconnect(self, request, context):
        self.clear_states(request.user)
        return EventResponse(user=request.user, message="disconnected and cleared")

    def start(self, request, context):
        self.clear_states(request.user)
        return EventResponse(user=request.user, message="started")

    def end(self, request, context):
        self.clear_buffers(request.user)
        return EventResponse(user=request.user, message="ended")

    def language_reset(self, request, context):
        self.clear_states(request.user)
        return EventResponse(user=request.user, message="reset done")

    def preprocess(self, data):
        local_file_name = None
        append_result = False
        if data.user in self.client_buffers:
            self.client_buffers[data.user] += data.audio
        else:
            self.client_buffers[data.user] = data.audio

        buffer = self.client_buffers[data.user]
        # print("when", len(buffer))
        if not data.speaking:
            del self.client_buffers[data.user]
            append_result = True
            # local_file_name = "utterances/{}__{}__{}.wav".format(data.user,str(int(time.time()*1000)), data.language)
            # self.write_wave_to_file(local_file_name, buffer)
        return buffer, append_result, None

    def write_wave_to_file(self, file_name, audio):
        with wave.open(file_name, 'wb') as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(16000.0)
            file.writeframes(audio)
        return os.path.join(os.getcwd(), file_name)

    def transcribe(self, buffer, count, data, append_result, local_file_name):
        index = data.user + count
        user = data.user
        file_name = self.write_wave_to_file(index + ".wav", buffer)
        #result = {"transcription":"hello", 'status':'OK'}
        result = self.inference.get_inference(file_name, data.language)
        # print("then", len(buffer))
        if user not in self.client_transcription:
            self.client_transcription[user] = ""
        transcription = (self.client_transcription[user] + " " + result['transcription']).lstrip()
        result['transcription'] = transcription
        if append_result:
            self.client_transcription[user] = transcription
            # print("appended")
            # if local_file_name is not None:
            #     with open(local_file_name.replace(".wav",".txt"), 'w') as local_file:
            #         local_file.write(result['transcription'])
        result["id"] = index
        print(user, "responsed")
        os.remove(file_name)
        if result['status'] != "OK":
            result["success"] = False
        else:
            result["success"] = True
        return json.dumps(result)


def serve():
    port = 55102
    server = grpc.server(futures.ThreadPoolExecutor())
    add_RecognizeServicer_to_server(RecognizeAudioServicer(), server)
    server.add_insecure_port('[::]:%d' % port)
    server.start()
    print("GRPC Server! Listening in port %d" % port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
