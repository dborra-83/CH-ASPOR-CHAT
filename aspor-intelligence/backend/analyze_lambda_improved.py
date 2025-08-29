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

def update_process_tracking(pk, sk, step_name, success=True, details=None):
    """Update DynamoDB with process tracking information"""
    try:
        update_expr = f"SET step_{step_name} = :status, step_{step_name}_time = :time"
        expr_values = {
            ':status': success,
            ':time': datetime.utcnow().isoformat()
        }
        
        if details:
            update_expr += f", step_{step_name}_details = :details"
            expr_values[':details'] = details[:500]  # Limit details length
            
        table.update_item(
            Key={'pk': pk, 'sk': sk},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values
        )
        print(f"Updated tracking: step_{step_name} = {success}")
    except Exception as e:
        print(f"Could not update tracking for {step_name}: {str(e)}")

def handler(event, context):
    print(f"Analyze Lambda received event: {json.dumps(event)}")
    
    # CORS headers for all responses
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'OK'})
        }
    
    pk = None
    sk = None
    
    try:
        body = json.loads(event['body'])
        run_id = body['runId']
        user_id = body.get('userId', 'web-user')
        model_type = body['model']  # 'A' or 'B'
        text_key = body.get('textKey')
        
        print(f"Processing: runId={run_id}, userId={user_id}, model={model_type}, textKey={text_key}")
        
        # Find the existing record
        print(f"Looking for record with runId: {run_id}")
        response = table.query(
            IndexName='runId-index',
            KeyConditionExpression=Key('runId').eq(run_id)
        )
        
        if response['Items']:
            existing_item = response['Items'][0]
            pk = existing_item['pk']
            sk = existing_item['sk']
            print(f"Found record: pk={pk}, sk={sk}")
        else:
            print(f"No record found for runId: {run_id}, creating new tracking")
            pk = f'USER#{user_id}'
            sk = f'RUN#{datetime.utcnow().isoformat()}#{run_id}'
            existing_item = {}
        
        # Update status to ANALYZING
        update_process_tracking(pk, sk, 'analysis_started', True, f"Model: {model_type}")
        
        # Get the extracted text
        extracted_text = None
        text_source = "unknown"
        
        # Method 1: Try to get from S3 if text_key is provided
        if text_key:
            print(f"Attempting to get text from S3: {BUCKET_NAME}/{text_key}")
            try:
                response = s3.get_object(Bucket=BUCKET_NAME, Key=text_key)
                extracted_text = response['Body'].read().decode('utf-8')
                text_source = "s3"
                print(f"Successfully loaded text from S3, length: {len(extracted_text)}")
                update_process_tracking(pk, sk, 'text_loaded_from_s3', True, f"Length: {len(extracted_text)}")
            except Exception as s3_error:
                print(f"Could not load from S3: {str(s3_error)}")
                update_process_tracking(pk, sk, 'text_loaded_from_s3', False, str(s3_error)[:200])
        
        # Method 2: If no text yet, check if it's in the DynamoDB record
        if not extracted_text and existing_item:
            if 'textExtracted' in existing_item:
                text_content = existing_item['textExtracted']
                # Check if it's just a length indicator like "1234 caracteres"
                if 'caracteres' in text_content:
                    print(f"Text in DB is just a length indicator: {text_content}")
                else:
                    extracted_text = text_content
                    text_source = "dynamodb"
                    print(f"Using text from DynamoDB, length: {len(extracted_text)}")
                    update_process_tracking(pk, sk, 'text_loaded_from_db', True, f"Length: {len(extracted_text)}")
        
        # Method 3: If still no text, try to reconstruct the text_key
        if not extracted_text and not text_key:
            reconstructed_key = f"extracted/{run_id}.txt"
            print(f"No text_key provided, trying reconstructed key: {reconstructed_key}")
            try:
                response = s3.get_object(Bucket=BUCKET_NAME, Key=reconstructed_key)
                extracted_text = response['Body'].read().decode('utf-8')
                text_source = "s3_reconstructed"
                print(f"Successfully loaded text from reconstructed S3 key, length: {len(extracted_text)}")
                update_process_tracking(pk, sk, 'text_loaded_reconstructed', True, f"Length: {len(extracted_text)}")
            except Exception as recon_error:
                print(f"Could not load from reconstructed key: {str(recon_error)}")
                update_process_tracking(pk, sk, 'text_loaded_reconstructed', False, str(recon_error)[:200])
        
        # Validate that we have text
        if not extracted_text or len(extracted_text.strip()) < 10:
            error_msg = f"No valid text available for analysis. Text source attempted: {text_source}, Length: {len(extracted_text) if extracted_text else 0}"
            print(f"ERROR: {error_msg}")
            
            # Check if the text contains an error message
            if extracted_text and extracted_text.startswith("Error:"):
                error_msg = f"Extraction failed: {extracted_text}"
            
            update_process_tracking(pk, sk, 'text_validation', False, error_msg)
            raise Exception(error_msg)
        
        update_process_tracking(pk, sk, 'text_validation', True, f"Valid text from {text_source}")
        
        # Truncate if too long
        if len(extracted_text) > 15000:
            print(f"Truncating text from {len(extracted_text)} to 15000 characters")
            extracted_text = extracted_text[:15000]
        
        # Prepare the prompt
        base_prompt = load_prompt(model_type)
        full_prompt = base_prompt + "\n\nTexto del documento:\n" + extracted_text
        
        print(f"Prepared prompt: base={len(base_prompt)} chars, text={len(extracted_text)} chars, total={len(full_prompt)} chars")
        
        # Update status
        table.update_item(
            Key={'pk': pk, 'sk': sk},
            UpdateExpression='SET #status = :status, analyzingAt = :time, model = :model',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'ANALYZING',
                ':time': datetime.utcnow().isoformat(),
                ':model': model_type
            }
        )
        
        # Call Bedrock
        print(f"Calling Bedrock model: {BEDROCK_MODEL_ID}")
        update_process_tracking(pk, sk, 'bedrock_called', True, f"Model: {BEDROCK_MODEL_ID}")
        
        bedrock_request = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ],
            "max_tokens": 4000,  # Increased for detailed analysis
            "temperature": 0.1,
            "top_p": 0.9
        }
        
        try:
            bedrock_response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps(bedrock_request),
                contentType='application/json',
                accept='application/json'
            )
            
            response_body = json.loads(bedrock_response['body'].read())
            analysis_result = response_body['content'][0]['text']
            
            print(f"Bedrock responded successfully with {len(analysis_result)} characters")
            update_process_tracking(pk, sk, 'bedrock_response', True, f"Response length: {len(analysis_result)}")
            
        except Exception as bedrock_error:
            print(f"Bedrock call failed: {str(bedrock_error)}")
            update_process_tracking(pk, sk, 'bedrock_response', False, str(bedrock_error)[:200])
            raise Exception(f"Error calling Bedrock: {str(bedrock_error)}")
        
        # Save analysis result to S3
        analysis_key = f"analysis/{run_id}.txt"
        try:
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=analysis_key,
                Body=analysis_result.encode('utf-8'),
                ContentType='text/plain'
            )
            print(f"Saved analysis to S3: {analysis_key}")
            update_process_tracking(pk, sk, 'analysis_saved', True, analysis_key)
        except Exception as save_error:
            print(f"Could not save analysis to S3: {str(save_error)}")
            update_process_tracking(pk, sk, 'analysis_saved', False, str(save_error)[:200])
        
        # Update final status
        table.update_item(
            Key={'pk': pk, 'sk': sk},
            UpdateExpression='SET #status = :status, bedrockResult = :result, analysisKey = :key, completedAt = :time, step_result_delivered = :delivered',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'COMPLETED',
                ':result': analysis_result[:1000] if len(analysis_result) > 1000 else analysis_result,  # Store preview
                ':key': analysis_key,
                ':time': datetime.utcnow().isoformat(),
                ':delivered': True
            }
        )
        
        print(f"Analysis complete, returning {len(analysis_result)} characters")
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'runId': run_id,
                'status': 'COMPLETED',
                'analysis': analysis_result,
                'model': model_type,
                'textSource': text_source
            })
        }
        
    except Exception as e:
        import traceback
        print(f"Error in analyze_lambda: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        
        # Update failure tracking
        if pk and sk:
            update_process_tracking(pk, sk, 'analysis_failed', False, str(e)[:200])
            
            try:
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
            except:
                print("Could not update DB with failure status")
        
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': str(e),
                'runId': body.get('runId') if 'body' in locals() else None
            })
        }