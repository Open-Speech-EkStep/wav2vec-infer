python examples/speech_recognition/infer.py .<path> --task audio_pretraining \
	--nbest 1 --path <path>/checkpoint_best.pt --gen-subset test --results-path ./prep_scripts/<path>/transcriptions --w2l-decoder viterbi --lm-weight 2 --word-score -1 --sil-weight 0 --criterion ctc --labels ltr --max-tokens 6400000 \
	--post-process letter
