import json
import boto3
import os
import base64
from datetime import datetime
from boto3.dynamodb.conditions import Key
from botocore.config import Config

# Initialize clients with timeout config
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Bedrock with config
bedrock_config = Config(
    region_name='us-east-1',
    read_timeout=25,
    connect_timeout=5,
    retries={'max_attempts': 0}
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

def analyze_with_document_vision(file_key, model_type):
    """Analyze document directly with Bedrock Vision"""
    print(f"Analyzing document directly with Bedrock Vision: {file_key}")
    
    try:
        # Get the original document from S3
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
        document_bytes = obj['Body'].read()
        
        # Check size
        doc_size_mb = len(document_bytes) / (1024 * 1024)
        print(f"Document size: {doc_size_mb:.2f} MB")
        
        if doc_size_mb > 4.5:
            print(f"Document too large, will try anyway")
        
        # Encode to base64
        document_base64 = base64.b64encode(document_bytes).decode('utf-8')
        
        # Determine media type from file extension
        file_extension = file_key.lower().split('.')[-1]
        if file_extension == 'pdf':
            media_type = 'application/pdf'
        elif file_extension in ['jpg', 'jpeg']:
            media_type = 'image/jpeg'
        elif file_extension == 'png':
            media_type = 'image/png'
        else:
            media_type = 'application/octet-stream'
        
        print(f"Using media type: {media_type}")
        
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
                            "type": "image" if 'image' in media_type else "document",
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
        
        # Call Bedrock
        print("Calling Bedrock with document vision...")
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        analysis_result = response_body['content'][0]['text']
        
        print(f"Bedrock Vision analysis complete: {len(analysis_result)} characters")
        return analysis_result
        
    except Exception as e:
        print(f"Error in document vision analysis: {str(e)}")
        raise

def handler(event, context):
    print(f"Analyze Lambda received: {json.dumps(event)}")
    
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'OK'})
        }
    
    try:
        body = json.loads(event['body'])
        run_id = body['runId']
        user_id = body.get('userId', 'web-user')
        model_type = body['model']
        text_key = body.get('textKey')
        
        print(f"Processing: runId={run_id}, model={model_type}, textKey={text_key}")
        
        # Find the record in DynamoDB
        response = table.query(
            IndexName='runId-index',
            KeyConditionExpression=Key('runId').eq(run_id)
        )
        
        if response['Items']:
            item = response['Items'][0]
            pk = item['pk']
            sk = item['sk']
            original_file_key = item.get('fileKey')  # Get original file key
            print(f"Found record with original file: {original_file_key}")
        else:
            print(f"No record found for runId: {run_id}")
            pk = f'USER#{user_id}'
            sk = f'RUN#{datetime.utcnow().isoformat()}#{run_id}'
            item = {}
            original_file_key = None
        
        # Try to get extracted text first
        extracted_text = None
        use_vision = False
        
        if text_key:
            try:
                print(f"Trying to load text from S3: {text_key}")
                obj = s3.get_object(Bucket=BUCKET_NAME, Key=text_key)
                extracted_text = obj['Body'].read().decode('utf-8')
                print(f"Loaded {len(extracted_text)} characters from S3")
                
                # Check if text is valid
                if extracted_text.startswith("Error:") or len(extracted_text.strip()) < 100:
                    print(f"Text seems invalid or too short, will use document vision")
                    use_vision = True
                    
            except Exception as e:
                print(f"Could not load text: {str(e)}")
                use_vision = True
        else:
            print("No text_key provided, will use document vision")
            use_vision = True
        
        # If no valid text or text is too short, use document vision with original file
        if use_vision and original_file_key:
            print(f"Using Bedrock Vision with original document: {original_file_key}")
            
            try:
                analysis_result = analyze_with_document_vision(original_file_key, model_type)
                
                # Update status
                table.update_item(
                    Key={'pk': pk, 'sk': sk},
                    UpdateExpression='SET #status = :status, analysisMethod = :method, completedAt = :time',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': 'COMPLETED',
                        ':method': 'bedrock_vision_direct',
                        ':time': datetime.utcnow().isoformat()
                    }
                )
                
                print(f"Analysis complete with vision: {len(analysis_result)} characters")
                
                return {
                    'statusCode': 200,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'runId': run_id,
                        'status': 'COMPLETED',
                        'analysis': analysis_result,
                        'model': model_type,
                        'method': 'document_vision'
                    })
                }
                
            except Exception as vision_error:
                print(f"Vision analysis failed: {str(vision_error)}")
                # Fall back to text if available
                if not extracted_text:
                    raise vision_error
        
        # Use extracted text for analysis (fallback or primary)
        if extracted_text and len(extracted_text.strip()) > 50:
            print(f"Using extracted text for analysis: {len(extracted_text)} characters")
            
            base_prompt = load_prompt(model_type)
            full_prompt = base_prompt + "\n\n" + extracted_text
            
            # Call Bedrock with text
            bedrock_request = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                "max_tokens": 10000,
                "temperature": 0.1,
                "top_p": 0.9
            }
            
            response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps(bedrock_request),
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(response['body'].read())
            analysis_result = response_body['content'][0]['text']
            
            # Update status
            table.update_item(
                Key={'pk': pk, 'sk': sk},
                UpdateExpression='SET #status = :status, analysisMethod = :method, completedAt = :time',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'COMPLETED',
                    ':method': 'text_analysis',
                    ':time': datetime.utcnow().isoformat()
                }
            )
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'runId': run_id,
                    'status': 'COMPLETED',
                    'analysis': analysis_result,
                    'model': model_type,
                    'method': 'text_analysis'
                })
            }
        else:
            raise Exception("No valid text or document available for analysis")
            
    except Exception as e:
        import traceback
        print(f"Error: {str(e)}")
        print(traceback.format_exc())
        
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': str(e),
                'runId': body.get('runId') if 'body' in locals() else None
            })
        }