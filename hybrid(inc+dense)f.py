# -*- coding: utf-8 -*-
"""hybrid(inc+dense)F.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1wYysaL6xPoBbmVIk4niwzFqORD56fvkw
"""

import os
import numpy as np
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import InceptionV3, DenseNet121
from tensorflow.keras.applications.inception_v3 import preprocess_input as inception_preprocess
from tensorflow.keras.applications.densenet import preprocess_input as densenet_preprocess
from tensorflow.keras import layers, models, Model, Input
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# ---- Parameters ----
IMG_HEIGHT, IMG_WIDTH = 299, 299
BATCH_SIZE = 32
EPOCHS = 20  # Updated to 20

# ---- Paths ----
base_dir = '/content/drive/MyDrive/my_folder/my_folder'
train_dir = os.path.join(base_dir, 'train')
valid_dir = os.path.join(base_dir, 'valid')
test_dir  = os.path.join(base_dir, 'test')

# ---- Data Augmentation ----
datagen = ImageDataGenerator(
    rotation_range=20,
    horizontal_flip=True,
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

# ---- Model Building ----
input_tensor = Input(shape=(IMG_HEIGHT, IMG_WIDTH, 3))

# Preprocess branches
inception_input = layers.Lambda(inception_preprocess)(input_tensor)
densenet_input = layers.Lambda(densenet_preprocess)(input_tensor)

# InceptionV3
inception_base = InceptionV3(include_top=False, weights='imagenet', input_tensor=inception_input)
inception_output = layers.GlobalAveragePooling2D()(inception_base.output)

# DenseNet121
densenet_base = DenseNet121(include_top=False, weights='imagenet', input_tensor=densenet_input)
densenet_output = layers.GlobalAveragePooling2D()(densenet_base.output)

# Merge features
combined = layers.concatenate([inception_output, densenet_output])
x = layers.Dense(256, activation='relu')(combined)
x = layers.Dropout(0.5)(x)
output = layers.Dense(train_generator.num_classes, activation='softmax')(x)

model = Model(inputs=input_tensor, outputs=output)

# ---- Fine-tuning: Unfreeze top 50 layers ----
for layer in inception_base.layers[:-50]:
    layer.trainable = False
for layer in inception_base.layers[-50:]:
    layer.trainable = True

for layer in densenet_base.layers[:-50]:
    layer.trainable = False
for layer in densenet_base.layers[-50:]:
    layer.trainable = True

# ---- Compile Model ----
model.compile(optimizer=Adam(learning_rate=1e-5),
              loss='categorical_crossentropy',
              metrics=['accuracy'])

# ---- Checkpoint Path for Resuming ----
checkpoint_path = '/content/drive/MyDrive/my_folder/hybrid_model_checkpoint.h5'

# ---- Callbacks ----
callbacks = [
    EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True, verbose=1),
    ReduceLROnPlateau(monitor='val_loss', factor=0.3, patience=2, verbose=1),
    ModelCheckpoint(filepath=checkpoint_path, monitor='val_loss', save_best_only=True, verbose=1)
]

# ---- Load Previous Weights (If Exist) ----
if os.path.exists(checkpoint_path):
    print("🔄 Loading existing model weights...")
    model = tf.keras.models.load_model(checkpoint_path)
else:
    print("✨ Training from scratch...")

# ---- Train Model ----
history = model.fit(
    train_generator,
    validation_data=valid_generator,
    epochs=EPOCHS,
    callbacks=callbacks
)

# ---- Evaluate Model ----
test_loss, test_acc = model.evaluate(test_generator)
print(f"\n✅ Test Accuracy: {test_acc:.4f}")

# ---- Prediction and Metrics ----
predictions = model.predict(test_generator)
predicted_classes = np.argmax(predictions, axis=1)
true_classes = test_generator.classes
class_labels = list(test_generator.class_indices.keys())

print("\nClassification Report:")
print(classification_report(true_classes, predicted_classes, target_names=class_labels))

# ---- Confusion Matrix ----
cm = confusion_matrix(true_classes, predicted_classes)
plt.figure(figsize=(8, 6))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=class_labels, yticklabels=class_labels)
plt.xlabel('Predicted')
plt.ylabel('True')
plt.title('Confusion Matrix')
plt.show()

# ---- Plot Accuracy & Loss ----
plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(history.history['accuracy'], label='Train Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.xlabel('Epoch')
plt.ylabel('Accuracy')
plt.title('Training vs Validation Accuracy')
plt.legend()

plt.subplot(1, 2, 2)
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.title('Training vs Validation Loss')
plt.legend()

plt.tight_layout()
plt.show()

# ---- Save Final Model ----
final_model_path = '/content/drive/MyDrive/my_folder/hybrid_model_final.h5'
model.save(final_model_path)
print(f"📦 Model saved at: {final_model_path}")

from google.colab import drive
drive.mount('/content/drive')