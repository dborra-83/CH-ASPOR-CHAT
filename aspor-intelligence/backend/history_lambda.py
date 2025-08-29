import json
import boto3
import os
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['TABLE_NAME']
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    try:
        user_id = event['pathParameters']['userId']
        
        # Query DynamoDB for user's history
        response = table.query(
            KeyConditionExpression=Key('pk').eq(f'USER#{user_id}'),
            ScanIndexForward=False,  # Most recent first
            Limit=50
        )
        
        print(f"Found {len(response['Items'])} items for user {user_id}")
        
        history = []
        for item in response['Items']:
            # Log all available keys in the item for debugging
            print(f"Item keys for run {item.get('runId')}: {list(item.keys())}")
            
            # Log if item has analysis results
            has_async_result = bool(item.get('analysisResult'))
            has_bedrock_result = bool(item.get('bedrockResult'))
            async_length = len(str(item.get('analysisResult', ''))) if item.get('analysisResult') else 0
            bedrock_length = len(str(item.get('bedrockResult', ''))) if item.get('bedrockResult') else 0
            print(f"Processing run {item.get('runId')}: status={item.get('status')}, has_analysisResult={has_async_result} ({async_length} chars), has_bedrockResult={has_bedrock_result} ({bedrock_length} chars), model={item.get('model')}")
            
            # Extract file name properly
            file_name = 'Unknown'
            if item.get('fileKey'):
                file_name = item.get('fileKey', '').split('/')[-1]
            elif item.get('fileName'):
                file_name = item.get('fileName')
            
            # Get the analysis result from any of the possible fields
            analysis_result = (
                item.get('analysisResult') or  # New async processing field
                item.get('bedrockResult') or   # Legacy field
                item.get('analysis')           # Alternative field
            )
            
            # Get the model, defaulting to 'A' if not set (as per the system default)
            model = item.get('model') or item.get('analysisModel') or 'A'
            
            history_item = {
                'runId': item.get('runId'),
                'status': item.get('status'),
                'model': model,
                'fileName': file_name,
                'textExtracted': item.get('textExtracted', 'N/A'),
                'processedAt': item.get('createdAt'),
                'completedAt': item.get('completedAt'),
                'errorMessage': item.get('errorMessage'),
                'bedrockResult': item.get('bedrockResult'),  # Legacy field
                'analysis': analysis_result,  # Primary field for frontend
                'analysisResult': item.get('analysisResult'),  # New async field
                'analysisKey': item.get('analysisKey'),  # Include S3 key if needed
                'analysisMethod': item.get('analysisMethod'),  # How it was analyzed
                # Add all fields for debugging
                'allFields': list(item.keys())
            }
            history.append(history_item)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'userId': user_id,
                'history': history,
                'count': len(history)
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
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