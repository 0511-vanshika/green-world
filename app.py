from flask import Flask, render_template, request, redirect, url_for, session, g, jsonify
import pandas as pd
import bcrypt
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

USER_DATA_FILE = 'data/users.xlsx'
PLANT_DATA_FILE = 'data/plant_data.xlsx'
NOTES_DIR = 'user_notes'

if not os.path.exists('data'):
    os.makedirs('data')
if not os.path.exists(NOTES_DIR):
    os.makedirs(NOTES_DIR)

def load_users():
    try:
        users_df = pd.read_excel(USER_DATA_FILE)
        users = {}
        for index, row in users_df.iterrows():
            users[row['username']] = row['password'].encode('utf-8')
        return users
    except FileNotFoundError:
        return {}

def save_user(username, password):
    try:
        users_df = pd.read_excel(USER_DATA_FILE)
    except FileNotFoundError:
        users_df = pd.DataFrame(columns=['username', 'password'])

    if username not in users_df['username'].values:
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_row = pd.DataFrame([{'username': username, 'password': hashed_password}])
        users_df = pd.concat([users_df, new_row], ignore_index=True)
        try:
            users_df.to_excel(USER_DATA_FILE, index=False)
            return True
        except IOError:
            print(f"Error: Could not save user data to {USER_DATA_FILE}")
            return False
    else:
        return False

users = load_users()

def check_password(stored_password, provided_password):
    return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password)

def load_plant_data():
    try:
        global plant_df
        plant_df = pd.read_excel(PLANT_DATA_FILE)
        print("Plant DataFrame loaded successfully:")
        print(f"Number of rows in plant_df: {len(plant_df)}")
        print("First 20 unique values in 'planting type' column:")
        print(plant_df['planting type'].unique()[:20]) # Check for variations
        return plant_df
    except FileNotFoundError:
        print(f"Error: {PLANT_DATA_FILE} not found.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading plant data: {e}")
        return pd.DataFrame()

plant_df = load_plant_data()

