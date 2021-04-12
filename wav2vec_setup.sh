#!/bin/bash

conda create --name fairseq python=3.7
conda activate fairseq

## For fairseq setup
# git clone https://github.com/Open-Speech-EkStep/wav2vec.git
# please use wav2vec present in this repo
cd wav2vec
pip install -e .

## install other libraries

## For Kenlm, openblas

cd ..
sudo apt-get install liblzma-dev libbz2-dev libzstd-dev libsndfile1-dev libopenblas-dev libfftw3-dev libgflags-dev libgoogle-glog-dev
sudo apt install build-essential cmake libboost-system-dev libboost-thread-dev libboost-program-options-dev libboost-test-dev libeigen3-dev zlib1g-dev libbz2-dev liblzma-dev


git clone https://github.com/kpu/kenlm.git
cd kenlm
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DKENLM_MAX_ORDER=20 -DCMAKE_POSITION_INDEPENDENT_CODE=ON
make -j16
cd ..
export KENLM_ROOT_DIR=$PWD
export USE_CUDA=0 ## for cpu



## Packages
pip install packaging soundfile


## wav2letter

git clone https://github.com/facebookresearch/wav2letter.git -b v0.2
cd wav2letter/bindings/python
pip install -e .



## Get the model

##### Ignore these models #####
# gsutil -m cp gs://ekstepspeechrecognition-dev/experiments/wav2vec2/2020_hi_3/final_custom_model.pt .
# gsutil -m cp gs://ekstepspeechrecognition-dev/experiments/wav2vec2/2020_hi_3/dict.ltr.txt .
# gsutil -m cp gs://ekstepspeechrecognition-dev/experiments/wav2vec2/2020_hi_3/test.wav .
##### Ignore these models #####

New Models are here:


Please bring your model using Custom model [script](https://github.com/Open-Speech-EkStep/vakyansh-wav2vec2-experimentation/blob/main/scripts/inference/generate_custom_model.sh) here.
#### Kindly update model paths in model_dict.json


## For Inference

pip install flask flask-cors

####### IGNORE ############
## Inference command: python wav2vec_inference.py -m ../files_hindi/final_custom_model.pt -d ../files_hindi/dict.ltr.txt  -w ../files_hindi/test.wav 
## Inference Command for server: python server.py -m ../files_hindi/final_custom_model.pt -d ../files_hindi/dict.ltr.txt 
## Test Server: curl -X POST http://0.0.0.0:8000/transcribe -H "Content-type: multipart/form-data" -F "file=@./files_hindi/test.wav"
#############################

## 20200621053251673Z_89ekede1
