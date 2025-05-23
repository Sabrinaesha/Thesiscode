# -*- coding: utf-8 -*-
"""hybrid_finetuned.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1U1Edl4dBZF0eKKVgrK6FLIRn9qz27fSr
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import InceptionV3, EfficientNetB0
from tensorflow.keras.applications.inception_v3 import preprocess_input as inception_preprocess
from tensorflow.keras.applications.efficientnet import preprocess_input as efficientnet_preprocess
from tensorflow.keras import layers, models, Model, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# ---- Parameters ----
IMG_HEIGHT, IMG_WIDTH = 299, 299  # Keep Inception size
BATCH_SIZE = 32
FINE_TUNE_EPOCHS = 10

# ---- Paths ----
base_dir = '/content/drive/MyDrive/my_folder'
train_dir = os.path.join(base_dir, 'train')
valid_dir = os.path.join(base_dir, 'valid')
test_dir  = os.path.join(base_dir, 'test')

# ---- Data Generator ----
datagen = ImageDataGenerator(
    rotation_range=20,
    horizontal_flip=True,
    preprocessing_function=inception_preprocess  # Using InceptionV3's preprocessing
)

train_generator = datagen.flow_from_directory(
    train_dir, target_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE, class_mode='categorical', shuffle=True)

valid_generator = datagen.flow_from_directory(
    valid_dir, target_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE, class_mode='categorical', shuffle=True)

test_generator = datagen.flow_from_directory(
    test_dir, target_size=(IMG_HEIGHT, IMG_WIDTH),
    batch_size=BATCH_SIZE, class_mode='categorical', shuffle=False)

# ---- Hybrid Model ----
input_tensor = Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3))

# InceptionV3 branch
inception_base = InceptionV3(include_top=False, weights='imagenet', input_tensor=input_tensor)
inception_output = layers.GlobalAveragePooling2D()(inception_base.output)

# EfficientNetB0 branch
efficientnet_base = EfficientNetB0(include_top=False, weights='imagenet', input_tensor=input_tensor)
efficientnet_output = layers.GlobalAveragePooling2D()(efficientnet_base.output)

# Combine both feature sets
combined = layers.concatenate([inception_output, efficientnet_output])
x = layers.Dense(256, activation='relu')(combined)
x = layers.Dropout(0.5)(x)
output = layers.Dense(train_generator.num_classes, activation='softmax')(x)

model = Model(inputs=input_tensor, outputs=output)

# ---- Compile model directly without freezing ----
model.compile(optimizer='adam',
              loss='categorical_crossentropy',
              metrics=['accuracy'])

# ---- Fine-tuning ----
model.compile(optimizer=Adam(learning_rate=1e-5),
              loss='categorical_crossentropy',
              metrics=['accuracy'])

# ---- Callbacks ----
checkpoint_path = 'best_hybrid_inception_efficientnet_finetuned.h5'
callbacks = [
    EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
    ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=3, verbose=1),
    ModelCheckpoint(filepath=checkpoint_path, monitor='val_loss', save_best_only=True, verbose=1)
]

# ---- Fine-tune the model ----
history_finetune = model.fit(
    train_generator,
    validation_data=valid_generator,
    epochs=FINE_TUNE_EPOCHS,
    callbacks=callbacks
)

# ---- Load the best model ----
model.load_weights(checkpoint_path)

# ---- Evaluate ----
test_loss, test_acc = model.evaluate(test_generator)
print("Test Accuracy after Fine-Tuning:", test_acc)

# ---- Predict & Metrics ----
predictions = model.predict(test_generator)
predicted_classes = np.argmax(predictions, axis=1)
true_classes = test_generator.classes
class_labels = list(test_generator.class_indices.keys())

print("\nClassification Report:")
print(classification_report(true_classes, predicted_classes, target_names=class_labels))

cm = confusion_matrix(true_classes, predicted_classes)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=class_labels, yticklabels=class_labels)
plt.xlabel('Predicted Class')
plt.ylabel('True Class')
plt.title('Confusion Matrix - Fine-Tuned Hybrid Model')
plt.show()

# ---- Plot Accuracy & Loss ----
plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(history_finetune.history['accuracy'], label='Train Acc')
plt.plot(history_finetune.history['val_accuracy'], label='Val Acc')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.title('Fine-Tuning Accuracy')
plt.ylim([0, 1])
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(history_finetune.history['loss'], label='Train Loss')
plt.plot(history_finetune.history['val_loss'], label='Val Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('Fine-Tuning Loss')
plt.legend()

plt.tight_layout()
plt.show()

# ---- Save Final Fine-Tuned Model ----
model.save('hybrid_inception_efficientnet_finetuned_final.h5')
from google.colab import files
files.download('hybrid_inception_efficientnet_finetuned_final.h5')