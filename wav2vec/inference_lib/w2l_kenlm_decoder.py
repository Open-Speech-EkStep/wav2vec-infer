from wav2letter.common import create_word_dict, load_words
from wav2letter.decoder import DecoderOptions,KenLM,SmearingMode,Trie,LexiconDecoder
import torch
from inference_lib.w2l_decoder import W2lDecoder

class W2lKenLMDecoder(W2lDecoder):
    def __init__(self,args,tgt_dict):
        super().__init__(tgt_dict)
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
        start_state = self.lm.start(False)
        for i, (word, spellings) in enumerate(self.lexicon.items()):
            word_idx = self.word_dict.get_index(word)
            _, score = self.lm.score(start_state, word_idx)
            for spelling in spellings:
                spelling_idxs = [tgt_dict.index(token) for token in spelling]
                assert (
                    tgt_dict.unk() not in spelling_idxs
                ), f"{spelling} {spelling_idxs}"
                self.trie.insert(spelling_idxs, word_idx, score)
        self.trie.smear(SmearingMode.MAX)
        self.decoder_opts = DecoderOptions(
            args['beam'],
            int(getattr(args, "beam_size_token", len(tgt_dict))),
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