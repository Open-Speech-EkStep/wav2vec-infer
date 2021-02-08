from google.cloud import storage
import os
import json


def set_gcs_credentials():
    with open('credentials.json','r') as f:
        json_object = json.load(f)

    # Writing to sample.json
    with open("temp.json", "w") as outfile:
        json.dump(json_object, outfile)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'temp.json'


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket."""
    # bucket_name = "your-bucket-name"
    # source_file_name = "local/path/to/file"
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(
        "File {} uploaded to {}/{}.".format(
            source_file_name, bucket_name, destination_blob_name
        )
    )    

def upload_file(user_id, source_file, base_folder, language):
    bucket_name = "ekstepspeechrecognition-dev"

    bucket_file_path = "inference_debug/{}/{}/{}".format(user_id, language, source_file)
    source_path = base_folder+"/"+source_file

    upload_blob(bucket_name, source_path, bucket_file_path)    

