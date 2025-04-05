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
        return f"Added medication: {name}, {dosage}, {schedule}"
    
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
        vital = {
            "id": str(uuid.uuid4())[:8],
            "type": vital_type,
            "value": value,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "notes": notes
        }
        self.user_data["vital_signs"].append(vital)
        self._save_user_data()
        return f"Recorded {vital_type}: {value}"
    
    def get_medications(self):
        if not self.user_data["medications"]:
            return "No medications currently tracked."
        return self.user_data["medications"]
    
    def get_appointments(self):
        if not self.user_data["appointments"]:
            return "No appointments currently scheduled."
        return self.user_data["appointments"]
    
    def get_vital_signs(self):
        if not self.user_data["vital_signs"]:
            return "No vital signs recorded yet."
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
    data = request.json
    response = nurse.add_medication(
        data.get('name'),
        data.get('dosage'),
        data.get('schedule'),
        data.get('notes', '')
    )
    return jsonify({'message': response})

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
    data = request.json
    response = nurse.add_vital_sign(
        data.get('type'),
        data.get('value'),
        data.get('notes', '')
    )
    return jsonify({'message': response})

if __name__ == '__main__':
    app.run(debug=True)