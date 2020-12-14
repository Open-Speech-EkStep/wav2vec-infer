import torch
import logging
import argparse
import soundfile as sf
import torch.nn.functional as F
import itertools as it
from fairseq import utils
from fairseq.models import BaseFairseqModel
from fairseq.data import Dictionary
from fairseq.models.wav2vec.wav2vec2_asr import base_architecture, Wav2VecEncoder
from wav2letter.common import create_word_dict, load_words
from wav2letter.decoder import CriterionType,DecoderOptions,KenLM,LM,LMState,SmearingMode,Trie,LexiconDecoder
from wav2letter.criterion import CpuViterbiPath, get_data_ptr_as_bytes
import numpy as np
from tqdm import tqdm

import os
from tempfile import NamedTemporaryFile
import torch
from flask import Flask, request, jsonify
import sys
from flask_cors import CORS, cross_origin
import json

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

ALLOWED_EXTENSIONS = set(['.wav', '.mp3', '.ogg', '.webm'])

#cs = ConfigStore.instance()
#cs.store(name="config", node=ServerConfig)



class Wav2VecCtc(BaseFairseqModel):
    def __init__(self, w2v_encoder, args):
        super().__init__()
        self.w2v_encoder = w2v_encoder
        self.args = args

    def upgrade_state_dict_named(self, state_dict, name):
        super().upgrade_state_dict_named(state_dict, name)
        return state_dict

    @classmethod
    def build_model(cls, args, target_dict):
        """Build a new model instance."""
        base_architecture(args)
        w2v_encoder = Wav2VecEncoder(args, target_dict)
        return cls(w2v_encoder, args)

    def get_normalized_probs(self, net_output, log_probs):
        """Get normalized probabilities (or log probs) from a net's output."""
        logits = net_output["encoder_out"]
        if log_probs:
            return utils.log_softmax(logits.float(), dim=-1)
        else:
            return utils.softmax(logits.float(), dim=-1)

    def forward(self, **kwargs):
        x = self.w2v_encoder(**kwargs)
        return x

class W2lDecoder(object):
    def __init__(self, tgt_dict):
        self.tgt_dict = tgt_dict
        self.vocab_size = len(tgt_dict)
        self.nbest = 1

        self.criterion_type = CriterionType.CTC
        self.blank = (
            tgt_dict.index("<ctc_blank>")
            if "<ctc_blank>" in tgt_dict.indices
            else tgt_dict.bos()
        )
        self.asg_transitions = None

    def generate(self, models, sample, **unused):
        """Generate a batch of inferences."""
        # model.forward normally channels prev_output_tokens into the decoder
        # separately, but SequenceGenerator directly calls model.encoder
        encoder_input = {
            k: v for k, v in sample["net_input"].items() if k != "prev_output_tokens"
        }
        emissions = self.get_emissions(models, encoder_input)
        return self.decode(emissions)

    def get_emissions(self, models, encoder_input):
        """Run encoder and normalize emissions"""
        # encoder_out = models[0].encoder(**encoder_input)
        encoder_out = models[0](**encoder_input)
        if self.criterion_type == CriterionType.CTC:
            emissions = models[0].get_normalized_probs(encoder_out, log_probs=True)

        return emissions.transpose(0, 1).float().cpu().contiguous()

    def get_tokens(self, idxs):
        """Normalize tokens by handling CTC blank, ASG replabels, etc."""
        idxs = (g[0] for g in it.groupby(idxs))
        idxs = filter(lambda x: x != self.blank, idxs)

        return torch.LongTensor(list(idxs))


class W2lViterbiDecoder(W2lDecoder):
    def __init__(self, tgt_dict):
        super().__init__(tgt_dict)

    def decode(self, emissions):
        B, T, N = emissions.size()
        hypos = list()

        if self.asg_transitions is None:
            transitions = torch.FloatTensor(N, N).zero_()
        else:
            transitions = torch.FloatTensor(self.asg_transitions).view(N, N)

        viterbi_path = torch.IntTensor(B, T)
        workspace = torch.ByteTensor(CpuViterbiPath.get_workspace_size(B, T, N))
        CpuViterbiPath.compute(
            B,
            T,
            N,
            get_data_ptr_as_bytes(emissions),
            get_data_ptr_as_bytes(transitions),
            get_data_ptr_as_bytes(viterbi_path),
            get_data_ptr_as_bytes(workspace),
        )
        return [
            [{"tokens": self.get_tokens(viterbi_path[b].tolist()), "score": 0}] for b in range(B)
        ]



