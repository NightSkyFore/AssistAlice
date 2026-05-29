import torch
from transformers import AutoTokenizer, AutoModelForMaskedLM
import sys

BERT_MODELS = {
    "ZH_MIX_EN": "bert-base-multilingual-uncased",
    "EN": "bert-base-uncased",
    "JP": "tohoku-nlp/bert-base-japanese-v3"
}

def get_bert_model_id(language):
    assert language in BERT_MODELS.keys()
    return BERT_MODELS[language]

def load_bert(model_id_or_path):
    model = AutoModelForMaskedLM.from_pretrained(model_id_or_path)
    tokenizer = AutoTokenizer.from_pretrained(model_id_or_path)
    return model, tokenizer
