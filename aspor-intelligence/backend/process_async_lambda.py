import json
import boto3
import os
import base64
from datetime import datetime
from boto3.dynamodb.conditions import Key
from botocore.config import Config

# Initialize clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
stepfunctions = boto3.client('stepfunctions')

# Bedrock with extended timeout for async processing
bedrock_config = Config(
    region_name='us-east-1',
    read_timeout=120,  # 2 minutes for async processing
    connect_timeout=10,
    retries={'max_attempts': 1}
)
bedrock = boto3.client('bedrock-runtime', config=bedrock_config)

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
BEDROCK_MODEL_ID = os.environ['BEDROCK_MODEL_ID']
table = dynamodb.Table(TABLE_NAME)

def load_prompt(model_type):
    """Load the appropriate prompt for the model type"""
    prompt_file = f"prompts/{'CONTRAGARANTIAS.txt' if model_type == 'A' else 'INFORMES_SOCIALES.txt'}"
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=prompt_file)
        return response['Body'].read().decode('utf-8')
    except:
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
    """Async processor for document analysis - runs in background"""
    print(f"Async processor started: {json.dumps(event)}")
    
    run_id = event['runId']
    model_type = event['model']
    user_id = event.get('userId', 'web-user')
    
    try:
        # Find the record in DynamoDB
        response = table.query(
            IndexName='runId-index',
            KeyConditionExpression=Key('runId').eq(run_id)
        )
        
        if not response['Items']:
            raise Exception(f"No record found for runId: {run_id}")
        
        item = response['Items'][0]
        pk = item['pk']
        sk = item['sk']
        file_key = item.get('fileKey')
        
        if not file_key:
            raise Exception("No fileKey found in record")
        
        print(f"Processing document: {file_key}")
        
        # Update status to PROCESSING
        table.update_item(
            Key={'pk': pk, 'sk': sk},
            UpdateExpression='SET #status = :status, asyncProcessingStarted = :time',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'PROCESSING_ASYNC',
                ':time': datetime.utcnow().isoformat()
            }
        )
        
        # Get document from S3
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
        document_bytes = obj['Body'].read()
        doc_size_mb = len(document_bytes) / (1024 * 1024)
        print(f"Document size: {doc_size_mb:.2f} MB")
        
        # Encode to base64
        document_base64 = base64.b64encode(document_bytes).decode('utf-8')
        
        # Determine media type
        file_extension = file_key.lower().split('.')[-1]
        media_types = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png'
        }
        media_type = media_types.get(file_extension, 'application/octet-stream')
        
        # Get the prompt
        base_prompt = load_prompt(model_type)
        
        # Prepare Bedrock request with document
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 10000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": base_prompt + "\n\nPor favor analiza el documento adjunto:"
                        },
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": document_base64
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.1,
            "top_p": 0.9
        }
        
        # Call Bedrock (with extended timeout)
        print("Calling Bedrock with document vision...")
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        analysis_result = response_body['content'][0]['text']
        
        print(f"Bedrock analysis complete: {len(analysis_result)} characters")
        
        # Save analysis to S3
        analysis_key = f"analysis/{run_id}.txt"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=analysis_key,
            Body=analysis_result.encode('utf-8'),
            ContentType='text/plain'
        )
        
        # Update status to COMPLETED
        table.update_item(
            Key={'pk': pk, 'sk': sk},
            UpdateExpression='SET #status = :status, analysisMethod = :method, completedAt = :time, analysisResult = :result',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'COMPLETED',
                ':method': 'async_bedrock_vision',
                ':time': datetime.utcnow().isoformat(),
                ':result': analysis_result[:5000]  # Store preview (5k chars)
            }
        )
        
        print(f"Async processing completed successfully for {run_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'runId': run_id,
                'status': 'COMPLETED',
                'analysisLength': len(analysis_result)
            })
        }
        
    except Exception as e:
        print(f"Error in async processing: {str(e)}")
        
        # Update status to FAILED
        if 'pk' in locals() and 'sk' in locals():
            table.update_item(
                Key={'pk': pk, 'sk': sk},
                UpdateExpression='SET #status = :status, errorMessage = :error, failedAt = :time',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'FAILED',
                    ':error': str(e)[:500],
                    ':time': datetime.utcnow().isoformat()
                }
            )
        
        raise