from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
from flask_cors import CORS
from flask_accepts import accepts
import os

# Configuración de la aplicación Flask
app = Flask(__name__)

# Configuración de la conexión a MongoDB
client = MongoClient(os.getenv('MONGO_URL'))
db = client["transfer-verify"]
messages_collection = db["messages"]

CORS(app)

# Ruta para agregar un mensaje
@app.route("/mensajes", methods=["POST"])
def agregar_mensaje():
    try:
        # Procesar el cuerpo de la solicitud independientemente del tipo de contenido
        message_body = request.get_data(as_text=True)

        mensaje = {
            "message_body": message_body,
            "timestamp": datetime.now(timezone.utc),
        }

        messages_collection.append(mensaje)

        return jsonify({"success": True}), 201

    except Exception as error:
        return jsonify({"success": False, "error": str(error)}), 400
    
# Iniciar la aplicación Flask
if __name__ == "__main__":
    app.run(debug=True)
