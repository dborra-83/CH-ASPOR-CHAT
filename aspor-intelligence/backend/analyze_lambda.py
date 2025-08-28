import json
import boto3
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
BEDROCK_MODEL_ID = os.environ['BEDROCK_MODEL_ID']
table = dynamodb.Table(TABLE_NAME)

def load_prompt(model_type):
    prompt_file = f"prompts/{'CONTRAGARANTIAS.txt' if model_type == 'A' else 'INFORMES_SOCIALES.txt'}"
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=prompt_file)
        return response['Body'].read().decode('utf-8')
    except:
        # Default prompts if files don't exist
        if model_type == 'A':
            return """Analiza el siguiente documento legal e identifica todas las contragarantías presentes.
Proporciona un análisis detallado que incluya:
1. Tipo de contragarantía
2. Partes involucradas
3. Condiciones específicas
4. Plazos y vigencia
5. Riesgos identificados

Documento:
"""
        else:
            return """Analiza el siguiente informe social y proporciona un resumen estructurado que incluya:
1. Situación socioeconómica actual
2. Factores de riesgo identificados
3. Recursos disponibles
4. Necesidades detectadas
5. Recomendaciones de intervención
6. Plan de acción sugerido

Informe:
"""

def handler(event, context):
    # Add CORS headers for OPTIONS requests
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'message': 'OK'})
        }
    
    try:
        body = json.loads(event['body'])
        run_id = body['runId']
        user_id = body.get('userId', 'web-user')
        model_type = body['model']  # 'A' or 'B'
        text_key = body['textKey']
        
        # Get the extracted text from S3
        response = s3.get_object(Bucket=BUCKET_NAME, Key=text_key)
        extracted_text = response['Body'].read().decode('utf-8')
        
        # Check text length
        if len(extracted_text) > 15000:
            extracted_text = extracted_text[:15000]
        
        # Get the appropriate prompt
        base_prompt = load_prompt(model_type)
        full_prompt = base_prompt + "\n" + extracted_text
        
        # First, we need to find the existing record using the GSI
        response = table.query(
            IndexName='runId-index',
            KeyConditionExpression=Key('runId').eq(run_id)
        )
        
        if not response['Items']:
            raise Exception(f"No record found for runId: {run_id}")
        
        existing_item = response['Items'][0]
        pk = existing_item['pk']
        sk = existing_item['sk']
        
        # Update status to ANALYZING using the correct keys
        timestamp = datetime.utcnow().isoformat()
        table.update_item(
            Key={
                'pk': pk,
                'sk': sk
            },
            UpdateExpression='SET #status = :status, analyzingAt = :time, model = :model',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'ANALYZING',
                ':time': timestamp,
                ':model': model_type
            }
        )
        
        # Call Bedrock with optimized settings for faster response
        bedrock_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            "max_tokens": 2000,  # Reduced for faster response
            "temperature": 0.1,   # Lower temperature for consistent output
            "top_p": 0.9
        }
        
        bedrock_response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(bedrock_request),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(bedrock_response['body'].read())
        analysis_result = response_body['content'][0]['text']
        
        # Save analysis result to S3
        analysis_key = f"analysis/{run_id}.txt"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=analysis_key,
            Body=analysis_result.encode('utf-8'),
            ContentType='text/plain'
        )
        
        # Update status to COMPLETED using the correct keys
        table.update_item(
            Key={
                'pk': pk,
                'sk': sk
            },
            UpdateExpression='SET #status = :status, bedrockResult = :result, analysisKey = :key, completedAt = :time',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'COMPLETED',
                ':result': analysis_result,
                ':key': analysis_key,
                ':time': datetime.utcnow().isoformat()
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'runId': run_id,
                'status': 'COMPLETED',
                'analysis': analysis_result,
                'model': model_type
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        
        # Update status to FAILED
        if 'run_id' in locals() and 'pk' in locals() and 'sk' in locals():
            table.update_item(
                Key={
                    'pk': pk,
                    'sk': sk
                },
                UpdateExpression='SET #status = :status, errorMessage = :error',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':status': 'FAILED',
                    ':error': str(e)
                }
            )
        elif 'run_id' in locals() and 'user_id' in locals():
            # Try to find the record if pk/sk are not available
            response = table.query(
                IndexName='runId-index',
                KeyConditionExpression=Key('runId').eq(run_id)
            )
            if response['Items']:
                item = response['Items'][0]
                table.update_item(
                    Key={
                        'pk': item['pk'],
                        'sk': item['sk']
                    },
                    UpdateExpression='SET #status = :status, errorMessage = :error',
                    ExpressionAttributeNames={
                        '#status': 'status'
                    },
                    ExpressionAttributeValues={
                        ':status': 'FAILED',
                        ':error': str(e)
                    }
                )
        
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': str(e)
            })
        }