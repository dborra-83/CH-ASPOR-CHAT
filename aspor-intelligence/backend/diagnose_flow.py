#!/usr/bin/env python3
"""
Diagnostic script to check the complete document processing flow
"""
import boto3
import json
from datetime import datetime, timedelta

# Initialize AWS clients
s3 = boto3.client('s3', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
logs = boto3.client('logs', region_name='us-east-1')

# Configuration
BUCKET_NAME = 'aspor-intelligence-documents'
TABLE_NAME = 'aspor-intelligence-executions'
table = dynamodb.Table(TABLE_NAME)

def check_recent_runs(hours_back=2):
    """Check recent runs in DynamoDB"""
    print("\n=== RECENT RUNS IN DYNAMODB ===")
    
    # Scan for recent items (not efficient for large tables, but OK for debugging)
    response = table.scan(Limit=10)
    
    items = response.get('Items', [])
    
    if not items:
        print("No items found in DynamoDB")
        return None
    
    print(f"Found {len(items)} recent items:")
    
    latest_run = None
    for item in items:
        run_id = item.get('runId', 'N/A')
        status = item.get('status', 'N/A')
        created = item.get('createdAt', 'N/A')
        text_key = item.get('textKey', 'N/A')
        text_extracted = item.get('textExtracted', 'N/A')
        extraction_method = item.get('extractionMethod', 'N/A')
        
        print(f"\n  RunID: {run_id}")
        print(f"  Status: {status}")
        print(f"  Created: {created}")
        print(f"  TextKey: {text_key}")
        print(f"  TextExtracted: {text_extracted}")
        print(f"  ExtractionMethod: {extraction_method}")
        
        # Check for step tracking
        step_fields = [k for k in item.keys() if k.startswith('step_')]
        if step_fields:
            print("  Steps completed:")
            for step in step_fields:
                if not step.endswith('_time') and not step.endswith('_details'):
                    print(f"    - {step}: {item.get(step, False)}")
        
        if not latest_run or (created and created > latest_run.get('createdAt', '')):
            latest_run = item
    
    return latest_run

def check_s3_files(run_id):
    """Check S3 for extracted text and analysis files"""
    print(f"\n=== S3 FILES FOR RUN {run_id} ===")
    
    # Check for extracted text
    text_key = f"extracted/{run_id}.txt"
    print(f"\nChecking for extracted text: {text_key}")
    
    try:
        response = s3.head_object(Bucket=BUCKET_NAME, Key=text_key)
        size = response['ContentLength']
        print(f"  ✓ Found: {size} bytes")
        
        # Get first 500 characters
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=text_key)
        text_content = obj['Body'].read().decode('utf-8')
        print(f"  First 500 chars: {text_content[:500]}...")
        
        if text_content.startswith("Error:"):
            print("  ⚠️ WARNING: Text content starts with 'Error:'")
        
        return text_key, text_content
        
    except s3.exceptions.NoSuchKey:
        print(f"  ✗ Not found in S3")
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
    
    # Check for analysis
    analysis_key = f"analysis/{run_id}.txt"
    print(f"\nChecking for analysis: {analysis_key}")
    
    try:
        response = s3.head_object(Bucket=BUCKET_NAME, Key=analysis_key)
        size = response['ContentLength']
        print(f"  ✓ Found: {size} bytes")
    except:
        print(f"  ✗ Not found")
    
    return None, None

