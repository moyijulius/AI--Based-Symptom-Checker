# app.py
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import pickle
import numpy as np
import pandas as pd
from difflib import get_close_matches
from flask_sqlalchemy import SQLAlchemy
from model import db, User  # Import db and User from model.py
from forms import RegistrationForm, LoginForm  # Import forms from forms.py
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure the SQLite database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable Flask-SQLAlchemy modification tracking

# Initialize SQLAlchemy
db.init_app(app)
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f"Welcome, {user.username}!", "success")  # Updated message
            return redirect(url_for('home'))
        else:
            flash("Invalid email or password", "error")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)



@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        # Check if the email is already registered
        if User.query.filter_by(email=email).first():
            flash("Email already registered continue login", "error")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            new_user = User(username=username, email=email, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error: {e}", "error")
            return redirect(url_for('register'))

    return render_template('register.html', form=form)
@app.route("/")
def home():
    if 'user_id' not in session:  # Check if user is logged in by checking the session
        flash("Please login to access the system.", "error")
        return redirect(url_for('login'))  # Redirect to the login page if not logged in
    return render_template("index.html", symptoms=symptoms)  # Display the home page if logged in


@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully!.", "success")
    return redirect(url_for('login'))


# Model loading and other routes omitted for brevity

# Load the trained model and required files
try:
    model = pickle.load(open("model/svc.pkl", "rb"))
    symptoms = pickle.load(open("model/symptom_list.pkl", "rb"))
    disease_mapping = pickle.load(open("model/disease_mapping.pkl", "rb"))  # Maps labels to disease names
except FileNotFoundError as e:
    print(f"Error: {e}")
    model, symptoms, disease_mapping = None, [], {}

# Load medication and description data
try:
    medication_data = pd.read_csv("data/medications.csv")
    description_data = pd.read_csv("data/description.csv")
    precautions_df_data=pd.read_csv("data/precautions_df.csv")
    diets_data=pd.read_csv("data/diets.csv")
    workout_df_data=pd.read_csv("data/workout_df.csv")
except FileNotFoundError as e:
    print(f"Error loading CSV files: {e}")
    medication_data, description_data,precautions_df_data,diets_data,workout_df_data = pd.DataFrame(), pd.DataFrame()

def match_symptoms(user_symptoms, valid_symptoms, threshold=0.6):
    matched = []
    unmatched = []
    for user_symptom in user_symptoms:
        closest = get_close_matches(user_symptom, valid_symptoms, n=1, cutoff=threshold)
        if closest:
            matched.append(closest[0])
        else:
            unmatched.append(user_symptom)
    return matched, unmatched




@app.route("/predict", methods=["POST"])
def predict():
    if model is None:
        return jsonify({"error": "Model files not found. Ensure svc.pkl, symptom_list.pkl, and disease_mapping.pkl exist."})

    try:
        user_input = request.form.get("symptoms", "")
        user_symptoms = [symptom.strip().lower().replace(" ", "_") for symptom in user_input.split(",")]

        matched_symptoms, unmatched_symptoms = match_symptoms(user_symptoms, symptoms)

        if unmatched_symptoms:
            return jsonify({
                "error": f"Some symptoms could not be recognized: {', '.join(unmatched_symptoms)}. "
                         f"Matched symptoms: {', '.join(matched_symptoms)}."
            })

        input_vector = np.zeros(len(symptoms))
        for symptom in matched_symptoms:
            if symptom in symptoms:
                input_vector[symptoms.index(symptom)] = 1

        prediction = model.predict([input_vector])[0]
        disease_name = disease_mapping.get(prediction, "Unknown Disease")

        return jsonify({"disease": disease_name})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/details/<disease>", methods=["GET"])
def get_disease_details(disease):
    try:
        # Fetch medication and description for the given disease
        medication = medication_data[
            medication_data["Disease"].str.strip().str.lower() == disease.strip().lower()

        ]
        description = description_data[
           description_data["Disease"].str.strip().str.lower() == disease.strip().lower()
        ]
        precautions_df = precautions_df_data[
            precautions_df_data["Disease"].str.strip().str.lower() == disease.strip().lower()
        ]
        diets = diets_data[
            diets_data["Disease"].str.strip().str.lower() == disease.strip().lower()
        ]
        workout_df= workout_df_data[
           workout_df_data["Disease"].str.strip().str.lower() == disease.strip().lower()
        ]


        # Get the first match or return default messages
        medication_info = medication["Medication"].iloc[0] if not medication.empty else "No medication information available."
        description_info = description["Description"].iloc[0] if not description.empty else "No description available."
        precautions_df_info = precautions_df["Precaution_1"].iloc[0] if not precautions_df.empty else "No description available."
        diets_info = diets["Diet"].iloc[0] if not diets.empty else "No Diets available."
        workout_df_info = workout_df["workout"].iloc[0] if not  workout_df.empty else "No Workout available."

        return jsonify({
            "medication": medication_info,
            "description": description_info,
            "precautions_df":precautions_df_info,
            "diets":diets_info,
            "workout_df":workout_df_info,
        })
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True)