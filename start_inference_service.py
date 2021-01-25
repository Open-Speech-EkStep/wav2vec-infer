import os
import socket
import time

os.system("nohup python wav2vec/realtime_inference_service.py &")

a_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
grpc_location = ("127.0.0.1", 55102)
batch_location = ("127.0.0.1",8001)
print("Waiting for grpc server to boot up...")

while (a_socket.connect_ex(grpc_location)) != 0:
    time.sleep(3)

print("Started grpc server....")

os.system("nohup python wav2vec/batch_inference_service.py &")

print("Waiting for batch server to boot up...")
while (a_socket.connect_ex(batch_location)) != 0:
    time.sleep(3)

print("Started batch server....")

os.system("nohup python monitor_and_upload_to_bucket.py &")

print("Started monitor")

os.system("nohup npm start --prefix inference-client-website/ &")

print("Started client server...")