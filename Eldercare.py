from flask import Flask, render_template, request, jsonify
import os
import datetime
import json
import uuid
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini API
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError("Please set the GEMINI_API_KEY environment variable")

genai.configure(api_key=API_KEY)

app = Flask(__name__)

class ElderlyVirtualNurse:
    def __init__(self, user_name="User"):
        self.user_name = user_name
        self.user_data_file = f"{user_name.lower()}_health_data.json"
        self.conversation_history = []
        self.user_data = self._load_user_data()
        self.model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Initialize default sections
        default_sections = ["medications", "appointments", "vital_signs", "general_health_notes"]
        for section in default_sections:
            if section not in self.user_data:
                self.user_data[section] = []
                
        self.system_prompt = """
        You are a virtual nursing assistant for elderly care. Your primary responsibilities include:
        1. Helping seniors track their medications (names, dosages, schedules)
        2. Managing healthcare appointments (dates, times, doctors, locations)
        3. Recording and monitoring vital signs (blood pressure, heart rate, temperature, etc.)
        4. Providing friendly reminders and health advice
        5. Responding to health questions with accurate information
        
        Always be patient, speak clearly, and focus on providing helpful healthcare assistance.
        DO NOT provide medical diagnoses or treatment recommendations beyond general health advice.
        Always suggest consulting healthcare providers for specific medical concerns.
        Be compassionate and understand that elderly users may need extra patience and simple explanations.
        """

        self.notes = []  # Add this line for storing health notes
        
    def _load_user_data(self):
        try:
            with open(self.user_data_file, 'r') as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "medications": [],
                "appointments": [],
                "vital_signs": [],
                "general_health_notes": []
            }
    
    def _save_user_data(self):
        with open(self.user_data_file, 'w') as file:
            json.dump(self.user_data, file, indent=4)
            
    def _add_to_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
    
    def add_medication(self, name, dosage, schedule, notes=""):
        if not name or not dosage or not schedule:
            return "Error: Name, dosage, and schedule are required"
            
        medication = {
            "id": str(uuid.uuid4())[:8],
            "name": name,
            "dosage": dosage,
            "schedule": schedule,
            "notes": notes,
            "date_added": datetime.datetime.now().strftime("%Y-%m-%d")
        }
        self.user_data["medications"].append(medication)
        self._save_user_data()
        return f"Successfully added medication: {name}"
    
    def add_appointment(self, doctor, date, time, location, notes=""):
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
            appointment = {
                "id": str(uuid.uuid4())[:8],
                "doctor": doctor,
                "date": date,
                "time": time,
                "location": location,
                "notes": notes
            }
            self.user_data["appointments"].append(appointment)
            self._save_user_data()
            return f"Appointment scheduled with {doctor} on {date} at {time}, {location}"
        except ValueError:
            return "Please use YYYY-MM-DD format for the date."
    
    def add_vital_sign(self, vital_type, value, notes=""):
        if not vital_type or not value:
            return "Error: Type and value are required"
            
        vital = {
            "id": str(uuid.uuid4())[:8],
            "type": vital_type,
            "value": value,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "notes": notes
        }
        self.user_data["vital_signs"].append(vital)
        self._save_user_data()
        return f"Successfully recorded {vital_type}: {value}"
    
    def get_medications(self):
        return self.user_data["medications"]
    
    def get_appointments(self):
        if not self.user_data["appointments"]:
            return "No appointments currently scheduled."
        return self.user_data["appointments"]
    
    def get_vital_signs(self):
        return self.user_data["vital_signs"]
    
    def process_user_input(self, user_input):
        if user_input.lower() in ["exit", "quit", "bye"]:
            return "Goodbye! Take care of your health."
        
        self._add_to_history("user", user_input)
        
        context = {
            "medications": self.get_medications(),
            "appointments": self.get_appointments(),
            "vitals": self.get_vital_signs()
        }
        
        context_str = f"USER CONTEXT:\n{json.dumps(context, indent=2)}\n\n"
        
        messages = [
            {"role": "system", "content": self.system_prompt + "\n\n" + context_str},
            *self.conversation_history
        ]
        
        try:
            response = self.model.generate_content([msg["content"] for msg in messages])
            if not response or not response.text:
                return "I apologize, but I couldn't generate a response. Please try again."
                
            response_text = response.text
            self._add_to_history("assistant", response_text)
            return response_text
            
        except Exception as e:
            print(f"Error generating response: {str(e)}")  # Log the error
            return f"I'm having trouble with the AI model: {str(e)}. Please try again later."

    def add_note(self, title, content):
        note = {
            "id": str(uuid.uuid4())[:8],
            "title": title,
            "content": content,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.notes.append(note)
        return "Note added successfully"
    
    def get_notes(self):
        if not self.notes:
            return "No health notes recorded yet."
        return self.notes

# Initialize the chatbot
nurse = ElderlyVirtualNurse("User")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    response = nurse.process_user_input(user_message)
    return jsonify({
        'response': response,
        'medications': nurse.get_medications(),
        'appointments': nurse.get_appointments(),
        'vitals': nurse.get_vital_signs()
    })

@app.route('/add_medication', methods=['POST'])
def add_medication():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        name = data.get('name')
        dosage = data.get('dosage')
        schedule = data.get('schedule')
        notes = data.get('notes', '')
        
        if not all([name, dosage, schedule]):
            return jsonify({'error': 'Name, dosage, and schedule are required'}), 400
            
        response = nurse.add_medication(name, dosage, schedule, notes)
        return jsonify({'message': response, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/add_appointment', methods=['POST'])
def add_appointment():
    data = request.json
    response = nurse.add_appointment(
        data.get('doctor'),
        data.get('date'),
        data.get('time'),
        data.get('location'),
        data.get('notes', '')
    )
    return jsonify({'message': response})

@app.route('/add_vital', methods=['POST'])
def add_vital():
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        vital_type = data.get('type')
        value = data.get('value')
        notes = data.get('notes', '')
        
        if not all([vital_type, value]):
            return jsonify({'error': 'Type and value are required'}), 400
            
        response = nurse.add_vital_sign(vital_type, value, notes)
        return jsonify({'message': response, 'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/dashboard_data')
def dashboard_data():
    medication_count = len([m for m in nurse.get_medications() if isinstance(m, dict)])
    appointment_count = len([a for a in nurse.get_appointments() if isinstance(a, dict)])
    vital_count = len([v for v in nurse.get_vital_signs() if isinstance(v, dict)])
    note_count = len([n for n in nurse.notes if isinstance(n, dict)])
    
    # Get recent activities (last 5 items from each category)
    recent_activities = []
    
    # Add medications
    medications = nurse.get_medications()
    if isinstance(medications, list):
        for med in medications[-5:]:
            recent_activities.append({
                "type": "Medication",
                "description": f"Added {med['name']} - {med['dosage']}",
                "timestamp": med['date_added']
            })
    
    # Add appointments
    appointments = nurse.get_appointments()
    if isinstance(appointments, list):
        for apt in appointments[-5:]:
            recent_activities.append({
                "type": "Appointment",
                "description": f"Scheduled with {apt['doctor']} on {apt['date']}",
                "timestamp": apt['date']
            })
    
    # Add vital signs
    vitals = nurse.get_vital_signs()
    if isinstance(vitals, list):
        for vital in vitals[-5:]:
            recent_activities.append({
                "type": "Vital Sign",
                "description": f"Recorded {vital['type']}: {vital['value']}",
                "timestamp": vital['timestamp']
            })
    
    # Sort activities by timestamp (most recent first)
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:5]  # Keep only the 5 most recent activities
    
    return jsonify({
        "medicationCount": medication_count,
        "appointmentCount": appointment_count,
        "vitalCount": vital_count,
        "noteCount": note_count,
        "recentActivities": recent_activities
    })

@app.route('/get_medications')
def get_medications():
    try:
        medications = nurse.get_medications()
        return jsonify({"medications": medications})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_appointments')
def get_appointments():
    appointments = nurse.get_appointments()
    return jsonify({"appointments": appointments if isinstance(appointments, list) else []})

@app.route('/get_vitals')
def get_vitals():
    try:
        vitals = nurse.get_vital_signs()
        return jsonify({"vitals": vitals})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_notes')
def get_notes():
    notes = nurse.get_notes()
    return jsonify({"notes": notes if isinstance(notes, list) else []})

@app.route('/add_note', methods=['POST'])
def add_note():
    data = request.json
    response = nurse.add_note(
        data.get('title'),
        data.get('content')
    )
    return jsonify({'message': response})

if __name__ == '__main__':
    app.run(debug=True)
