import soundfile as sf
import torch.nn.functional as F
from fairseq import utils
import torch
import numpy as np
from audio_normalization import AudioNormalization
from fairseq.data import Dictionary

def get_args(lexicon_path, lm_path, BEAM=128, LM_WEIGHT=2, WORD_SCORE=-1):
    args = {}
    args['lexicon'] = lexicon_path
    args['kenlm_model'] = lm_path
    args['beam'] = BEAM
    args['beam_threshold'] = 25
    args['lm_weight'] = LM_WEIGHT
    args['word_score'] = WORD_SCORE
    args['unk_weight'] = -np.inf
    args['sil_weight'] = 0
    args['nbest'] = 1
    args['criterion'] ='ctc'
    args['labels']='ltr'
    return args

def get_results(wav_path,target_dict_path,use_cuda=False,w2v_path=None,model=None, generator = None):
    sample = dict()
    net_input = dict()
    
    normalized_audio = AudioNormalization(wav_path).loudness_normalization_effects()
    wav = np.array(normalized_audio.get_array_of_samples()).astype('float64')

    feature = get_feature(wav, 16000)
    target_dict = Dictionary.load(target_dict_path)
    
    model[0].eval()

    # generator = W2lViterbiDecoder(target_dict)

    if generator is None:
        generator = W2lViterbiDecoder(target_dict)

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

def get_feature(wav, sample_rate):
    def postprocess(feats, sample_rate):
        if feats.dim == 2:
            feats = feats.mean(-1)

        assert feats.dim() == 1, feats.dim()

        with torch.no_grad():
            feats = F.layer_norm(feats, feats.shape)
        return feats

    # wav, sample_rate = sf.read(filepath)
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



