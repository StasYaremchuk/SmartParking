from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy import text
from datetime import datetime

app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}}, methods=["GET", "POST", "DELETE", "OPTIONS"])

# DATABASE 
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:stas2006@localhost/smart_parking'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# DATA MODELS

class ParkingSlot(db.Model):
    __tablename__ = 'parking_slots'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Integer) 
    is_reserved = db.Column(db.Boolean, default=False)

class HourlyStat(db.Model):
    __tablename__ = 'hourly_stats'
    id = db.Column(db.Integer, primary_key=True)
    recorded_at = db.Column(db.DateTime, default=datetime.now)
    free_slots = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)

current_env_data = {"temp": 0.0, "hum": 0.0}

# API

@app.route('/update', methods=['POST'])
def update_status():
    global current_env_data
    try:
        data = request.json
        slot_id = data.get('id')
        new_status = data.get('status')
        
        if 'temp' in data and 'hum' in data:
            current_env_data["temp"] = data.get('temp')
            current_env_data["hum"] = data.get('hum')

        slot = ParkingSlot.query.get(slot_id)
        if slot:
            if slot.status != new_status:
                action = 'arrival' if new_status == 1 else 'departure'
                sql = text("INSERT INTO parking_logs (slot_id, action) VALUES (:sid, :act)")
                db.session.execute(sql, {"sid": slot_id, "act": action})

            if new_status == 1:
                slot.is_reserved = False

            slot.status = new_status
            db.session.commit()
            return jsonify({"status": "success", "weather": current_env_data}), 200
        
        return jsonify({"status": "error", "message": "Slot not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/save-hourly-stat', methods=['POST'])
def save_hourly():
    try:
        free_count = ParkingSlot.query.filter_by(status=0).count()
        new_stat = HourlyStat(
            free_slots=free_count,
            temperature=current_env_data["temp"],
            humidity=current_env_data["hum"]
        )
        db.session.add(new_stat)
        db.session.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/status', methods=['GET'])
def get_full_status():
    try:
        slots = ParkingSlot.query.all()
        history = HourlyStat.query.order_by(HourlyStat.recorded_at.desc()).limit(10).all()
        
        return jsonify({
            "slots": [{"id": s.id, "status": s.status, "is_reserved": s.is_reserved} for s in slots],
            "weather": current_env_data,
            "history": [
                {
                    "id": h.id,  
                    "time": h.recorded_at.strftime("%H:%M"),
                    "free": h.free_slots,
                    "temp": h.temperature,
                    "hum": h.humidity
                } for h in history
            ]
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/reserve', methods=['POST'])
def reserve_slot():
    try:
        data = request.json
        slot_id = data.get('id')
        slot = ParkingSlot.query.get(slot_id)
        if slot:
            if slot.status == 1:
                return jsonify({"status": "error", "message": "Місце вже зайняте"}), 400
            slot.is_reserved = not slot.is_reserved
            db.session.commit()
            return jsonify({"status": "success", "is_reserved": slot.is_reserved}), 200
        return jsonify({"status": "error", "message": "Slot not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/logs/clear', methods=['DELETE'])
def clear_logs():
    try:
        db.session.execute(text("DELETE FROM parking_logs"))
        db.session.execute(text("DELETE FROM hourly_stats"))
        db.session.commit()
        return jsonify({"status": "success", "message": "Всі дані очищено"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/logs/delete/<int:stat_id>', methods=['DELETE'])
def delete_single_log(stat_id):
    try:
        stat = HourlyStat.query.get(stat_id)
        if stat:
            db.session.delete(stat)
            db.session.commit()
            return jsonify({"status": "success", "message": f"Запис №{stat_id} видалено"}), 200
        return jsonify({"status": "error", "message": "Запис не знайдено"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/logs', methods=['GET'])
def get_logs():
    try:
        result = db.session.execute(text("SELECT * FROM parking_logs ORDER BY timestamp DESC LIMIT 10"))
        logs = [{"id": row[0], "slot_id": row[1], "action": row[2], "time": str(row[3])} for row in result]
        return jsonify(logs), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5001, debug=True)