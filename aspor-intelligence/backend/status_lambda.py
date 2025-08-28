import json
import boto3
import os
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['TABLE_NAME']
table = dynamodb.Table(TABLE_NAME)

def handler(event, context):
    try:
        run_id = event['pathParameters']['id']
        
        # Query using GSI
        response = table.query(
            IndexName='runId-index',
            KeyConditionExpression=Key('runId').eq(run_id)
        )
        
        if response['Items']:
            item = response['Items'][0]
            
            # Log the item for debugging
            print(f"Retrieved item for run_id {run_id}: {json.dumps(item, default=str)}")
            
            result = {
                'runId': run_id,
                'status': item.get('status'),
                'model': item.get('model'),
                'createdAt': item.get('createdAt'),
                'completedAt': item.get('completedAt'),
                'textExtracted': item.get('textExtracted'),
                'errorMessage': item.get('errorMessage')
            }
            
            # Include analysis result if completed
            if item.get('status') == 'COMPLETED':
                # Include both fields for compatibility
                result['bedrockResult'] = item.get('bedrockResult')
                result['analysis'] = item.get('bedrockResult')
                print(f"Added bedrockResult to response: {bool(item.get('bedrockResult'))}")
            
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps(result)
            }
        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Content-Type': 'application/json'
                },
                'body': json.dumps({
                    'error': 'Run not found'
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