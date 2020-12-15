cd wav2vec
pip install -e .

cd ..
apt-get update -y
apt-get install liblzma-dev libbz2-dev libzstd-dev libsndfile1-dev libopenblas-dev libfftw3-dev libgflags-dev libgoogle-glog-dev -y
apt install build-essential cmake libboost-system-dev libboost-thread-dev libboost-program-options-dev libboost-test-dev libeigen3-dev zlib1g-dev libbz2-dev liblzma-dev -y
apt install git -y

git clone https://github.com/kpu/kenlm.git
cd kenlm
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DKENLM_MAX_ORDER=20 -DCMAKE_POSITION_INDEPENDENT_CODE=ON
make -j16
cd ..
export KENLM_ROOT_DIR=$PWD
export USE_CUDA=0 


git clone https://github.com/facebookresearch/wav2letter.git -b v0.2
cd wav2letter/bindings/python
pip install -e .

cd ../../../..
mkdir deployed_models
gsutil -m cp -r gs://ekstepspeechrecognition-dev/deployed_models deployed_models/

python generate_model_dict.py
