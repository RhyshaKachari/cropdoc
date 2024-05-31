from flask import Flask, request, jsonify
import sqlite3
import os
from tensorflow.keras.models import load_model
import numpy as np
import json
import bcrypt
from flask_cors import CORS
import tensorflow as tf

APP_ROOT = os.path.abspath(os.path.dirname(__file__))

model = load_model("plant_safe.h5", compile=False)

# Loading labels
with open("./labels.json", "r") as f:
    category_names = json.load(f)
    img_classes = list(category_names.values())

# Pre-processing images
def config_image_file(_image_path):
    predict = tf.keras.preprocessing.image.load_img(_image_path, target_size=(224, 224))
    predict_modified = tf.keras.preprocessing.image.img_to_array(predict)
    predict_modified = predict_modified / 255
    predict_modified = np.expand_dims(predict_modified, axis=0)
    return predict_modified

# Predicting
def predict_image(image):
    result = model.predict(image)
    return np.array(result[0])

# Working as the toString method
def output_prediction(filename):
    _image_path = f"images/{filename}"
    img_file = config_image_file(_image_path)
    results = predict_image(img_file)
    probability = np.max(results)
    index_max = np.argmax(results)

    return {"prediction": str(img_classes[index_max]), "probability": str(probability)}

# Init app
app = Flask(__name__)
CORS(app)

# Database
DATABASE = os.path.join(APP_ROOT, 'heart-safe.db')

# Initialize database schema
def init_db():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email VARCHAR(255) UNIQUE NOT NULL,
                fullname VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL
            )
        """)
        conn.commit()

# Initialize the database
init_db()

# Create a user
@app.route("/api/users", methods=["POST"])
def add_user():
    data = request.json
    email = data["email"]
    fullname = data["fullname"]
    password = data["password"].encode("utf-8")
    hash_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode("utf-8")

    print(password)

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, fullname, password) VALUES (?, ?, ?)", (email, fullname, hash_password))
        conn.commit()

    return jsonify({"message": "User created successfully"})

# Login user
@app.route("/api/users/login", methods=["POST"])
def login_user():
    data = request.json
    email = data["email"]
    password = data["password"].encode("utf-8")

    print(email, password)

    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=?", (email,))
        user = cursor.fetchone()
    
    print(user)

    if user:
        hashed_password = user[3].encode("utf-8")
        if bcrypt.checkpw(password, hashed_password):
            return jsonify([{"id": user[0], "email": user[1], "fullname": user[2]}])
    return jsonify({"message": "Invalid credentials"})

# Get All users
@app.route("/api/users", methods=["GET"])
def get_users():
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        users_data = [{"id": user[0], "email": user[1], "fullname": user[2]} for user in users]

    return jsonify(users_data)

# Image prediction
@app.route("/api/predict", methods=["POST"])
def get_disease_prediction():
    target = os.path.join(APP_ROOT, "images/")

    if not os.path.isdir(target):
        os.mkdir(target)

    file = request.files.get("file")

    filename = file.filename
    destination = os.path.join(target, filename)

    file.save(destination)

    result = output_prediction(filename)
    return jsonify(result)

# Run Server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
