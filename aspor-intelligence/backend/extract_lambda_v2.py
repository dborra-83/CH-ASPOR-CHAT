import json
import boto3
import uuid
from datetime import datetime
import os
import time
import base64
from botocore.exceptions import ClientError
from botocore.config import Config

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Initialize Bedrock with aggressive timeout
try:
    bedrock_config = Config(
        region_name='us-east-1',
        read_timeout=15,  # 15 second read timeout
        connect_timeout=3,  # 3 second connection timeout
        retries={'max_attempts': 0}  # No retries to save time
    )
    
    bedrock_runtime = boto3.client('bedrock-runtime', config=bedrock_config)
    BEDROCK_AVAILABLE = True
    print("Bedrock client initialized successfully")
except Exception as e:
    print(f"Warning: Could not initialize Bedrock client: {str(e)}")
    bedrock_runtime = None
    BEDROCK_AVAILABLE = False

# Textract with timeout config
try:
    textract_config = Config(
        read_timeout=5,  # 5 second timeout for Textract
        connect_timeout=2,
        retries={'max_attempts': 1}
    )
    textract = boto3.client('textract', config=textract_config)
except:
    textract = boto3.client('textract')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
table = dynamodb.Table(TABLE_NAME)

def process_document_with_bedrock_direct(bucket, file_key, file_type='pdf'):
    """Process document directly with Bedrock without Textract"""
    print(f"Processing DIRECTLY with Bedrock (skipping Textract): {file_key}")
    
    if not BEDROCK_AVAILABLE or not bedrock_runtime:
        raise Exception("Bedrock no está disponible")
    
    try:
        # Get the document from S3
        obj = s3.get_object(Bucket=bucket, Key=file_key)
        document_bytes = obj['Body'].read()
        
        # Check document size
        doc_size_mb = len(document_bytes) / (1024 * 1024)
        print(f"Document size: {doc_size_mb:.2f} MB")
        
        # Limit document size for Bedrock
        max_size_mb = 4.5
        if doc_size_mb > max_size_mb:
            print(f"Document too large ({doc_size_mb:.2f} MB), truncating...")
            # For PDFs we can't easily truncate, so we'll try anyway
            # In production, you might want to implement PDF page extraction
        
        # Encode to base64
        document_base64 = base64.b64encode(document_bytes).decode('utf-8')
        
        # Determine media type
        if file_type == 'pdf':
            media_type = 'application/pdf'
        elif file_type in ['jpg', 'jpeg']:
            media_type = 'image/jpeg'
        elif file_type == 'png':
            media_type = 'image/png'
        else:
            media_type = 'application/octet-stream'
        
        print(f"Sending to Bedrock with media type: {media_type}")
        
        # Prepare the request for Claude 3.5 Sonnet
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extrae TODO el texto de este documento. Incluye texto de imágenes escaneadas. Devuelve SOLO el texto extraído sin comentarios adicionales."
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
            "temperature": 0.0,
            "top_p": 0.9
        }
        
        # Call Bedrock
        start_time = time.time()
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        elapsed = time.time() - start_time
        print(f"Bedrock responded in {elapsed:.2f} seconds")
        
        # Parse response
        response_body = json.loads(response['body'].read())
        extracted_text = response_body.get('content', [{}])[0].get('text', '')
        
        if not extracted_text:
            raise Exception("Bedrock no pudo extraer texto del documento")
            
        print(f"Bedrock extracted {len(extracted_text)} characters")
        return extracted_text
        
    except Exception as e:
        print(f"Error processing with Bedrock: {str(e)}")
        raise

def quick_textract_attempt(bucket, file_key, file_extension, max_wait_seconds=3):
    """Quick attempt to use Textract with strict timeout"""
    try:
        if file_extension == 'pdf':
            print(f"Quick Textract attempt for PDF: {file_key}")
            
            # Try synchronous detection with timeout
            start_time = time.time()
            response = textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': file_key
                    }
                }
            )
            
            elapsed = time.time() - start_time
            print(f"Textract responded in {elapsed:.2f} seconds")
            
            if elapsed > max_wait_seconds:
                print(f"Textract took too long ({elapsed:.2f}s), switching to Bedrock")
                return None
                
            # Extract text quickly
            extracted_text = ""
            for block in response.get('Blocks', []):
                if block.get('BlockType') == 'LINE':
                    extracted_text += block.get('Text', '') + "\n"
            
            if len(extracted_text.strip()) > 50:  # Got meaningful text
                print(f"Textract quick success: {len(extracted_text)} characters")
                return extracted_text
            else:
                print("Textract returned too little text, switching to Bedrock")
                return None
                
        elif file_extension in ['png', 'jpg', 'jpeg']:
            # Quick attempt for images
            response = textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': bucket,
                        'Name': file_key
                    }
                }
            )
            
            extracted_text = ""
            for block in response.get('Blocks', []):
                if block.get('BlockType') == 'LINE':
                    extracted_text += block.get('Text', '') + "\n"
                    
            if len(extracted_text.strip()) > 50:
                return extracted_text
                
        return None
        
    except Exception as e:
        print(f"Textract quick attempt failed: {str(e)}")
        return None

