import json
import os
import time
import wave
from concurrent import futures

import grpc

from audio_to_text_pb2 import Response
from audio_to_text_pb2_grpc import add_RecognizeServicer_to_server, RecognizeServicer
from inference_service import W2lDecoder, W2lViterbiDecoder, Wav2VecCtc, InferenceService


class RecognizeAudioServicer(RecognizeServicer):
    def __init__(self):
        cwd = os.getcwd()
        self.inference = InferenceService(cwd + "/model_dict.json")
        print('Model Loaded Successfully')
        self.count = 0
        # self.file_names = {}
        self.client_buffers = {}

    def recognize_audio(self, request_iterator, context):
        for data in request_iterator:
            self.count += 1
            buffer = self.preprocess(data)
            transcription = self.transcribe(buffer, data.user + str(self.count), data.language)
            yield Response(transcription=transcription, user=data.user, action="",
                           language=data.language)

    def preprocess(self, data):
        file_name = "{}_{}.wav".format(data.user, int(time.time() * 1000))
        # if data.user in self.file_names:
        #     audio_file_name = self.file_names[data.user]
        #     with open(audio_file_name, mode='rb') as f:
        #         audio = f.read() + b'' + audio
        # else:
        #     audio_file_name = "_{}.wav".format(data.user)
        #     self.file_names[data.user] = audio_file_name
        # if not data.speaking:
        #     os.system('rm {}'.format(audio_file_name))
        # else:
        #     with open(audio_file_name, mode='bx') as f:
        #         f.write(audio)
        # return self.write_wave_to_file(file_name, audio)

        if data.user in self.client_buffers:
            self.client_buffers[data.user] += data.audio
        else:
            self.client_buffers[data.user] = data.audio

        buffer = self.client_buffers[data.user]

        if not data.speaking:
            del self.client_buffers[data.user]

        return buffer

    def write_wave_to_file(self, file_name, audio):
        with wave.open(file_name, 'wb') as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(16000.0)
            file.writeframes(audio)
        return os.path.join(os.getcwd(), file_name)

    def transcribe(self, buffer, index, language):
        file_name = self.write_wave_to_file(index + ".wav", buffer)
        result = self.inference.get_inference(file_name, language)
        print("result", result)
        result["id"] = index
        os.remove(file_name)
        if result['status'] != "OK":
            result["success"] = False
        else:
            result["success"] = True
        return json.dumps(result)


def serve():
    port = 55102
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_RecognizeServicer_to_server(RecognizeAudioServicer(), server)
    server.add_insecure_port('[::]:%d' % port)
    server.start()
    print("GRPC Server! Listening in port %d" % port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
