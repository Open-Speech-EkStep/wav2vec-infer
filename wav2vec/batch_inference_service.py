import logging
import os
from tempfile import NamedTemporaryFile
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import subprocess
from google.cloud import storage
import json

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
from inference_service import InferenceService, Wav2VecCtc, W2lViterbiDecoder, W2lDecoder, W2lKenLMDecoder

ALLOWED_EXTENSIONS = set(['.wav', '.mp3', '.ogg', '.webm'])

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    # bucket_name = "your-bucket-name"
    # source_blob_name = "storage-object-name"
    # destination_file_name = "local/path/to/file"

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    blob.download_to_filename(destination_file_name)

    logging.info(
        "Blob {} from Bucket {} downloaded to {}.".format(
            source_blob_name, bucket_name, destination_file_name
        )
    )


def check_blob(bucket_name, file_prefix):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    stats = storage.Blob(bucket=bucket, name=file_prefix).exists(storage_client)
    return stats


@app.route('/transcribe', methods=['POST'])
@cross_origin()
def parse_transcription():
    if request.method == 'POST':
        res = {}
        language = request.args.get("lang")

        model_path = model_dict[language]
        
        file = request.files['file']
        filename = file.filename
        _, file_extension = os.path.splitext(filename)

        if file_extension.lower() not in ALLOWED_EXTENSIONS:
            res['status'] = "error"
            res['message'] = "{} is not supported format.".format(file_extension)
            return jsonify(res)
       
        filename_final = ''
        with NamedTemporaryFile(suffix=file_extension,delete=False) as tmp_saved_audio_file:
            file.save(tmp_saved_audio_file.name)
            filename_final = tmp_saved_audio_file.name
        filename_local = filename_final.split('/')[-1][:-4]
        filename_new = '/tmp/'+filename_local+'_16.wav'
        delete = True
        
        subprocess.call(["sox {} -r {} -b 16 -c 1 {}".format(filename_final, str(16000), filename_new)], shell=True)

        # write model infer code here
        result = inference_service.get_inference(filename_new, language)

        if delete:
            cmd = 'rm -f {}'.format(filename_final)
            cmd2 = 'rm -f {}'.format(filename_new)
            os.system(cmd)
            os.system(cmd2)

        logging.info('File transcribed')
        res['status'] = "OK"
        res['transcription'] = result
        return jsonify(res)
 
@app.route('/transcribe_gcp', methods=['POST'])
@cross_origin()
def parse_transcription_gcp():
    if request.method == 'POST':
        res = {}
        language = request.args.get("lang")
        res = {}
        audio_path = request.form['audio_path']
        audio_path = audio_path.replace('https://storage.googleapis.com/','')
        audio_path_parts = audio_path.split('/')
        bucket = audio_path_parts[0]
        file_path = "/".join(audio_path_parts[1:])
        file_name = audio_path_parts[-1]
        local_file_path = "downloads/"+file_name
        ext = local_file_path[-4:]
        reformatted_file_path = local_file_path[:-4]+"_16"+ext

        if check_blob(bucket, file_path):
            download_blob(bucket, file_path, local_file_path)
        else:
            res['status'] = "NOT OK"
            return jsonify(res), 500

        subprocess.call(["sox {} -r {} -b 16 -c 1 {}".format(local_file_path, str(16000), reformatted_file_path)], shell=True)

        result = inference_service.get_inference(reformatted_file_path, language)

        os.remove(local_file_path)
        os.remove(reformatted_file_path)

        res['status'] = result['status']
        res['transcription'] = result['transcription']
        return jsonify(res)



if __name__ == "__main__":
    cwd = os.getcwd()
    if not os.path.exists("downloads"):
        os.system("mkdir downloads")
    inference_service = InferenceService(cwd + "/model_dict.json")
    logging.info('Server initialised')
    app.run(host='0.0.0.0', port=8001, use_reloader=False)

