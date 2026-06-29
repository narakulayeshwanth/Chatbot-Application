import os
import io
import sys
import json
import pickle
import numpy as np
import random
import tensorflow as tf
from tensorflow.keras.models import load_model
from config import MODEL_DIR, INTENTS_FILE
import nltk
from nltk.stem import WordNetLemmatizer

lemmatizer = WordNetLemmatizer()

words = []
classes = []
model = None
intents_data = None

def load_ml_assets():
    global words, classes, model, intents_data
    try:
        words = pickle.load(open(os.path.join(MODEL_DIR, "tokenizer.pkl"), "rb"))
        classes = pickle.load(open(os.path.join(MODEL_DIR, "label_encoder.pkl"), "rb"))
        model = load_model(os.path.join(MODEL_DIR, "model.h5"))
        with open(INTENTS_FILE, "r", encoding="utf-8") as f:
            intents_data = json.load(f)
        return True
    except Exception as e:
        print(f"Failed to load ML models. Ensure train.py has run: {e}")
        return False

def clean_up_sentence(sentence):
    return [lemmatizer.lemmatize(word.lower().strip()) for word in nltk.word_tokenize(sentence)]

def bag_of_words(sentence):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words)
    for s in sentence_words:
        for i, word in enumerate(words):
            if word == s:
                bag[i] = 1
    return np.array(bag)

def predict_class(sentence):
    if not model:
        if not load_ml_assets():
            return "unknown", 0.0
            
    bow = bag_of_words(sentence)
    # Redirect stdout to prevent Keras from flushing to invalid handle in Flask thread (Windows [Errno 22])
    _old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        res = model.predict(np.array([bow]), verbose=0)[0]
    finally:
        sys.stdout = _old_stdout
    ERROR_THRESHOLD = 0.25
    results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]
    results.sort(key=lambda x: x[1], reverse=True)
    
    if results:
        tag = classes[results[0][0]]
        confidence = float(results[0][1])
        return tag, confidence
    return "unknown", 0.0

def get_ml_response(tag):
    if not intents_data:
        if not load_ml_assets():
             return "I'm having trouble accessing my local memory right now."
        
    for intent in intents_data["intents"]:
        if intent["tag"] == tag:
            return random.choice(intent["responses"])
    return "I'm not exactly sure what to respond to that."
