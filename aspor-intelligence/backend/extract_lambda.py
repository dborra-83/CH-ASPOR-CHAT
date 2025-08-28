import json
import boto3
import uuid
from datetime import datetime
import os
import time
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
table = dynamodb.Table(TABLE_NAME)

def start_document_analysis(bucket, document_key):
    """Start async document analysis for PDF files"""
    try:
        response = textract.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': bucket,
                    'Name': document_key
                }
            }
        )
        return response['JobId']
    except ClientError as e:
        if 'UnsupportedDocumentException' in str(e):
            # Try with analyze_document for single page
            return None
        raise e

def get_document_analysis(job_id):
    """Get results from async document analysis"""
    max_tries = 30
    delay = 2
    
    for _ in range(max_tries):
        response = textract.get_document_text_detection(JobId=job_id)
        status = response['JobStatus']
        
        if status == 'SUCCEEDED':
            return response
        elif status == 'FAILED':
            raise Exception(f"Textract job failed: {response.get('StatusMessage', 'Unknown error')}")
        
        time.sleep(delay)
    
    raise Exception("Textract job timed out")

def extract_text_from_response(response):
    """Extract text from Textract response"""
    extracted_text = ""
    
    if 'Blocks' in response:
        blocks = response['Blocks']
    elif 'Pages' in response:
        # For async responses
        blocks = []
        for page in response.get('Pages', []):
            blocks.extend(page.get('Blocks', []))
    else:
        return ""
    
    for block in blocks:
        if block.get('BlockType') == 'LINE':
            extracted_text += block.get('Text', '') + "\n"
    
    return extracted_text

def handler(event, context):
    try:
        body = json.loads(event['body'])
        user_id = body.get('userId', 'web-user')
        file_key = body['fileKey']
        run_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Determine file type
        file_extension = file_key.lower().split('.')[-1]
        
        # Update status to EXTRACTING
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
        
        extracted_text = ""
        
        # Handle different file types
        if file_extension == 'pdf':
            # Try async document text detection for PDFs
            job_id = start_document_analysis(BUCKET_NAME, file_key)
            
            if job_id:
                # Wait for async job to complete
                response = get_document_analysis(job_id)
                extracted_text = extract_text_from_response(response)
            else:
                # Fallback to synchronous analyze_document for single-page PDFs
                try:
                    response = textract.analyze_document(
                        Document={
                            'S3Object': {
                                'Bucket': BUCKET_NAME,
                                'Name': file_key
                            }
                        },
                        FeatureTypes=['TABLES', 'FORMS']
                    )
                    extracted_text = extract_text_from_response(response)
                except Exception as e:
                    if 'UnsupportedDocumentException' in str(e):
                        # Last resort: try detect_document_text
                        response = textract.detect_document_text(
                            Document={
                                'S3Object': {
                                    'Bucket': BUCKET_NAME,
                                    'Name': file_key
                                }
                            }
                        )
                        extracted_text = extract_text_from_response(response)
                    else:
                        raise e
                        
        elif file_extension in ['png', 'jpg', 'jpeg', 'tiff', 'bmp']:
            # Use detect_document_text for images
            response = textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': BUCKET_NAME,
                        'Name': file_key
                    }
                }
            )
            extracted_text = extract_text_from_response(response)
            
        elif file_extension == 'docx':
            # For DOCX files, we need a different approach
            # For now, return a message that DOCX needs preprocessing
            extracted_text = "DOCX files require preprocessing. Please convert to PDF and try again."
            
        else:
            # Try generic text detection
            response = textract.detect_document_text(
                Document={
                    'S3Object': {
                        'Bucket': BUCKET_NAME,
                        'Name': file_key
                    }
                }
            )
            extracted_text = extract_text_from_response(response)
        
        # Check if we got any text
        if not extracted_text or len(extracted_text.strip()) == 0:
            extracted_text = "No se pudo extraer texto del documento. Por favor, verifica que el documento contiene texto legible."
        
        # Save extracted text to S3
        text_key = f"extracted/{run_id}.txt"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=text_key,
            Body=extracted_text.encode('utf-8'),
            ContentType='text/plain; charset=utf-8'
        )
        
        # Update status to EXTRACTED
        table.update_item(
            Key={
                'pk': f'USER#{user_id}',
                'sk': f'RUN#{timestamp}#{run_id}'
            },
            UpdateExpression='SET #status = :status, textExtracted = :text, textKey = :textKey, extractedAt = :time',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'EXTRACTED',
                ':text': f"{len(extracted_text)} caracteres",
                ':textKey': text_key,
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
                'status': 'EXTRACTED',
                'textLength': len(extracted_text),
                'textKey': text_key
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        error_message = str(e)
        
        # Provide more user-friendly error messages
        if 'UnsupportedDocumentException' in error_message:
            error_message = "El formato del documento no es compatible. Por favor, usa PDF, imágenes (PNG, JPG) o convierte el documento a uno de estos formatos."
        elif 'InvalidParameterException' in error_message:
            error_message = "El documento está dañado o tiene un formato inválido. Por favor, verifica el archivo."
        elif 'ProvisionedThroughputExceededException' in error_message:
            error_message = "El servicio está temporalmente sobrecargado. Por favor, intenta de nuevo en unos momentos."
        
        # Update status to FAILED
        if 'run_id' in locals() and 'user_id' in locals() and 'timestamp' in locals():
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
                    ':error': error_message
                }
            )
        
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'error': error_message
            })
        }