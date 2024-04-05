from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
from flask_cors import CORS
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
    """Agrega un nuevo mensaje a la colección."""
    try:
        # Obtener el cuerpo del mensaje de la solicitud
        message_body = request.get_json()["message_body"]

        # Crear un nuevo documento con timestamp
        mensaje = {
            "message_body": message_body,
            "timestamp": datetime.now(timezone.utc),
        }

        # Insertar el documento en la colección
        messages_collection.insert_one(mensaje)

        # Responder con éxito
        return jsonify({"success": True}), 201

    except Exception as error:
        # Responder con error
        return jsonify({"success": False, "error": str(error)}), 400

# Iniciar la aplicación Flask
if __name__ == "__main__":
    app.run(debug=True)
