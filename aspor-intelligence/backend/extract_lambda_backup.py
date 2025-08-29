import json
import boto3
import uuid
from datetime import datetime
import os
import time
import base64
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
textract = boto3.client('textract')
dynamodb = boto3.resource('dynamodb')

# Initialize Bedrock client with error handling
try:
    # Use config for faster timeouts
    from botocore.config import Config
    
    bedrock_config = Config(
        region_name='us-east-1',
        read_timeout=20,  # 20 second read timeout
        connect_timeout=5,  # 5 second connection timeout
        retries={'max_attempts': 1}  # Minimize retries
    )
    
    bedrock_runtime = boto3.client('bedrock-runtime', config=bedrock_config)
    BEDROCK_AVAILABLE = True
    print("Bedrock client initialized successfully")
except Exception as e:
    print(f"Warning: Could not initialize Bedrock client: {str(e)}")
    bedrock_runtime = None
    BEDROCK_AVAILABLE = False

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
    max_tries = 5  # Further reduced
    initial_delay = 0.5  # Start faster
    max_delay = 1.5  # Faster polling
    
    for attempt in range(max_tries):
        try:
            response = textract.get_document_text_detection(JobId=job_id)
            status = response['JobStatus']
            
            if status == 'SUCCEEDED':
                print(f"Textract job succeeded after {attempt + 1} attempts")
                return response
            elif status == 'FAILED':
                error_msg = response.get('StatusMessage', 'Unknown error')
                print(f"Textract job failed: {error_msg}")
                raise Exception(f"OCR failed: {error_msg}")
            
            # Log progress for debugging
            print(f"Attempt {attempt + 1}/{max_tries}: Job status is {status}")
            
            # Progressive delay - starts fast, slows down
            delay = min(initial_delay * (1.5 ** attempt), max_delay)
            time.sleep(delay)
            
        except ClientError as e:
            print(f"Error checking job status: {str(e)}")
            if attempt == max_tries - 1:
                raise
            time.sleep(2)
    
    print(f"Textract job {job_id} timed out after {max_tries} attempts")
    raise Exception("El procesamiento está tardando demasiado. Por favor, intente con un documento más pequeño o inténtelo nuevamente.")

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