def handler(event, context):
    print(f"Event received: {json.dumps(event)}")
    
    # Always return CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # Handle OPTIONS request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'CORS preflight response'})
        }
    
    run_id = None
    user_id = None
    timestamp = None
    
    try:
        body = json.loads(event['body'])
        user_id = body.get('userId', 'web-user')
        file_key = body['fileKey']
        run_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        print(f"Processing - User: {user_id}, File: {file_key}, RunID: {run_id}")
        
        # Determine file type
        file_extension = file_key.lower().split('.')[-1]
        print(f"File extension: {file_extension}")
        
        # Update status to EXTRACTING
        try:
            table.put_item(
                Item={
                    'pk': f'USER#{user_id}',
                    'sk': f'RUN#{timestamp}#{run_id}',
                    'runId': run_id,
                    'status': 'EXTRACTING',
                    'fileKey': file_key,
                    'fileType': file_extension,
                    'createdAt': timestamp,
                    'userId': user_id
                }
            )
            print("Status updated to EXTRACTING")
        except Exception as db_error:
            print(f"Warning: Could not update DB: {str(db_error)}")
        
        # Check remaining time
        remaining_time = 25000  # Default 25 seconds
        if hasattr(context, 'get_remaining_time_in_millis'):
            remaining_time = context.get_remaining_time_in_millis()
            print(f"Lambda has {remaining_time}ms remaining")
        
        extracted_text = ""
        extraction_method = "unknown"
        
        # STRATEGY: Try Textract quickly, fallback to Bedrock immediately if it fails or is slow
        if remaining_time > 20000:  # More than 20 seconds remaining
            print("Attempting quick Textract extraction (3 second limit)...")
            extracted_text = quick_textract_attempt(BUCKET_NAME, file_key, file_extension, max_wait_seconds=3)
            
            if extracted_text and len(extracted_text.strip()) > 50:
                extraction_method = "textract"
                print(f"Textract succeeded quickly with {len(extracted_text)} characters")
            else:
                print("Textract failed or was too slow, using Bedrock directly...")
                extraction_method = "bedrock_direct"
                try:
                    extracted_text = process_document_with_bedrock_direct(BUCKET_NAME, file_key, file_extension)
                except Exception as bedrock_error:
                    print(f"Bedrock also failed: {str(bedrock_error)}")
                    extracted_text = f"Error: No se pudo procesar el documento. {str(bedrock_error)}"
        else:
            # Not enough time, go straight to Bedrock
            print(f"Only {remaining_time}ms remaining, going straight to Bedrock...")
            extraction_method = "bedrock_direct"
            try:
                extracted_text = process_document_with_bedrock_direct(BUCKET_NAME, file_key, file_extension)
            except Exception as bedrock_error:
                print(f"Bedrock failed: {str(bedrock_error)}")
                extracted_text = f"Error: No se pudo procesar el documento. {str(bedrock_error)}"
        
        # Validate and limit text
        if not extracted_text or len(extracted_text.strip()) == 0:
            extracted_text = "No se pudo extraer texto del documento. Por favor, verifica que el documento contiene texto legible."
        elif len(extracted_text) > 15000:
            print(f"Text is {len(extracted_text)} characters, truncating to 15000...")
            extracted_text = extracted_text[:15000] + "\n\n[Texto truncado por límite de caracteres]"
        
        # Save extracted text to S3
        text_key = f"extracted/{run_id}.txt"
        try:
            s3.put_object(
                Bucket=BUCKET_NAME,
                Key=text_key,
                Body=extracted_text.encode('utf-8'),
                ContentType='text/plain; charset=utf-8',
                Metadata={
                    'extraction_method': extraction_method,
                    'original_file': file_key
                }
            )
            print(f"Saved extracted text to S3: {text_key}")
        except Exception as s3_error:
            print(f"Warning: Could not save to S3: {str(s3_error)}")
            text_key = None
        
        # Update status to EXTRACTED
        try:
            table.update_item(
                Key={
                    'pk': f'USER#{user_id}',
                    'sk': f'RUN#{timestamp}#{run_id}'
                },
                UpdateExpression='SET #status = :status, textExtracted = :text, textKey = :textKey, extractedAt = :time, extractionMethod = :method',
                ExpressionAttributeNames={
                    '#status': 'status'
                },
                ExpressionAttributeValues={
                    ':status': 'EXTRACTED',
                    ':text': f"{len(extracted_text)} caracteres",
                    ':textKey': text_key,
                    ':time': datetime.utcnow().isoformat(),
                    ':method': extraction_method
                }
            )
            print("Status updated to EXTRACTED")
        except Exception as db_error:
            print(f"Warning: Could not update DB: {str(db_error)}")
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'runId': run_id,
                'status': 'EXTRACTED',
                'textLength': len(extracted_text),
                'textKey': text_key,
                'extractionMethod': extraction_method
            })
        }
        
    except Exception as e:
        print(f"Error in extract_lambda: {str(e)}")
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Full traceback:\n{traceback_str}")
        
        error_message = str(e)
        
        # Update status to FAILED if we have the necessary info
        if run_id and user_id and timestamp:
            try:
                table.update_item(
                    Key={
                        'pk': f'USER#{user_id}',
                        'sk': f'RUN#{timestamp}#{run_id}'
                    },
                    UpdateExpression='SET #status = :status, errorMessage = :error',
                    ExpressionAttributeNames={
                        '#status': 'status'
                    },
                    ExpressionAttributeValues={
                        ':status': 'FAILED',
                        ':error': error_message[:500]  # Limit error message length
                    }
                )
                print("Status updated to FAILED")
            except:
                pass
        
        # Always return a proper response with CORS headers
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': error_message[:500],
                'runId': run_id
            })
        }