@app.route('/', methods=['GET'])
def index():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    if username in users and check_password(users[username], password):
        session['username'] = username
        return redirect(url_for('choose_planting_type'))
    else:
        return render_template('login.html', error='Wrong username or password')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        new_username = request.form['new_username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if new_password != confirm_password:
            return render_template('register.html', error='Passwords do not match')
        elif save_user(new_username, new_password):
            global users
            users = load_users()
            return redirect(url_for('index'))
        else:
            return render_template('register.html', error='Username already exists')
    return render_template('register.html')

@app.route('/choose_planting_type')
def choose_planting_type():
    return render_template('choose_planting_type.html')

@app.route('/show_plants/<planting_type>')
def show_plants(planting_type):
    print(f"Request received for planting type: {planting_type}")
    if not plant_df.empty and 'Plant Name' in plant_df.columns and 'planting type' in plant_df.columns:
        plant_df['planting type'] = plant_df['planting type'].str.strip().str.lower() # Trim spaces and lowercase
        filtered_plants = plant_df[plant_df['planting type'] == planting_type.lower()].to_dict('records')
        print(f"Filtered plants for '{planting_type}': {len(filtered_plants)}")
        print(f"Filtered plants for '{planting_type}': {filtered_plants}")
        return render_template('plant_list.html', plants=filtered_plants, planting_type=planting_type.capitalize())
    else:
        print("Plant DataFrame is empty or missing required columns in /show_plants.")
        return render_template('choose_planting_type.html', error='Plant data not loaded or missing \"Plant Name\" column.')

@app.route('/plant/<plant_name>')
def show_plant_details(plant_name):
    print(f"Request received for plant details: {plant_name}")
    plant_data_series = plant_df[plant_df['Plant Name'].str.replace(' ', '_').str.lower() == plant_name.lower()]
    if not plant_data_series.empty:
        plant_data = plant_data_series.iloc[0].to_dict()
        return render_template('plant_details.html', plant=plant_data)
    else:
        return render_template('plant_details.html', plant=None, error=f"Plant '{plant_name.replace('_', ' ')}' not found.")

@app.route('/create_word_note', methods=['GET'])
def create_word_note():
    return render_template('create_word_note.html')

@app.route('/save_word_note', methods=['POST'])
def save_word_note():
    data = request.get_json()
    note_text = data.get('note')
    note_title = data.get('title')

    if note_text:
        user_id = session.get('username', 'guest')
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        sanitized_title = "".join(c if c.isalnum() else "_" for c in note_title.strip()) if note_title else "untitled"
        filename = f"{user_id}_{timestamp}_{sanitized_title}.txt"
        filepath = os.path.join(NOTES_DIR, filename)

        try:
            with open(filepath, 'w') as f:
                f.write(f"Title: {note_title}\n\n{note_text}")
            return jsonify({'success': True, 'message': f'Note "{note_title}" saved as {filename}'})
        except Exception as e:
            return jsonify({'success': False, 'error': f'Error saving note: {str(e)}'})
    else:
        return jsonify({'success': False, 'error': 'Note content is empty.'})

import os
from flask import Flask, render_template, session, url_for
from datetime import datetime

# Assuming NOTES_DIR is defined globally

@app.route('/my_notes')
def my_notes():
    username = session.get('username')
    print("\n--- Accessing /my_notes ---")
    print(f"Username in session: {username}")
    if username:
        user_notes = []
        print(f"Looking for notes in: {NOTES_DIR}")
        for filename in os.listdir(NOTES_DIR):
            print(f"Checking filename: {filename}")
            if filename.startswith(f"{username}_") and filename.endswith(".txt"):
                filepath = os.path.join(NOTES_DIR, filename)
                print(f"Potential note file found: {filepath}")
                try:
                    with open(filepath, 'r') as f:
                        lines = f.readlines()
                        title = "Untitled"
                        content = ""
                        if lines and lines[0].startswith("Title:"):
                            title = lines[0].split(":", 1)[1].strip()
                            content = "".join(lines[2:])
                            print(f"  Read title: '{title}'")
                            print(f"  First 20 chars of content: '{content[:20]}'")
                        else:
                            content = "".join(lines)
                            print("  No title line found.")
                            print(f"  First 20 chars of content: '{content[:20]}'")

                        parts = filename.split('_')
                        timestamp_str = None
                        if len(parts) >= 3:
                            timestamp_str = f"{parts[1]}_{parts[2]}"
                            try:
                                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                                user_notes.append({'title': title, 'content': content, 'timestamp': timestamp})
                                print(f"  Extracted timestamp: {timestamp}")
                            except ValueError as e:
                                print(f"  Error parsing timestamp '{timestamp_str}' from filename '{filename}': {e}")
                        else:
                            print(f"  Filename '{filename}' does not contain expected timestamp format.")

                except Exception as e:
                    print(f"  Error reading file '{filepath}': {e}")

        print(f"Final user_notes list: {user_notes}")
        user_notes.sort(key=lambda x: x['timestamp'], reverse=True)
        return render_template('view_saved_notes.html', notes=user_notes)
    else:
        print("  Username not in session, redirecting to login.")
        return redirect(url_for('index'))

@app.route('/plant_search')
def plant_search():
    return render_template('plant_search.html')

@app.route('/results', methods=['POST'])
def results():
    plant_name = request.form['plant_name'].strip().lower()
    if not plant_df.empty and 'Plant Name' in plant_df.columns and plant_name in plant_df['Plant Name'].str.lower().values:
        plant_info = plant_df[plant_df['Plant Name'].str.lower() == plant_name].iloc[0].to_dict()
        return render_template('results.html', plant=plant_info, name=plant_name.capitalize())
    else:
        return render_template('plant_search.html', error='Plant not found')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)