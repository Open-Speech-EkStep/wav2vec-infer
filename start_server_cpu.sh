nohup python $PWD/ASR-Website-newe/code/server.py &
nohup python $PWD/wav2vec/server.py -m files_hindi/final_custom_model.pt -d files_hindi/dict.ltr.txt &

