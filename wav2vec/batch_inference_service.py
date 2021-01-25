import logging
import os
from tempfile import NamedTemporaryFile
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import subprocess

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

ALLOWED_EXTENSIONS = set(['.wav', '.mp3', '.ogg', '.webm'])


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
        result = self.inference.get_inference(filename_new, language)

        if delete:
            cmd = 'rm -f {}'.format(filename_final)
            cmd2 = 'rm -f {}'.format(filename_new)
            os.system(cmd)
            os.system(cmd2)

        logging.info('File transcribed')
        res['status'] = "OK"
        res['transcription'] = result
        return jsonify(res)
 



if __name__ == "__main__":
    cwd = os.getcwd()
    inference_service = InferenceService(cwd + "/model_dict.json")
    logging.info('Server initialised')
    app.run(host='0.0.0.0', port=8000, debug=True, use_reloader=False)

