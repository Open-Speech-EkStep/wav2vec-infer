import os
import socket
import time

os.system("nohup python wav2vec/realtime_inference_service.py &")

grpc_location = ("127.0.0.1", 55102)
batch_location = ("127.0.0.1", 8001)
print("Waiting for grpc server to boot up...")

a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while (a_socket.connect_ex(grpc_location)) != 0:
    time.sleep(3)
a_socket.close()
print("Started grpc server....")

os.system("nohup npm start --prefix inference-client-website/ &")

print("Started client server...")
