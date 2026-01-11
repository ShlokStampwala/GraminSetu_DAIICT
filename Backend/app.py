from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import datetime


app = Flask(__name__)


CORS(app)


client = MongoClient("mongodb://localhost:27017/")
db = client['Graminsetu_Shlok']


asha_col = db['ASHA']
doctor_col = db['Doctor']
patients_col = db['Patients']


AUTHORIZED_MASTER_KEY = "GRAMIN_2026_SECURE"

@app.route('/api/auth/register', methods=['POST'])
def register_user():
    try:
        data = request.get_json()
        role = data.get('role')
        if data.get('masterKey') != AUTHORIZED_MASTER_KEY:
            return jsonify({"status": "error", "message": "Invalid Master Key"}), 403
        collection = asha_col if role == 'asha' else doctor_col
        if collection.find_one({"phone": data.get('phone')}):
            return jsonify({"status": "error", "message": "User already exists"}), 400
        data['created_at'] = datetime.datetime.utcnow()
        collection.insert_one(data)
        return jsonify({"status": "success", "message": "Registration successful"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/api/auth/login', methods=['POST'])
def login_user():
    try:
        data = request.get_json()
        role = data.get('role')
        collection = asha_col if role == 'asha' else doctor_col
        user = collection.find_one({
            "phone": data.get('phone'),
            "password": data.get('password')
        })

        if user:
            collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_login": datetime.datetime.utcnow()}}
            )
            return jsonify({
                "status": "success", 
                "user": {
                    "name": user.get('name'),
                    "phone": user.get('phone'),
                    "village": user.get('village')
                }
            }), 200
        return jsonify({"status": "error", "message": "Invalid credentials"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/api/sync/patients', methods=['POST'])
def sync_patients():
    try:
        records = request.get_json()
        for record in records:
            # BMI calculate karo agar height/weight hai
            h = float(record.get('height', 0)) / 100
            w = float(record.get('weight', 0))
            bmi_calc = round(w / (h * h), 2) if h > 0 else 0

            current_vitals = {
                "date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
                "bmi": bmi_calc,
                "glucose": float(record.get('glucose_mg', 0)), # Match with glucose_mg
                "cholesterol": float(record.get('cholesterol_mg', 0)), # Match with cholesterol_mg
                "ap_hi": float(record.get('ap_hi', 0)),
                "riskProbability": float(record.get('riskProbability', 0))
            }
            
            patients_col.update_one(
                {"aadhaar": str(record['aadhaar'])},
                {
                    "$set": {
                        "name": record.get('name'),
                        "age": record.get('age'),
                        "smoke": record.get('smoke'),
                        "alco": record.get('alco'),
                        "active": record.get('active'),
                        "latest_vitals": current_vitals
                    },
                    "$addToSet": {"history": current_vitals}
                },
                upsert=True
            )
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
@app.route('/api/patient/<aadhaar>', methods=['GET'])
def get_patient_profile(aadhaar):
    try:
        patient = patients_col.find_one({"aadhaar": aadhaar}, {"_id": 0})
        if patient:
            return jsonify(patient), 200
        return jsonify({"status": "error", "message": "Not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)