class W2lKenLMDecoder(W2lDecoder):
    def __init__(self, args, tgt_dict):
        super().__init__( tgt_dict)

        self.silence = (
            tgt_dict.index("<ctc_blank>")
            if "<ctc_blank>" in tgt_dict.indices
            else tgt_dict.bos()
        )
        self.lexicon = load_words(args['lexicon'])
        self.word_dict = create_word_dict(self.lexicon)
        self.unk_word = self.word_dict.get_index("<unk>")

        self.lm = KenLM(args['kenlm_model'], self.word_dict)
        self.trie = Trie(self.vocab_size, self.silence)
        print('h1')
        print(len(self.lexicon.items()))
        start_state = self.lm.start(False)
        for i, (word, spellings) in enumerate(self.lexicon.items()):
            print(i, word, spellings)
            word_idx = self.word_dict.get_index(word)
            _, score = self.lm.score(start_state, word_idx)
            for spelling in spellings:
                spelling_idxs = [tgt_dict.index(token) for token in spelling]
                assert (
                    tgt_dict.unk() not in spelling_idxs
                ), f"{spelling} {spelling_idxs}"
                self.trie.insert(spelling_idxs, word_idx, score)
        self.trie.smear(SmearingMode.MAX)
        print('h2')

        if args['beam_size_token']:
            argument_2 = int(args['beam_size_token'])
        else:
            argument_2 = int(len(tgt_dict))

        self.decoder_opts = DecoderOptions(
            args['beam'],
            argument_2,
            args['beam_threshold'],
            args['lm_weight'],
            args['word_score'],
            args['unk_weight'],
            args['sil_weight'],
            0,
            False,
            self.criterion_type,
        )

        if self.asg_transitions is None:
            N = 768
            # self.asg_transitions = torch.FloatTensor(N, N).zero_()
            self.asg_transitions = []

        self.decoder = LexiconDecoder(
            self.decoder_opts,
            self.trie,
            self.lm,
            self.silence,
            self.blank,
            self.unk_word,
            self.asg_transitions,
            False,
        )

    def decode(self, emissions):
        B, T, N = emissions.size()
        hypos = []
        print('Decoding with Kenlm')
        for b in range(B):
            emissions_ptr = emissions.data_ptr() + 4 * b * emissions.stride(0)
            results = self.decoder.decode(emissions_ptr, T, N)

            nbest_results = results[: self.nbest]
            hypos.append(
                [
                    {
                        "tokens": self.get_tokens(result.tokens),
                        "score": result.score,
                        "words": [
                            self.word_dict.get_entry(x) for x in result.words if x >= 0
                        ],
                    }
                    for result in nbest_results
                ]
            )
        return hypos



def get_results(wav_path,target_dict_path,use_cuda=False,w2v_path=None,model=None):
    sample = dict()
    net_input = dict()

    feature = get_feature(wav_path)
    target_dict = Dictionary.load(target_dict_path)
    
    model[0].eval()

    #generator = W2lViterbiDecoder(target_dict)
    net_input["source"] = feature.unsqueeze(0)

    padding_mask = torch.BoolTensor(net_input["source"].size(1)).fill_(False).unsqueeze(0)

    net_input["padding_mask"] = padding_mask
    sample["net_input"] = net_input
    sample = utils.move_to_cuda(sample) if use_cuda else sample
    with torch.no_grad():
        hypo = generator.generate(model, sample, prefix_tokens=None)
    hyp_pieces = target_dict.string(hypo[0][0]["tokens"].int().cpu())
    text=post_process(hyp_pieces, 'letter')
    return text

def get_feature(filepath):
    def postprocess(feats, sample_rate):
        if feats.dim == 2:
            feats = feats.mean(-1)

        assert feats.dim() == 1, feats.dim()

        with torch.no_grad():
            feats = F.layer_norm(feats, feats.shape)
        return feats

    wav, sample_rate = sf.read(filepath)
    feats = torch.from_numpy(wav).float()
    feats = postprocess(feats, sample_rate)
    return feats

def post_process(sentence: str, symbol: str):
    if symbol == "sentencepiece":
        sentence = sentence.replace(" ", "").replace("\u2581", " ").strip()
    elif symbol == 'wordpiece':
        sentence = sentence.replace(" ", "").replace("_", " ").strip()
    elif symbol == 'letter':
        sentence = sentence.replace(" ", "").replace("|", " ").strip()
    elif symbol == "_EOW":
        sentence = sentence.replace(" ", "").replace("_EOW", " ").strip()
    elif symbol is not None and symbol != 'none':
        sentence = (sentence + " ").replace(symbol, "").rstrip()
    return sentence


def load_gpu_model(model_path):
    return torch.load(model_path,map_location=torch.device("cuda"))

def load_cpu_model(model_path):
        return torch.load(model_path,map_location=torch.device("cpu"))


#import wav

import cgi
import contextlib
import wave

import os
import subprocess

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

        dict_path = "/".join(model_path.split('/')[:-1]) + '/dict.ltr.txt'

        if cuda:
            gpu_model = load_gpu_model(model_path)
            result = get_results( filename_new , dict_path,cuda,model=gpu_model)
        else:
            cpu_model = load_cpu_model(model_path)
            result = get_results( filename_new , dict_path,cuda,model=cpu_model)

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
    parser = argparse.ArgumentParser(description='Run')
    parser.add_argument('-m', '--model-path', type=str, required=True, help="Model path")
    parser.add_argument('-c', '--cuda',default=False, type=bool, help="CUDA path")
    args_local = parser.parse_args()
    global model_dict, cuda, generator

    with open(args_local.model_path) as f:
        model_dict = json.load(f)

    dict_path = '/home/harveen.chadha/deployed_models/hi/dict.ltr.txt'

    args_lm = {}
    args_lm['lexicon'] = '/home/harveen.chadha/github/lm/LM_v2/lexicon.lst'
    args_lm['kenlm_model'] = '/home/harveen.chadha/github/lm/LM_v2/lm.binary'
    args_lm['beam'] = 128
    args_lm['beam_threshold'] = 25
    args_lm['lm_weight'] = 0.4
    args_lm['word_score'] = 0.3
    args_lm['unk_weight'] = -np.inf
    args_lm['sil_weight'] = 0

    print(args_lm)
    print('heere')
    #print(args_lm.lexicon)
    print('heere 2')
    target_dict = Dictionary.load(dict_path)
    generator = W2lKenLMDecoder(args_lm, target_dict)

    cuda = args_local.cuda
    print(cuda) 
    logging.info('Server initialised')
    app.run(host='0.0.0.0', port=8020, debug=True, use_reloader=False)

