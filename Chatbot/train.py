import json
import numpy as np
import pickle
import os
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.optimizers import Adam
import nltk
from nltk.stem import WordNetLemmatizer

nltk.download('punkt')
nltk.download('wordnet')
lemmatizer = WordNetLemmatizer()

from config import INTENTS_FILE, MODEL_DIR

def clean_up_word(word):
    return lemmatizer.lemmatize(word.lower().strip())

def train():
    with open(INTENTS_FILE, "r", encoding="utf-8") as f:
        intents = json.load(f)

    words = []
    classes = []
    documents = []
    
    # Very rudimentary tokenization/bag of words logic to keep it dependency-light
    for intent in intents["intents"]:
        for pattern in intent["patterns"]:
            # Tokenize using NLTK
            w = [clean_up_word(word) for word in nltk.word_tokenize(pattern)]
            words.extend(w)
            documents.append((w, intent["tag"]))
            if intent["tag"] not in classes:
                classes.append(intent["tag"])

    words = sorted(list(set(words)))
    classes = sorted(list(set(classes)))

    training = []
    output_empty = [0] * len(classes)

    for doc in documents:
        bag = []
        pattern_words = doc[0]
        for w in words:
            bag.append(1) if w in pattern_words else bag.append(0)

        output_row = list(output_empty)
        output_row[classes.index(doc[1])] = 1
        training.append([bag, output_row])

    # Convert to array
    training = np.array(training, dtype=object)
    
    train_x = np.array([x[0] for x in training])
    train_y = np.array([x[1] for x in training])

    print("Building model...")
    model = Sequential()
    model.add(Dense(128, input_shape=(len(train_x[0]),), activation="relu"))
    model.add(Dropout(0.5))
    model.add(Dense(64, activation="relu"))
    model.add(Dropout(0.5))
    model.add(Dense(len(train_y[0]), activation="softmax"))

    model.compile(loss="categorical_crossentropy", optimizer="adam", metrics=["accuracy"])

    print("Training model... (Limited to 50 epochs for efficiency)")
    model.fit(train_x, train_y, epochs=50, batch_size=5, verbose=1)
    
    if not os.path.exists(MODEL_DIR):
         os.makedirs(MODEL_DIR)

    model.save(os.path.join(MODEL_DIR, "model.h5"))
    pickle.dump(words, open(os.path.join(MODEL_DIR, "tokenizer.pkl"), "wb"))
    pickle.dump(classes, open(os.path.join(MODEL_DIR, "label_encoder.pkl"), "wb"))
    
    print("Training complete! Model and encoders serialized.")

if __name__ == "__main__":
    train()
