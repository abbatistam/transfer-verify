from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime, timezone
from flask_cors import CORS
import os
import re
import urllib.parse
from bson import ObjectId

# Configuración de la aplicación Flask
app = Flask(__name__)

# Configuración de la conexión a MongoDB
client = MongoClient(os.getenv('MONGO_URL'))
db = client["transfer-verify"]
messages_collection = db["messages"]
payment_orders_collection = db["payment_orders"]

CORS(app)

def procesar_cadena(cadena_decodificada):
    try:
        # Decodificar la cadena
        mensaje_decodificado = urllib.parse.unquote(cadena_decodificada).replace('+', ' ')
        
        # Buscar información en el mensaje usando expresiones regulares
        matches = {
            "desde": re.search(r"Desde : (.+)", mensaje_decodificado),
            "numero_de_telefono": re.search(r"telefono (\d{10})", mensaje_decodificado),
            "numero_cuenta": re.search(r"cuenta (\d+)", mensaje_decodificado),
            "cantidad_dinero": re.search(r"(\d+\.\d+) (\w+)", mensaje_decodificado),
            "moneda": re.search(r"\d+\.\d+\s+(CUP|USD)\.", mensaje_decodificado),
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
            "numero_de_telefono": datos_mensaje.get("numero_de_telefono"),
            "numero_cuenta": datos_mensaje.get("numero_cuenta"),
            "cantidad_dinero": datos_mensaje.get("cantidad_dinero"),
            "moneda": datos_mensaje.get("moneda"),
            "numero_de_transaccion": datos_mensaje.get("numero_de_transaccion"),
            "status": "unconfirmed"
        }

        # Insertar el documento en la colección
        messages_collection.insert_one(mensaje)

        # Buscar y actualizar el primer registro ordenado por timestamp que coincida con el número de tarjeta,
        # cantidad a pagar y moneda en la colección payment_orders si el status es "pending"
        filtro = {
            "numero_cuenta": datos_mensaje.get("numero_cuenta"),
            "cantidad_dinero": datos_mensaje.get("cantidad_dinero"),
            "moneda": datos_mensaje.get("moneda"),
            "status": "pending",
            "numero_de_transaccion": "unconfirmed",
        }
        print(filtro)
        actualizacion = {"$set": {"status": "processing"}}
        resultado = payment_orders_collection.find_one_and_update(
            filtro,
            actualizacion,
            sort=[("timestamp", 1)]  # Ordenar por timestamp ascendente
        )

        # Verificar si se actualizó algún documento
        if not resultado:
            return jsonify({"success": False, "error": "No se encontró ninguna orden de pago pendiente que coincida"}), 404

        # Responder con éxito
        return jsonify({"success": True}), 201

    except Exception as error:
        # Responder con error
        return jsonify({"success": False, "error": str(error)}), 400
     
@app.route('/payment_orders', methods=['POST'])
def create_payment_order():
    data = request.json
    # Asegurarse de que los campos requeridos están presentes
    if 'numero_cuenta' not in data or 'cantidad_dinero' not in data or 'moneda' not in data:
        return jsonify({'error': 'Faltan campos requeridos'}), 400
    
    # Convertir la cantidad de dinero a float con dos decimales
    cantidad_dinero = float(data['cantidad_dinero'])
    cantidad_dinero_formateada = '{:.2f}'.format(cantidad_dinero)
    data['cantidad_dinero'] = cantidad_dinero_formateada

    # Agregar el campo 'status' por defecto si no está presente
    data['status'] = data.get('status', 'pending')
    data['timestamp'] = datetime.now(timezone.utc)
    data['numero_de_transaccion'] = 'unconfirmed'
    # Insertar la orden de pago en la colección
    result = payment_orders_collection.insert_one(data)
    return jsonify({'message': 'Orden de pago creada exitosamente', 'id': str(result.inserted_id)}), 201

# Ruta para obtener todas las órdenes de pago
@app.route('/payment_orders', methods=['GET'])
def get_all_payment_orders():
    payment_orders = list(payment_orders_collection.find()) 
    for order in payment_orders:
        order['_id'] = str(order['_id'])
    return jsonify(payment_orders), 200

# Ruta para obtener una orden de pago por ID
@app.route('/payment_orders/<order_id>', methods=['GET'])
def get_payment_order_by_id(order_id):
    payment_order = payment_orders_collection.find_one({'_id': ObjectId(order_id)})
    if payment_order:
        return jsonify(payment_order), 200
    else:
        return jsonify({'error': 'Orden de pago no encontrada'}), 404

# Ruta para actualizar una orden de pago por ID
@app.route('/payment_orders/<order_id>', methods=['PUT'])
def update_payment_order_by_id(order_id):
    data = request.json
    updated_order = payment_orders_collection.update_one({'_id': ObjectId(order_id)}, {'$set': data})
    if updated_order.modified_count:
        return jsonify({'message': 'Orden de pago actualizada exitosamente'}), 200
    else:
        return jsonify({'error': 'Orden de pago no encontrada'}), 404

# Ruta para eliminar una orden de pago por ID
@app.route('/payment_orders/<order_id>', methods=['DELETE'])
def delete_payment_order_by_id(order_id):
    deleted_order = payment_orders_collection.delete_one({'_id': ObjectId(order_id)})
    if deleted_order.deleted_count:
        return jsonify({'message': 'Orden de pago eliminada exitosamente'}), 200
    else:
        return jsonify({'error': 'Orden de pago no encontrada'}), 404

@app.route('/confirmar_pago', methods=['POST'])
def confirmar_pago():
    data = request.json
    numero_de_transaccion = data.get('numero_de_transaccion')
    orden_de_pago_id = data.get('orden_de_pago_id')
    
    # Obtener los datos de la orden de pago por ID
    orden_de_pago = payment_orders_collection.find_one({'_id': ObjectId(orden_de_pago_id)})
    if not orden_de_pago:
        return jsonify({'error': 'Orden de pago no encontrada'}), 404
    
    # Buscar un mensaje de confirmación exitoso de pago en la colección messages
    mensaje_confirmacion = messages_collection.find_one({
        "numero_de_transaccion": numero_de_transaccion,
        "numero_cuenta": orden_de_pago.get('numero_cuenta'),
        "cantidad_dinero": orden_de_pago.get('cantidad_dinero'),
        "moneda": orden_de_pago.get('moneda'),
        "status": 'unconfirmed'
        # Aquí puedes agregar más criterios de coincidencia si es necesario
        # Por ejemplo, también podrías verificar el timestamp del mensaje si es importante
    })
    
    if not mensaje_confirmacion:
        return jsonify({'error': 'Mensaje de confirmación de pago no encontrado'}), 404
    
    # Si se encuentra un mensaje de confirmación, actualizar el estado de la orden de pago
    result = payment_orders_collection.update_one(
        {'_id': ObjectId(orden_de_pago_id)},
        {'$set': {'status': 'paid', 'numero_de_transaccion': numero_de_transaccion}}
    )
    
    if result.modified_count:
        # Marcar el mensaje de confirmación como confirmado
        messages_collection.update_one(
            {'_id': mensaje_confirmacion['_id']},
            {'$set': {'status': 'confirmed'}}
        )
        return jsonify({'message': 'Pago confirmado exitosamente'}), 200
    else:
        return jsonify({'error': 'No se pudo confirmar el pago'}), 400


# Iniciar la aplicación Flask
if __name__ == "__main__":
    app.run(debug=True)