def check_lambda_logs(function_name, run_id):
    """Check CloudWatch logs for specific run"""
    print(f"\n=== LAMBDA LOGS FOR {function_name} ===")
    
    log_group = f"/aws/lambda/{function_name}"
    
    try:
        # Get recent log streams
        streams = logs.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=3
        )
        
        if not streams['logStreams']:
            print(f"No log streams found")
            return
        
        # Search for the run_id in recent logs
        for stream in streams['logStreams']:
            stream_name = stream['logStreamName']
            
            # Get events from this stream
            events = logs.filter_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                filterPattern=run_id,
                limit=20
            )
            
            if events['events']:
                print(f"\nFound {len(events['events'])} log entries for run {run_id}:")
                for event in events['events']:
                    message = event['message'].strip()
                    if 'ERROR' in message or 'Error' in message:
                        print(f"  [ERROR] {message[:200]}")
                    elif 'extracted' in message.lower() or 'bedrock' in message.lower():
                        print(f"  [INFO] {message[:200]}")
                        
    except Exception as e:
        print(f"Error checking logs: {str(e)}")

def test_direct_flow(run_id):
    """Test if we can reconstruct the flow"""
    print(f"\n=== TESTING DIRECT FLOW FOR {run_id} ===")
    
    # Get the record from DynamoDB
    from boto3.dynamodb.conditions import Key
    
    response = table.query(
        IndexName='runId-index',
        KeyConditionExpression=Key('runId').eq(run_id)
    )
    
    if not response['Items']:
        print(f"No record found for runId: {run_id}")
        return
    
    item = response['Items'][0]
    print(f"Found record: {item.get('pk')} / {item.get('sk')}")
    
    # Check what text is available
    text_key = item.get('textKey')
    text_extracted = item.get('textExtracted', '')
    
    print(f"\nTextKey in DB: {text_key}")
    print(f"TextExtracted in DB: {text_extracted[:100] if text_extracted else 'None'}...")
    
    # Try to get text from S3
    if text_key:
        try:
            obj = s3.get_object(Bucket=BUCKET_NAME, Key=text_key)
            text_from_s3 = obj['Body'].read().decode('utf-8')
            print(f"\nText from S3 ({text_key}):")
            print(f"  Length: {len(text_from_s3)} characters")
            print(f"  First 200 chars: {text_from_s3[:200]}...")
            
            if len(text_from_s3) < 50:
                print("  ⚠️ WARNING: Text is very short!")
            if text_from_s3.startswith("Error:"):
                print("  ⚠️ WARNING: Text contains error message!")
                
        except Exception as e:
            print(f"  ✗ Could not load from S3: {str(e)}")

def main():
    print("ASPOR Intelligence - Document Flow Diagnostic")
    print("=" * 50)
    
    # Check recent runs
    latest_run = check_recent_runs()
    
    if not latest_run:
        print("\nNo runs found to diagnose")
        return
    
    run_id = latest_run.get('runId')
    if not run_id:
        print("\nNo valid runId found")
        return
    
    print(f"\n\nDiagnosing latest run: {run_id}")
    print("=" * 50)
    
    # Check S3 files
    text_key, text_content = check_s3_files(run_id)
    
    # Check Lambda logs
    check_lambda_logs('AsporApiStack-ExtractLambda8D90D717-dAwzKoXY8epJ', run_id)
    check_lambda_logs('AsporApiStack-AnalyzeLambda57C19DB1-IjhGSozJvIlN', run_id)
    
    # Test direct flow
    test_direct_flow(run_id)
    
    # Summary
    print("\n" + "=" * 50)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    status = latest_run.get('status', 'UNKNOWN')
    print(f"Run Status: {status}")
    
    if text_content:
        if text_content.startswith("Error:"):
            print("❌ Problem: Extraction failed, error message stored instead of text")
            print("   Solution: Check why Bedrock/Textract failed in extraction")
        elif len(text_content) < 50:
            print("❌ Problem: Very little text extracted")
            print("   Solution: Document might be image-heavy, ensure Bedrock Vision is working")
        else:
            print("✅ Text extraction successful")
            
            if status != 'COMPLETED':
                print("⚠️  But analysis may have failed")
                print("   Check if text is being passed correctly to analyze Lambda")
    else:
        print("❌ Problem: No text found in S3")
        print("   Solution: Check extraction Lambda logs for errors")

if __name__ == "__main__":
    main()