def process_with_bedrock_vision(bucket, file_key, file_type='pdf'):
    """Process document directly with Bedrock Claude Vision when Textract fails"""
    print(f"Processing with Bedrock Vision: {file_key}")
    
    if not BEDROCK_AVAILABLE or not bedrock_runtime:
        print("Bedrock is not available, skipping vision processing")
        raise Exception("Bedrock Vision no está disponible")
    
    try:
        # Get the document from S3
        obj = s3.get_object(Bucket=bucket, Key=file_key)
        document_bytes = obj['Body'].read()
        
        # Check document size
        doc_size_mb = len(document_bytes) / (1024 * 1024)
        print(f"Document size: {doc_size_mb:.2f} MB")
        
        # If document is too large, sample first pages
        if doc_size_mb > 2:  # Lower threshold for faster processing
            print(f"Document large ({doc_size_mb:.2f} MB), processing first pages only")
            # For PDFs, we can't easily extract pages here, so return async message
            raise Exception("Documento grande requiere procesamiento especial")
        
        # Encode document to base64
        document_base64 = base64.b64encode(document_bytes).decode('utf-8')
        
        # Determine media type
        media_type = 'application/pdf' if file_type == 'pdf' else f'image/{file_type}'
        if file_type == 'jpg':
            media_type = 'image/jpeg'
        
        # Ultra-concise prompt for speed
        prompt = """Extrae el texto del documento. Solo el texto, sin comentarios."""
        
        # Prepare the request for Claude 3 Haiku (faster and cheaper for OCR)
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,  # Further reduced for faster response
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
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
        
        # Call Bedrock with Claude Sonnet 3.5
        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        extracted_text = response_body.get('content', [{}])[0].get('text', '')
        
        print(f"Bedrock Vision extracted {len(extracted_text)} characters")
        return extracted_text
        
    except Exception as e:
        print(f"Error processing with Bedrock Vision: {str(e)}")
        raise Exception(f"No se pudo procesar el documento con visión AI: {str(e)}")

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
    
    try:
        body = json.loads(event['body'])
        user_id = body.get('userId', 'web-user')
        file_key = body['fileKey']
        run_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        print(f"Processing request - User: {user_id}, File: {file_key}, RunID: {run_id}")
        
        # Determine file type
        file_extension = file_key.lower().split('.')[-1]
        print(f"File extension detected: {file_extension}")
        
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
            print(f"Status updated to EXTRACTING in DynamoDB")
        except Exception as db_error:
            print(f"Error updating DynamoDB status: {str(db_error)}")
            # Continue processing even if DB update fails
        
        extracted_text = ""
        
        # Handle different file types
        if file_extension == 'pdf':
            print(f"Processing PDF file: {file_key}")
            
            # Check file size first (optional - for optimization)
            try:
                head_obj = s3.head_object(Bucket=BUCKET_NAME, Key=file_key)
                file_size = head_obj['ContentLength']
                print(f"PDF file size: {file_size} bytes")
            except:
                file_size = 0
            
            # First, try synchronous processing (faster for small PDFs)
            try:
                print("Attempting synchronous text detection...")
                response = textract.detect_document_text(
                    Document={
                        'S3Object': {
                            'Bucket': BUCKET_NAME,
                            'Name': file_key
                        }
                    }
                )
                extracted_text = extract_text_from_response(response)
                print(f"Synchronous processing succeeded, extracted {len(extracted_text)} characters")
                
                # If no text was extracted, it might be a scanned image PDF
                if len(extracted_text.strip()) < 10:
                    print("Very little text extracted, trying OCR methods...")
                    raise Exception("Insufficient text - trying alternative methods")
                    
            except Exception as sync_error:
                print(f"Synchronous processing failed: {str(sync_error)}")
                
                # If sync fails, try async processing
                try:
                    print("Attempting asynchronous processing...")
                    job_id = start_document_analysis(BUCKET_NAME, file_key)
                    
                    if job_id:
                        print(f"Started async job: {job_id}")
                        response = get_document_analysis(job_id)
                        extracted_text = extract_text_from_response(response)
                        print(f"Async processing succeeded, extracted {len(extracted_text)} characters")
                        
                        # Check if text was actually extracted
                        if len(extracted_text.strip()) < 10:
                            print("Async extracted very little text, trying alternative methods...")
                            raise Exception("Insufficient text - trying alternative methods")
                    else:
                        raise Exception("Could not start async processing")
                        
                except Exception as async_error:
                    print(f"Async processing also failed: {str(async_error)}")
                    # Try analyze_document with OCR features
                    try:
                        print("Attempting analyze_document with OCR features...")
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
                        print(f"Analyze document succeeded, extracted {len(extracted_text)} characters")
                        
                        # Final check for scanned content
                        if len(extracted_text.strip()) < 10:
                            print("Still insufficient text, PDF likely contains scanned images")
                            raise Exception("PDF contains scanned images")
                            
                    except Exception as textract_final_error:
                        print(f"All Textract methods failed: {str(textract_final_error)}")
                        
                        # FALLBACK TO BEDROCK VISION FOR SCANNED PDFS
                        if BEDROCK_AVAILABLE:
                            try:
                                print("Falling back to Bedrock Vision for PDF processing...")
                                # Store a flag that Bedrock is needed
                                extracted_text = "[BEDROCK_PROCESSING_REQUIRED]"
                                print("Marking document for async Bedrock processing")
                                
                                # Actually try Bedrock but with timeout awareness
                                try:
                                    import time
                                    start_time = time.time()
                                    
                                    # Check remaining time in Lambda context
                                    if hasattr(context, 'get_remaining_time_in_millis'):
                                        remaining_time = context.get_remaining_time_in_millis()
                                        if remaining_time < 15000:  # Less than 15 seconds remaining
                                            print(f"Only {remaining_time}ms remaining, returning async response")
                                            # Mark for async processing
                                            extracted_text = "[ASYNC_PROCESSING_REQUIRED]"
                                            
                                            # Update DB to indicate async processing
                                            table.update_item(
                                                Key={
                                                    'pk': f'USER#{user_id}',
                                                    'sk': f'RUN#{timestamp}#{run_id}'
                                                },
                                                UpdateExpression='SET #status = :status, processingType = :type',
                                                ExpressionAttributeNames={'#status': 'status'},
                                                ExpressionAttributeValues={
                                                    ':status': 'PROCESSING_ASYNC',
                                                    ':type': 'BEDROCK_VISION'
                                                }
                                            )
                                            
                                            # Return early with async status
                                            return {
                                                'statusCode': 202,  # Accepted for processing
                                                'headers': cors_headers,
                                                'body': json.dumps({
                                                    'runId': run_id,
                                                    'status': 'PROCESSING_ASYNC',
                                                    'message': 'El documento contiene imágenes escaneadas y está siendo procesado. Por favor, espere unos momentos.',
                                                    'estimatedTime': 30
                                                })
                                            }
                                        else:
                                            # Try Bedrock with quick timeout
                                            extracted_text = process_with_bedrock_vision(BUCKET_NAME, file_key, 'pdf')
                                    else:
                                        # Try with a time limit
                                        extracted_text = process_with_bedrock_vision(BUCKET_NAME, file_key, 'pdf')
                                    
                                    elapsed = time.time() - start_time
                                    print(f"Bedrock processing took {elapsed:.2f} seconds")
                                    
                                except Exception as timeout_error:
                                    print(f"Bedrock processing error/timeout: {str(timeout_error)}")
                                    extracted_text = "El procesamiento del documento está tardando más de lo esperado. El documento parece contener imágenes escaneadas complejas."
                                
                                if not extracted_text or len(extracted_text.strip()) < 10:
                                    raise Exception("Bedrock también falló en extraer texto del documento")
                                    
                            except Exception as bedrock_error:
                                print(f"Bedrock Vision also failed: {str(bedrock_error)}")
                                raise Exception(f"No se pudo procesar el PDF. El documento puede contener imágenes escaneadas o estar en un formato no compatible.")
                        else:
                            print("Bedrock not available, cannot process scanned PDFs")
                            raise Exception(f"No se pudo procesar el PDF. El documento parece contener imágenes escaneadas y el procesamiento avanzado no está disponible.")
                        
        elif file_extension in ['png', 'jpg', 'jpeg', 'tiff', 'bmp']:
            # Use detect_document_text for images
            try:
                response = textract.detect_document_text(
                    Document={
                        'S3Object': {
                            'Bucket': BUCKET_NAME,
                            'Name': file_key
                        }
                    }
                )
                extracted_text = extract_text_from_response(response)
                
                # If no text extracted from image, try Bedrock Vision
                if len(extracted_text.strip()) < 10 and BEDROCK_AVAILABLE:
                    print(f"Textract extracted little text from image, trying Bedrock Vision...")
                    extracted_text = process_with_bedrock_vision(BUCKET_NAME, file_key, file_extension)
                    
            except Exception as img_error:
                print(f"Image processing with Textract failed: {str(img_error)}")
                # Fallback to Bedrock Vision for images
                if BEDROCK_AVAILABLE:
                    try:
                        extracted_text = process_with_bedrock_vision(BUCKET_NAME, file_key, file_extension)
                    except Exception as bedrock_img_error:
                        print(f"Bedrock Vision for image also failed: {str(bedrock_img_error)}")
                        raise Exception(f"No se pudo procesar la imagen: {str(img_error)}")
                else:
                    raise Exception(f"No se pudo procesar la imagen: {str(img_error)}")
            
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
        
        # Check for async processing flag
        if extracted_text == "[ASYNC_PROCESSING_REQUIRED]":
            print("Async processing was required, returning early")
            return {
                'statusCode': 202,
                'headers': cors_headers,
                'body': json.dumps({
                    'runId': run_id,
                    'status': 'PROCESSING_ASYNC',
                    'message': 'Documento en procesamiento asíncrono'
                })
            }
        
        # Check if we got any text and validate length
        if not extracted_text or len(extracted_text.strip()) == 0:
            extracted_text = "No se pudo extraer texto del documento. Por favor, verifica que el documento contiene texto legible."
        elif len(extracted_text) > 15000:
            # Truncate if text is too long but keep processing
            print(f"Text is {len(extracted_text)} characters, truncating to 15000...")
            extracted_text = extracted_text[:15000] + "\n\n[Texto truncado por límite de caracteres]"
        
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
            'headers': cors_headers,
            'body': json.dumps({
                'runId': run_id,
                'status': 'EXTRACTED',
                'textLength': len(extracted_text),
                'textKey': text_key
            })
        }
        
    except Exception as e:
        print(f"Error in extract_lambda: {str(e)}")
        import traceback
        traceback_str = traceback.format_exc()
        print(f"Full traceback:\n{traceback_str}")
        
        # Log additional debugging information
        if 'file_key' in locals():
            print(f"Failed file: {file_key}")
        if 'file_extension' in locals():
            print(f"File extension: {file_extension}")
        
        error_message = str(e)
        
        # Provide more user-friendly error messages
        if 'UnsupportedDocumentException' in error_message:
            error_message = "El formato del documento no es compatible. Por favor, usa PDF, imágenes (PNG, JPG) o convierte el documento a uno de estos formatos."
        elif 'InvalidParameterException' in error_message:
            error_message = "El documento está dañado o tiene un formato inválido. Por favor, verifica el archivo."
        elif 'ProvisionedThroughputExceededException' in error_message:
            error_message = "El servicio está temporalmente sobrecargado. Por favor, intenta de nuevo en unos momentos."
        elif 'tardando demasiado' in error_message or 'taking too long' in error_message:
            error_message = "El procesamiento del documento está tardando más de lo esperado. Por favor, intente con un archivo más pequeño o inténtelo nuevamente más tarde."
        elif 'AccessDenied' in error_message:
            error_message = "Error de permisos al acceder al documento. Por favor, contacte al administrador."
        elif 'escaneadas' in error_message or 'scanned' in error_message.lower():
            error_message = "El documento parece contener imágenes escaneadas. El sistema intentó procesarlo pero no pudo extraer texto legible."
        elif 'bedrock' in error_message.lower():
            error_message = "El procesamiento avanzado del documento falló. Por favor, asegúrese de que el documento contiene texto legible."
        
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
        
        # Return error with CORS headers
        if 'cors_headers' not in locals():
            cors_headers = {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
                'Content-Type': 'application/json'
            }
        
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': error_message
            })
        }