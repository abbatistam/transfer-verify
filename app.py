from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
from flask_cors import CORS
import os
import re
from urllib.parse import unquote

# Configuración de la aplicación Flask
app = Flask(__name__)

# Configuración de la conexión a MongoDB
client = MongoClient(os.getenv('MONGO_URL'))
db = client["transfer-verify"]
messages_collection = db["messages"]

CORS(app)

def procesar_cadena(cadena_decodificada):
    # Extraer el valor de "message_body" del JSON
    match_mensaje = re.search(r'"message_body": "(.*?)"', cadena_decodificada)
    if not match_mensaje:
        return None  # Retornar None si no se encuentra el mensaje
    
    mensaje = match_mensaje.group(1)

    # Decodificar el mensaje
    mensaje_decodificado = mensaje.replace('+', ' ').replace('%28', '(').replace('%29', ')').replace('%0A', '\n').replace('%3A', ':')

    # Buscar información en el mensaje usando expresiones regulares
    match = re.search(r"Desde\s*:\s*([^()]+)\(([^()]+)\)\s*([\w\s]+)\s+(\d+)\s+de\s+([0-9.]+)\s+(\w+)\.\s*Nro\.\s+Transaccion\s+(\w+)", mensaje_decodificado)
    
    # Si no hay coincidencias, retornar None
    if not match:
        return None
    
    # Extraer la información
    desde = match.group(1).strip()
    nombre_de_contacto = match.group(2).strip()
    informacion_transferencia = match.group(3).strip()
    numero_de_cuenta = match.group(4)
    cantidad_de_dinero = match.group(5)
    moneda = match.group(6)
    numero_de_transaccion = match.group(7)
        
    # Devolver la información extraída
    return {
        "desde": desde,
        "nombre_de_contacto": nombre_de_contacto,
        "informacion_transferencia": informacion_transferencia,
        "numero_de_cuenta": numero_de_cuenta,
        "cantidad_de_dinero": cantidad_de_dinero,
        "moneda": moneda,
        "numero_de_transaccion": numero_de_transaccion
    }

@app.route("/mensajes", methods=["POST"])
def agregar_mensaje():
    """Agrega un nuevo mensaje a la colección."""
    try:
        # Obtener el cuerpo del mensaje de la solicitud
        message_body = request.get_data(as_text=True)
        print(message_body)
        # Procesar el cuerpo del mensaje
        datos_mensaje = procesar_cadena(message_body)
        
        # Si no se puede procesar el mensaje, responder con error
        if datos_mensaje is None:
            return jsonify({"success": False, "error": "No se pudo procesar el mensaje"}), 400
        
        # Agregar todos los campos devueltos por la función procesar_cadena
        mensaje = {
            "timestamp": datetime.now(timezone.utc),
            "desde": datos_mensaje.get("desde"),
            "nombre_de_contacto": datos_mensaje.get("nombre_de_contacto"),
            "informacion_transferencia": datos_mensaje.get("informacion_transferencia"),
            "numero_de_cuenta": datos_mensaje.get("numero_de_cuenta"),
            "cantidad_de_dinero": datos_mensaje.get("cantidad_de_dinero"),
            "moneda": datos_mensaje.get("moneda"),
            "numero_de_transaccion": datos_mensaje.get("numero_de_transaccion")
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
