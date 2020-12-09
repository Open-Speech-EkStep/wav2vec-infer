import json
import os
import wave
from concurrent import futures

import grpc
from audio_to_text_pb2 import Response
from audio_to_text_pb2_grpc import add_RecognizeServicer_to_server, RecognizeServicer


def write_wave_to_file(file_name, audio):
    with wave.open(file_name, 'wb') as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(16000.0)
        file.writeframes(audio)
    return os.path.join(os.getcwd(), file_name)


class RecognizeAudioServicer(RecognizeServicer):
    def __init__(self):
        # cwd = os.getcwd()
        # self.inference = InferenceService(cwd + "/model_dict.json")
        print('Model Loaded Successfully')
        self.count = 0

    def recognize_audio(self, request_iterator, context):
        for data in request_iterator:
            self.count += 1
            if data.mic_flag == "end":
                yield Response(message=json.dumps({'transcription': "", 'id': self.count, 'success': True}),
                               type=data.message,
                               user=data.user, mic_flag=data.mic_flag,
                               language=data.language)
            else:
                transcription = self.transcribe(data.audio, data.user + str(self.count), data.language)
                yield Response(message=transcription, type=data.message, user=data.user, mic_flag=data.mic_flag,
                               language=data.language)

    def transcribe(self, audio, index, language):
        name = "wave_0%s.wav" % index
        file_name = write_wave_to_file(name, audio)
        result = {'transcription': "hello", 'status': "OK"}  # self.inference.get_inference(file_name, language)
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
