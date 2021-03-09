import os, datetime
import subprocess
from pydub import AudioSegment
from extract_time_stamps_vad import extract_time_stamps
from extended_audio_infer import parse_transcription, Wav2VecCtc, W2lViterbiDecoder, W2lDecoder, W2lKenLMDecoder
import shutil
import torch
import json

DENOISER_PATH = '/home/nireshkumarr/denoiser/'

MODEL_PATH = '/home/nireshkumarr/wav2vec-infer/deployed_models/hindi/hindi.pt'
DICT_PATH = '/home/nireshkumarr/wav2vec-infer/deployed_models/hindi/dict.ltr.txt'
LEXICON_PATH = '/home/nireshkumarr/wav2vec-infer/deployed_models/hindi/lexicon.lst'
LM_PATH = '/home/nireshkumarr/wav2vec-infer/deployed_models/hindi/lm.binary' 

MODEL_DICT_PATH = '/home/nireshkumarr/wav2vec_vakyansh/model_dict.json'

def media_conversion(file_name, duration_limit=5):
    dir_name = os.path.join('/tmp', datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
    os.makedirs(dir_name)

    subprocess.call(["ffmpeg -i {} -ar {} -ac {} -bits_per_raw_sample {} -vn {}".format(file_name, 16000, 1, 16, dir_name + '/input_audio.wav')], shell=True)

    audio_file = AudioSegment.from_wav(dir_name + '/input_audio.wav')

    audio_duration_min = audio_file.duration_seconds / 60

    if audio_duration_min > 5:
        clipped_audio = audio_file[:300000]
        clipped_audio.export(dir_name + '/clipped_audio.wav', format='wav')
    else:
        audio_file.export(dir_name + '/clipped_audio.wav', format='wav')

    os.remove(dir_name + '/input_audio.wav')

    return dir_name

def noise_suppression(dir_name):

    cwd = os.getcwd()
    os.chdir(DENOISER_PATH)
    subprocess.call(["python -m denoiser.enhance --dns48 --noisy_dir {} --out_dir {} --sample_rate {} --num_workers {} --device cpu".format(dir_name, dir_name, 16000, 1)], shell=True)
    os.chdir(cwd)

def subtitle_generation(file_name, audio_threshold=5, language='hi'):
    dir_name = media_conversion(file_name, duration_limit=audio_threshold)
    noise_suppression(dir_name)
    audio_file = dir_name + '/clipped_audio_enhanced.wav'
    with open(MODEL_DICT_PATH) as f:
        model_dict = json.load(f)
    decoder = 'viterbi'
    model_path = model_dict[language]
    prefix_path = "/".join(model_path.split('/')[:-1])
    dict_path = prefix_path + "/dict.ltr.txt"
    lexicon_path = None
    lm_path = None

    if language=='hi' or language=='en-IN' or language=='kn-lm':
       
        decoder = 'kenlm'
        lexicon_path = prefix_path + "/lexicon.lst"
        lm_path = prefix_path + "/lm.binary"

    
    parse_transcription(model_path, dict_path, audio_file, torch.cuda.is_available(), decoder, lexicon_path, lm_path, language=language)
    shutil.move('subtitle_file.srt', dir_name)
    return dir_name + '/subtitle_file.srt'

#subtitle_generation('/home/nireshkumarr/test_vad/ravish_short.mp3', audio_threshold=1, language='en-IN')






