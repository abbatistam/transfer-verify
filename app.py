from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
from flask_cors import CORS
import os
import re
import urllib.parse


# Configuración de la aplicación Flask
app = Flask(__name__)

# Configuración de la conexión a MongoDB
client = MongoClient(os.getenv('MONGO_URL'))
db = client["transfer-verify"]
messages_collection = db["messages"]

CORS(app)

def procesar_cadena(cadena_decodificada):
    try:
        # Decodificar la cadena
        mensaje_decodificado = urllib.parse.unquote(cadena_decodificada).replace('+', ' ')
        
        # Buscar información en el mensaje usando expresiones regulares
        matches = {
            "desde": re.search(r"Desde : (.+)", mensaje_decodificado),
            "numero_de_telefono": re.search(r"telefono (\d{10})", mensaje_decodificado),
            "numero_de_cuenta": re.search(r"cuenta (\d+)", mensaje_decodificado),
            "cantidad_moneda": re.search(r"(\d+\.\d+) (\w+)", mensaje_decodificado),
            "tipo_moneda": re.search(r"\d+\.\d+\s+(CUP|USD)\.", mensaje_decodificado),
            "numero_de_transaccion": re.search(r"Nro\. Transaccion (\w+)", mensaje_decodificado)
        }
        
        # Extraer la información de las coincidencias
        informacion = {}
        for key, match in matches.items():
            if match:
                informacion[key] = match.group(1)
            else:
                informacion[key] = None
        
        return informacion
        
    except Exception as e:
        # En caso de error, imprimir el error y retornar None
        print("Error al procesar cadena:", e)
        return None

@app.route("/mensajes", methods=["POST"])
def agregar_mensaje():
    """Agrega un nuevo mensaje a la colección."""
    try:
        # Obtener el cuerpo del mensaje de la solicitud
        message_body = request.get_data(as_text=True)
        print(message_body)
        messages_collection.insert_one({
            "timestamp": datetime.now(timezone.utc),
            "message_body": message_body
        })
        # Procesar el cuerpo del mensaje
        datos_mensaje = procesar_cadena(message_body)
        print(datos_mensaje)
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
