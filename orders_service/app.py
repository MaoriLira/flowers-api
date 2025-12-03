import json
import boto3
import uuid
import os
from datetime import datetime

# BUENA PRÁCTICA SENIOR:
# Inicializamos el cliente de DynamoDB FUERA de la función (handler).
# Esto aprovecha el "Execution Context Reuse" de Lambda para que las siguientes
# llamadas sean más rápidas (no tiene que reconectarse cada vez).
dynamodb = boto3.resource('dynamodb')

# Leemos el nombre de la tabla desde las Variables de Entorno del sistema.
# Esto evita tener "harcodeado" el nombre de la tabla en el código.
TABLE_NAME = os.environ.get('TABLE_NAME', 'FloresOrders')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Función Lambda que procesa la creación de un nuevo pedido de flores.
    """
    print(f"Procesando evento: {json.dumps(event)}") # Log para CloudWatch (Observabilidad)

    try:
        # 1. Validar que tengamos un cuerpo en la petición HTTP
        if not event.get('body'):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'El cuerpo de la petición está vacío'})
            }
        
        # Parseamos el JSON que viene del frontend/cliente
        body = json.loads(event['body'])
        
        # 2. Validación de Campos Requeridos (Business Logic)
        required_fields = ['name', 'email', 'description']
        missing_fields = [field for field in required_fields if field not in body]
        
        if missing_fields:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Faltan campos obligatorios: {", ".join(missing_fields)}'})
            }

        # 3. Construcción del Objeto de Dominio (El Pedido)
        order_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        item = {
            'orderId': order_id,            # Partition Key
            'customerName': body['name'],
            'customerEmail': body['email'],
            'customerPhone': body.get('phone', 'N/A'),
            'description': body['description'],
            'status': 'PENDIENTE',          # Estado inicial del flujo
            'createdAt': timestamp,
            'type': 'COTIZACION'
        }

        # 4. Persistencia en DynamoDB
        table.put_item(Item=item)
        print(f"Pedido guardado exitosamente: {order_id}")

        # 5. Respuesta al Cliente (201 Created)
        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                # CORS headers son importantes si conectas un frontend después
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST"
            },
            "body": json.dumps({
                "message": "Pedido creado exitosamente",
                "orderId": order_id,
                "status": "PENDIENTE",
                "timestamp": timestamp
            }),
        }

    except Exception as e:
        # Logueamos el error completo para poder depurar en CloudWatch
        print(f"ERROR CRÍTICO: {str(e)}")
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": "Error interno del servidor al procesar el pedido",
                "requestId": context.aws_request_id # Útil para rastrear el error en logs
            }),
        }