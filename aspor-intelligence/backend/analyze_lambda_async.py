import json
import boto3
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key

# Initialize clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

BUCKET_NAME = os.environ['BUCKET_NAME']
TABLE_NAME = os.environ['TABLE_NAME']
ASYNC_PROCESSOR_FUNCTION = os.environ.get('ASYNC_PROCESSOR_FUNCTION', 'AsporApiStack-ProcessAsyncLambda')
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    """
    Main analyze endpoint - initiates async processing for documents
    Returns immediately with processing status
    """
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
        
        print(f"Processing request: runId={run_id}, model={model_type}")
        
        # Find the record in DynamoDB
        response = table.query(
            IndexName='runId-index',
            KeyConditionExpression=Key('runId').eq(run_id)
        )
        
        if response['Items']:
            item = response['Items'][0]
            pk = item['pk']
            sk = item['sk']
            file_key = item.get('fileKey')
            current_status = item.get('status')
            
            # Check if already completed
            if current_status == 'COMPLETED':
                analysis_result = item.get('analysisResult', '')
                if analysis_result:
                    print(f"Returning cached result for {run_id}")
                    return {
                        'statusCode': 200,
                        'headers': cors_headers,
                        'body': json.dumps({
                            'runId': run_id,
                            'status': 'COMPLETED',
                            'analysis': analysis_result,
                            'model': model_type,
                            'method': 'cached'
                        })
                    }
            
            # Check if already processing
            if current_status in ['PROCESSING_ASYNC', 'ANALYZING']:
                print(f"Already processing: {run_id}")
                return {
                    'statusCode': 202,
                    'headers': cors_headers,
                    'body': json.dumps({
                        'runId': run_id,
                        'status': 'PROCESSING',
                        'message': 'Document is being processed. Please check back in a few seconds.'
                    })
                }
            
            print(f"Found record with file: {file_key}")
        else:
            print(f"No record found for runId: {run_id}")
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': f'No document found for runId: {run_id}'
                })
            }
        
        if not file_key:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': 'No document file found in the record'
                })
            }
        
        # Update status to indicate async processing is starting
        table.update_item(
            Key={'pk': pk, 'sk': sk},
            UpdateExpression='SET #status = :status, asyncInitiated = :time',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'PROCESSING_ASYNC',
                ':time': datetime.utcnow().isoformat()
            }
        )
        
        # Invoke async processor Lambda
        print(f"Invoking async processor for {run_id}")
        
        async_payload = {
            'runId': run_id,
            'userId': user_id,
            'model': model_type
        }
        
        try:
            lambda_client.invoke(
                FunctionName=ASYNC_PROCESSOR_FUNCTION,
                InvocationType='Event',  # Async invocation
                Payload=json.dumps(async_payload)
            )
            
            print(f"Async processing initiated for {run_id}")
            
            return {
                'statusCode': 202,  # Accepted
                'headers': cors_headers,
                'body': json.dumps({
                    'runId': run_id,
                    'status': 'PROCESSING',
                    'message': 'Document processing has been initiated. Results will be available in 10-30 seconds.',
                    'checkStatusUrl': f'/api/status/{run_id}'
                })
            }
            
        except Exception as invoke_error:
            print(f"Failed to invoke async processor: {str(invoke_error)}")
            
            # Update status to failed
            table.update_item(
                Key={'pk': pk, 'sk': sk},
                UpdateExpression='SET #status = :status, errorMessage = :error',
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'FAILED',
                    ':error': f'Failed to start async processing: {str(invoke_error)}'
                }
            )
            
            raise
            
    except Exception as e:
        print(f"Error: {str(e)}")
        
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': str(e),
                'runId': body.get('runId') if 'body' in locals() else None
            })
        }