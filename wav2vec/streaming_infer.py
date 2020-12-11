from wav2vec_inference import parse_transcription
from wav2vec_inference import W2lDecoder, W2lViterbiDecoder, Wav2VecCtc


from utilities import audio_int, listen_for_speech

MODEL_PATH = 'hindi.pt'
DICT_PATH = 'dict.ltr.txt'

res = listen_for_speech(2500, -1)
print(res)