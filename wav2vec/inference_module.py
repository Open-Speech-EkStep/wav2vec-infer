import json
import logging
from fairseq import utils
from fairseq.data import Dictionary
import torch
from inference_lib.utilities import get_args, get_results, load_cpu_model ,load_gpu_model
from inference_lib.w2l_kenlm_decoder import W2lKenLMDecoder
from inference_lib.wav2vec_ctc import Wav2VecCtc
from inference_lib.srt.subtitle_generator import get_srt

class InferenceService:

    def __init__(self, model_dict_path):
        self.models = {}
        self.dict_paths = {}
        self.generators = {}
        with open(model_dict_path) as f:
            model_dict = json.load(f)
        for lang, path in model_dict.items():
            if torch.cuda.is_available():
                self.cuda = True
                self.models[lang] = load_gpu_model(path)
            else:
                self.cuda = False
                self.models[lang] = load_cpu_model(path)
            parent_path = "/".join(path.split('/')[:-1])
            self.dict_paths[lang] =  parent_path + '/dict.ltr.txt'
            if lang == 'hi' or lang == 'en-IN' or lang == 'kn-lm':
                # load kenlm
                lexicon_path = parent_path + '/lexicon.lst'
                lm_path = parent_path + '/lm.binary'
                target_dict_path = parent_path + '/dict.ltr.txt'
                target_dict = Dictionary.load(target_dict_path)
                args = get_args(lexicon_path, lm_path)
                generator = W2lKenLMDecoder(args, target_dict)
                self.generators[lang] = generator
        

    def get_inference(self, file_name, language):
        generator = None
        if language == 'hi' or language == 'en-IN' or language == 'kn-lm':
            generator = self.generators[language]
        result = get_results( file_name , self.dict_paths[language],self.cuda,model=self.models[language], generator=generator)
        res = {}
        logging.info('File transcribed')
        res['status'] = "OK"
        res['transcription'] = result
        return res

    def get_srt(self, file_name, language):
        generator = None
        if language == 'hi' or language == 'en-IN' or language == 'kn-lm':
            generator = self.generators[language]
        result = get_srt(file_name=file_name, model=self.models[language], generator=generator, dict_path=self.dict_paths[language], language=language)
        res = {}
        res['status'] = "OK"
        res['srt'] = result
        return res

if __name__ == '__main__':
    inference = InferenceService("./../model_dict.json")
    # result = inference.get_inference('./../changed.wav','hi')
    result = inference.get_srt('./../changed.wav','hi')
    print(result)