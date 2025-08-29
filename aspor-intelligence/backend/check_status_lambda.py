import json
import boto3
import os
from boto3.dynamodb.conditions import Key

# Initialize clients
dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

TABLE_NAME = os.environ['TABLE_NAME']
BUCKET_NAME = os.environ['BUCKET_NAME']
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    """
    Check the status of a document processing run
    """
    print(f"Status check received: {json.dumps(event)}")
    
    # CORS headers
    cors_headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
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
        # Get runId from path parameters or query string
        run_id = None
        
        if event.get('pathParameters'):
            run_id = event['pathParameters'].get('runId')
        
        if not run_id and event.get('queryStringParameters'):
            run_id = event['queryStringParameters'].get('runId')
        
        if not run_id:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'runId is required'})
            }
        
        print(f"Checking status for runId: {run_id}")
        
        # Query DynamoDB for the run
        response = table.query(
            IndexName='runId-index',
            KeyConditionExpression=Key('runId').eq(run_id)
        )
        
        if not response['Items']:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({
                    'error': f'No record found for runId: {run_id}'
                })
            }
        
        item = response['Items'][0]
        status = item.get('status', 'UNKNOWN')
        
        # Build response based on status
        response_body = {
            'runId': run_id,
            'status': status,
            'createdAt': item.get('createdAt'),
            'model': item.get('model')
        }
        
        if status == 'COMPLETED':
            # Get the analysis result
            analysis_result = item.get('analysisResult')
            
            # If not in DynamoDB, try to get from S3
            if not analysis_result:
                analysis_key = f"analysis/{run_id}.txt"
                try:
                    obj = s3.get_object(Bucket=BUCKET_NAME, Key=analysis_key)
                    analysis_result = obj['Body'].read().decode('utf-8')
                except:
                    analysis_result = None
            
            if analysis_result:
                response_body['analysis'] = analysis_result
                response_body['completedAt'] = item.get('completedAt')
                response_body['method'] = item.get('analysisMethod', 'unknown')
            else:
                response_body['status'] = 'COMPLETED_NO_RESULT'
                response_body['message'] = 'Processing completed but no result found'
        
        elif status == 'FAILED':
            response_body['error'] = item.get('errorMessage', 'Unknown error')
            response_body['failedAt'] = item.get('failedAt')
        
        elif status in ['PROCESSING_ASYNC', 'ANALYZING', 'EXTRACTING']:
            response_body['message'] = 'Document is still being processed'
            response_body['startedAt'] = item.get('asyncInitiated') or item.get('createdAt')
            
            # Add progress information if available
            if item.get('step_extraction_started'):
                response_body['extractionStarted'] = True
            if item.get('step_bedrock_called'):
                response_body['analysisStarted'] = True
        
        else:
            response_body['message'] = f'Document in {status} state'
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        print(f"Error checking status: {str(e)}")
        
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({
                'error': str(e)
            })
        }