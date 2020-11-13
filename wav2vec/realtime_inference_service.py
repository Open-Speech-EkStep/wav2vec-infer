import os
import wave
import grpc
from concurrent import futures
from audio_to_text_pb2_grpc import add_RecognizeServicer_to_server, RecognizeServicer
from audio_to_text_pb2 import Response
import time
import json
import io
import json
from inference_service import InferenceService

class RecognizeAudioServicer(RecognizeServicer):
    def __init__(self):
        cwd = os.getcwd()
        self.inference = InferenceService(cwd+"/final_custom_model.pt",cwd+"/dict.ltr.txt")
        print(' Model Loaded Successfully')
        self.count = 0

    def recognize_audio(self, request_iterator, context):
        for data in request_iterator:
            self.count+=1
            transcription, flag = self.transcribe(data.audio, data.user+str(self.count))
            if(flag):
                print(data.user, "responded")
                yield Response(message=transcription, type=data.message,user=data.user, mic_flag=data.mic_flag)

    def write_wave_to_file(self, file_name, audio):
        with wave.open(file_name,'wb') as file:
            file.setnchannels(1)
            file.setsampwidth(2)
            file.setframerate(16000.0)
            file.writeframes(audio)
        return os.path.join(os.getcwd(),file_name)

    def transcribe(self, audio, index):
        name = "wave_0%s.wav" % index
        file_name = self.write_wave_to_file(name, audio)
        result = self.inference.get_inference(file_name)
        result["id"] = index
        os.remove(file_name)
        if(result['status'] != "OK"):
            result["success"] = False
        return json.dumps(result), True

def serve():
    PORT = 55102
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    add_RecognizeServicer_to_server(RecognizeAudioServicer(),server)
    server.add_insecure_port('[::]:%d'%PORT)
    server.start()
    print("GRPC Server! Listening in port %d"%PORT)
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
