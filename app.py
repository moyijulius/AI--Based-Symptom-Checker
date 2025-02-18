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
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure the SQLite database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable Flask-SQLAlchemy modification tracking


app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Replace with your email provider's SMTP server
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'moyijulius17@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'fwyh bkbi qdtp twbb'     # Replace with your email password or app password
app.config['MAIL_DEFAULT_SENDER'] = 'moyijulius17@gmail.com'  # Replace with your email


# Initialize SQLAlchemy and Mail
db.init_app(app)
mail = Mail(app)


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
            session['email'] = user.email  # Store user email in session
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
    medication_data, description_data, precautions_df_data, diets_data, workout_df_data = pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

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
        workout_df = workout_df_data[
           workout_df_data["Disease"].str.strip().str.lower() == disease.strip().lower()
        ]

        # Get the first match or return default messages
        medication_info = medication["Medication"].iloc[0] if not medication.empty else "No medication information available."
        description_info = description["Description"].iloc[0] if not description.empty else "No description available."
        precautions_df_info = precautions_df["Precaution_1"].iloc[0] if not precautions_df.empty else "No description available."
        diets_info = diets["Diet"].iloc[0] if not diets.empty else "No Diets available."
        workout_df_info = workout_df["workout"].iloc[0] if not workout_df.empty else "No Workout available."

        return jsonify({
            "medication": medication_info,
            "description": description_info,
            "precautions_df": precautions_df_info,
            "diets": diets_info,
            "workout_df": workout_df_info,
        })
    except Exception as e:
        return jsonify({"error": str(e)})
    
    # route to send results
@app.route("/send-results", methods=["POST"])
def send_results():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Please login to access this feature."})
    
    try:
        # Get data from the request
        email = request.form.get("email")
        disease = request.form.get("disease")
        description = request.form.get("description")
        medication = request.form.get("medication")
        precaution = request.form.get("precaution")
        diet = request.form.get("diet")
        workout = request.form.get("workout")
        
        # Create the email content
        subject = f"Your Health Report for {disease}"
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .container {{ max-width: 600px; margin: auto; padding: 20px; }}
                h1 {{ color: #2a5885; }}
                h2 {{ color: #507299; margin-top: 20px; }}
                p {{ line-height: 1.5; }}
                .footer {{ margin-top: 30px; font-size: 0.8em; color: #777; }}
                #dis{{color:red;}}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Your Health Report</h1>
                <h2>Predicted Disease: <span id="dis">{disease}<span></h2>
                
                <h2>Description</h2>
                <p>{description}</p>
                
                <h2>Recommended Medication</h2>
                <p>{medication}</p>
                
                <h2>Precautions</h2>
                <p>{precaution}</p>
                
                <h2>Recommended Diet</h2>
                <p>{diet}</p>
                
                <h2>Recommended Workout</h2>
                <p>{workout}</p>
                
                <div class="footer">
                    <p>This health report is generated based on your symptoms by our AI system.</p>
                    <p>Disclaimer: This is not medical advice. Please consult a healthcare professional for proper diagnosis and treatment.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send the email
        msg = Message(subject=subject, recipients=[email], html=body)
        mail.send(msg)
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({"success": False, "message": f"Error: {e}"})\
        
# get email
@app.route("/get-user-email", methods=["GET"])
def get_user_email():
    if 'email' in session:
        return jsonify({"email": session['email']})
    return jsonify({"email": ""})

#flash message for email sending

@app.route("/set-flash-message", methods=["GET"])
def set_flash_message():
    message_type = request.args.get("type", "info")  # Default to 'info' if type not specified
    message = request.args.get("message", "")
    
    if message:
        flash(message, message_type)
    
    return jsonify({"success": True})

# about view function and path
@app.route('/about')
def about():
    return render_template("about.html")

# contact view function and path
@app.route('/contact')
def contact():
    return render_template("contact.html")

# developer view function and path
@app.route('/developer')
def developer():
    return render_template("developer.html")

if __name__ == "__main__":
    app.run(debug=True)