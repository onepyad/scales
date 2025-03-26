from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

# Инициализация хранилища данных
data_storage = {
    "timestamp": "",
    "weight": None,
}

@app.route('/update_data', methods=['POST'])
def update_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Пустые данные"}), 400

        data_storage["timestamp"] = data.get("timestamp", "")
        data_storage["weight"] = data.get("weight", None)

        for key in data.keys():
            if key.startswith("laser"):
                data_storage[key] = data.get(key, None)

        return jsonify({"message": "Данные успешно обновлены"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_data', methods=['GET'])
def get_data():
    response_data = data_storage.copy()
    return jsonify(response_data)

@app.route('/restart_service', methods=['POST'])
def restart_service():
    try:
        result = subprocess.run(['sudo', 'systemctl', 'restart', 'weith_service.service'], check=True, capture_output=True, text=True)
        return jsonify({"message": "Служба успешно перезапущена", "output": result.stdout.strip()}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "Не удалось перезапустить службу", "details": e.stderr.strip()}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/make_measurement', methods=['POST'])
def make_measurement():
    try:
        with open("/tmp/do_measure.flag", "w") as f:
            f.write("1")
        return jsonify({"message": "Измерение инициировано"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
