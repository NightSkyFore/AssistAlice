import re
import soundfile
import numpy as np
from tqdm import tqdm
import torch
import torch.nn as nn
import multiprocessing

# default limit threads num.
target_threads = max(2, multiprocessing.cpu_count() // 2)
target_threads = min(target_threads, 6)
torch.set_num_threads(target_threads)
torch.set_num_interop_threads(target_threads)

from .models import SynthesizerTrn
from .bert_utils import get_bert_model_id, load_bert
from .split_utils import split_sentence
from .download_utils import load_or_download_config, load_or_download_model
from .text.symbols import _symbol_to_id, language_id_map, language_tone_start_map
from .text import japanese, english, chinese_mix
from . import commons

language_module_map = {
    "ZH": chinese_mix, "JP": japanese, "EN": english, 'ZH_MIX_EN': chinese_mix
}

class TTS(nn.Module):
    def __init__(
        self, 
        language,
        device='auto',
        use_hf=True,
        config_path=None,
        ckpt_path=None,
        bert_path=None,
        num_threads=None,
        **kwargs,
    ):
        super().__init__()

        # limit core used in pytorch
        self._setup_cpu_threads(num_threads)

        # device choose
        if device == 'auto':
            device = 'cpu'
            if torch.cuda.is_available(): device = 'cuda'
            if torch.backends.mps.is_available(): device = 'mps'
        if 'cuda' in device:
            assert torch.cuda.is_available()
        self.device = device

        # load base model and config
        hps = load_or_download_config(language, use_hf=use_hf, config_path=config_path)
        self.hps = hps

        num_languages = hps.num_languages
        num_tones = hps.num_tones
        symbols = hps.symbols
        self.symbol_to_id = {s: i for i, s in enumerate(symbols)}

        model = SynthesizerTrn(
            len(symbols),
            hps.data.filter_length // 2 + 1,
            hps.train.segment_size // hps.data.hop_length,
            n_speakers=hps.data.n_speakers,
            num_tones=num_tones,
            num_languages=num_languages,
            **hps.model,
        ).to(device)
        model.eval()
        self.model = model
        checkpoint_dict = load_or_download_model(language, device, use_hf=use_hf, ckpt_path=ckpt_path)
        self.model.load_state_dict(checkpoint_dict['model'], strict=True)
        
        language = language.split('_')[0]
        self.language = 'ZH_MIX_EN' if language == 'ZH' else language # we support a ZH_MIX_EN model

        # load bert
        if not bert_path:
            # remote download model
            bert_model, tokenizer = load_bert(get_bert_model_id(self.language))
        else:
            bert_model, tokenizer = load_bert(bert_path)
        bert_model.to(device)
        bert_model.eval()
        self.bert_model = bert_model
        self.tokenizer = tokenizer
    
    def _setup_cpu_threads(self, num_threads):
        total_sys_threads = multiprocessing.cpu_count()
        if num_threads is not None:
            self.num_threads = max(1, min(num_threads, total_sys_threads))
            torch.set_num_threads(self.num_threads)

    @staticmethod
    def audio_numpy_concat(segment_data_list, sr, speed=1.):
        audio_segments = []
        for segment_data in segment_data_list:
            audio_segments += segment_data.reshape(-1).tolist()
            audio_segments += [0] * int((sr * 0.05) / speed)
        audio_segments = np.array(audio_segments).astype(np.float32)
        return audio_segments

    @staticmethod
    def split_sentences_into_pieces(text, language, quiet=False):
        texts = split_sentence(text, language_str=language)
        if not quiet:
            print(" > Text split to sentences.")
            print('\n'.join(texts))
            print(" > ===========================")
        return texts

    def tts_to_file(self, text, speaker_id, output_path=None, sdp_ratio=0.2, noise_scale=0.6, noise_scale_w=0.8, speed=1.0, pbar=None, format=None, position=None, quiet=False,):
        language = self.language
        texts = self.split_sentences_into_pieces(text, language, quiet)
        audio_list = []
        if pbar:
            tx = pbar(texts)
        else:
            if position:
                tx = tqdm(texts, position=position)
            elif quiet:
                tx = texts
            else:
                tx = tqdm(texts)
        for t in tx:
            if language in ['EN', 'ZH_MIX_EN']:
                t = re.sub(r'([a-z])([A-Z])', r'\1 \2', t)
            device = self.device
            bert, ja_bert, phones, tones, lang_ids = self.get_text_for_tts_infer(t)
            with torch.no_grad():
                x_tst = phones.to(device).unsqueeze(0)
                tones = tones.to(device).unsqueeze(0)
                lang_ids = lang_ids.to(device).unsqueeze(0)
                bert = bert.to(device).unsqueeze(0)
                ja_bert = ja_bert.to(device).unsqueeze(0)
                x_tst_lengths = torch.LongTensor([phones.size(0)]).to(device)
                del phones
                speakers = torch.LongTensor([speaker_id]).to(device)
                audio = self.model.infer(
                        x_tst,
                        x_tst_lengths,
                        speakers,
                        tones,
                        lang_ids,
                        bert,
                        ja_bert,
                        sdp_ratio=sdp_ratio,
                        noise_scale=noise_scale,
                        noise_scale_w=noise_scale_w,
                        length_scale=1. / speed,
                    )[0][0, 0].data.cpu().float().numpy()
                del x_tst, tones, lang_ids, bert, ja_bert, x_tst_lengths, speakers

            audio_list.append(audio)
        torch.cuda.empty_cache()
        audio = self.audio_numpy_concat(audio_list, sr=self.hps.data.sampling_rate, speed=speed)

        if output_path is None:
            return audio
        else:
            if format:
                soundfile.write(output_path, audio, self.hps.data.sampling_rate, format=format)
            else:
                soundfile.write(output_path, audio, self.hps.data.sampling_rate)
    
    def get_text_for_tts_infer(self, text):
        norm_text, phone, tone, word2ph = self.clean_text(text)
        phone, tone, language = self.cleaned_text_to_sequence(phone, tone)

        if self.hps.data.add_blank:
            phone = commons.intersperse(phone, 0)
            tone = commons.intersperse(tone, 0)
            language = commons.intersperse(language, 0)
            for i in range(len(word2ph)):
                word2ph[i] = word2ph[i] * 2
            word2ph[0] += 1

        if getattr(self.hps.data, "disable_bert", False):
            bert = torch.zeros(1024, len(phone))
            ja_bert = torch.zeros(768, len(phone))
        else:
            bert = self.get_bert_feature(norm_text, word2ph)
            del word2ph
            assert bert.shape[-1] == len(phone), phone

            if self.language == "ZH":
                bert = bert
                ja_bert = torch.zeros(768, len(phone))
            elif self.language in ["JP", "EN", "ZH_MIX_EN", 'KR', 'SP', 'ES', 'FR', 'DE', 'RU']:
                ja_bert = bert
                bert = torch.zeros(1024, len(phone))
            else:
                raise NotImplementedError()

        assert bert.shape[-1] == len(
            phone
        ), f"Bert seq len {bert.shape[-1]} != {len(phone)}"

        phone = torch.LongTensor(phone)
        tone = torch.LongTensor(tone)
        language = torch.LongTensor(language)
        return bert, ja_bert, phone, tone, language

    def clean_text(self, text):
        language_module = language_module_map[self.language]
        norm_text = language_module.text_normalize(text)
        phones, tones, word2ph = language_module.g2p(norm_text, self.tokenizer)
        return norm_text, phones, tones, word2ph
    
    def cleaned_text_to_sequence(self, cleaned_text, tones):
        """Converts a string of text to a sequence of IDs corresponding to the symbols in the text.
        Args:
            text: string to convert to a sequence
        Returns:
            List of integers corresponding to the symbols in the text
        """
        symbol_to_id_map = self.symbol_to_id if self.symbol_to_id else _symbol_to_id
        phones = [symbol_to_id_map[symbol] for symbol in cleaned_text]
        tone_start = language_tone_start_map[self.language]
        tones = [i + tone_start for i in tones]
        lang_id = language_id_map[self.language]
        lang_ids = [lang_id for i in phones]
        return phones, tones, lang_ids

    def get_bert_feature(self, text, word2ph):
        with torch.no_grad():
            inputs = self.tokenizer(text, return_tensors="pt")
            for i in inputs:
                inputs[i] = inputs[i].to(self.device)
            res = self.bert_model(**inputs, output_hidden_states=True)
            res = torch.cat(res["hidden_states"][-3:-2], -1)[0].cpu()
        
        word2phone = word2ph
        phone_level_feature = []
        for i in range(len(word2phone)):
            repeat_feature = res[i].repeat(word2phone[i], 1)
            phone_level_feature.append(repeat_feature)

        phone_level_feature = torch.cat(phone_level_feature, dim=0)
        return phone_level_feature.T
