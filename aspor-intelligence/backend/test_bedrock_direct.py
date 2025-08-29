#!/usr/bin/env python3
"""
Test Bedrock Vision directly with AWS CLI to bypass Lambda limitations
"""
import boto3
import json
import base64
import sys
from botocore.config import Config

# Initialize clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Bedrock with extended timeout for testing
bedrock_config = Config(
    region_name='us-east-1',
    read_timeout=60,  # 60 seconds for testing
    connect_timeout=10,
    retries={'max_attempts': 1}
)
bedrock = boto3.client('bedrock-runtime', config=bedrock_config)

BUCKET_NAME = 'aspor-intelligence-documents'
TABLE_NAME = 'aspor-intelligence-executions'
BEDROCK_MODEL_ID = 'anthropic.claude-3-5-sonnet-20241022-v2:0'

def test_direct_bedrock_vision(run_id):
    """Test Bedrock Vision directly with a document from S3"""
    print(f"\n=== TESTING BEDROCK VISION DIRECTLY FOR RUN {run_id} ===\n")
    
    # Get the record from DynamoDB
    table = dynamodb.Table(TABLE_NAME)
    from boto3.dynamodb.conditions import Key
    
    response = table.query(
        IndexName='runId-index',
        KeyConditionExpression=Key('runId').eq(run_id)
    )
    
    if not response['Items']:
        print(f"No record found for runId: {run_id}")
        return
    
    item = response['Items'][0]
    file_key = item.get('fileKey')
    
    if not file_key:
        print("No fileKey found in DynamoDB record")
        return
    
    print(f"Found file key: {file_key}")
    
    try:
        # Get the document from S3
        print(f"\n1. Getting document from S3...")
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=file_key)
        document_bytes = obj['Body'].read()
        doc_size_mb = len(document_bytes) / (1024 * 1024)
        print(f"   Document size: {doc_size_mb:.2f} MB")
        
        # Encode to base64
        print(f"\n2. Encoding document to base64...")
        document_base64 = base64.b64encode(document_bytes).decode('utf-8')
        print(f"   Base64 length: {len(document_base64)} characters")
        
        # Determine media type
        file_extension = file_key.lower().split('.')[-1]
        if file_extension == 'pdf':
            media_type = 'application/pdf'
        elif file_extension in ['jpg', 'jpeg']:
            media_type = 'image/jpeg'
        elif file_extension == 'png':
            media_type = 'image/png'
        else:
            media_type = 'application/octet-stream'
        
        print(f"   Media type: {media_type}")
        
        # Prepare the request
        print(f"\n3. Preparing Bedrock request...")
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,  # Start with smaller response for testing
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Please extract and summarize the text content from this document. If you can see the document, start your response with 'Document received successfully'. If you cannot see the document, start with 'Document not visible'."
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
            "temperature": 0.1
        }
        
        # Call Bedrock
        print(f"\n4. Calling Bedrock (this may take 30-60 seconds)...")
        print(f"   Model: {BEDROCK_MODEL_ID}")
        
        response = bedrock.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body),
            contentType='application/json',
            accept='application/json'
        )
        
        # Parse response
        response_body = json.loads(response['body'].read())
        result = response_body['content'][0]['text']
        
        print(f"\n5. SUCCESS! Bedrock responded with {len(result)} characters")
        print(f"\nFirst 500 characters of response:")
        print("-" * 50)
        print(result[:500])
        print("-" * 50)
        
        # Save to file for review
        output_file = f"bedrock_test_result_{run_id}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f"\nFull response saved to: {output_file}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        print(f"\nFull traceback:")
        print(traceback.format_exc())
        return False

def get_latest_run():
    """Get the most recent run from DynamoDB"""
    table = dynamodb.Table(TABLE_NAME)
    response = table.scan(Limit=1)
    
    if response['Items']:
        return response['Items'][0].get('runId')
    return None

def main():
    if len(sys.argv) > 1:
        run_id = sys.argv[1]
    else:
        print("No run_id provided, using latest run...")
        run_id = get_latest_run()
        if not run_id:
            print("No runs found in DynamoDB")
            return
    
    print(f"Testing with run_id: {run_id}")
    success = test_direct_bedrock_vision(run_id)
    
    if success:
        print("\n✅ Test completed successfully!")
        print("\nNext steps:")
        print("1. If this worked but Lambda doesn't, the issue is timeout-related")
        print("2. Consider implementing async processing with Step Functions")
        print("3. Or use a larger Lambda timeout with reserved concurrency")
    else:
        print("\n❌ Test failed")
        print("\nPossible issues:")
        print("1. Document format not supported by Bedrock")
        print("2. Document too large (>5MB)")
        print("3. Bedrock model permissions")
        print("4. Network/connectivity issues")

if __name__ == "__main__":
    main()