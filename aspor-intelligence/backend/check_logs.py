#!/usr/bin/env python3
"""
Script to check CloudWatch logs for Lambda errors
"""
import boto3
import json
from datetime import datetime, timedelta

def get_recent_logs(log_group_name, hours_back=1):
    """Get recent logs from CloudWatch"""
    client = boto3.client('logs', region_name='us-east-1')
    
    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=hours_back)
    
    try:
        # Get log streams
        response = client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not response['logStreams']:
            print(f"No log streams found for {log_group_name}")
            return
        
        # Get logs from the most recent stream
        for stream in response['logStreams']:
            stream_name = stream['logStreamName']
            print(f"\n=== Log Stream: {stream_name} ===")
            
            # Get events from this stream
            events_response = client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=stream_name,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                limit=100
            )
            
            for event in events_response['events']:
                message = event['message']
                if 'ERROR' in message or 'Error' in message or 'error' in message:
                    print(f"\n[ERROR] {message}")
                elif 'Processing' in message or 'Attempting' in message:
                    print(f"[INFO] {message}")
                    
    except Exception as e:
        print(f"Error getting logs: {str(e)}")

def check_lambda_configuration(function_name):
    """Check Lambda function configuration"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        response = lambda_client.get_function_configuration(
            FunctionName=function_name
        )
        
        print(f"\n=== Lambda Configuration: {function_name} ===")
        print(f"Runtime: {response.get('Runtime')}")
        print(f"Timeout: {response.get('Timeout')} seconds")
        print(f"Memory: {response.get('MemorySize')} MB")
        print(f"Last Modified: {response.get('LastModified')}")
        
        # Check environment variables
        env_vars = response.get('Environment', {}).get('Variables', {})
        print(f"\nEnvironment Variables:")
        for key, value in env_vars.items():
            if 'KEY' not in key.upper() and 'SECRET' not in key.upper():
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: ***HIDDEN***")
                
    except Exception as e:
        print(f"Error checking Lambda configuration: {str(e)}")

def check_bedrock_access():
    """Check if we have Bedrock access"""
    bedrock = boto3.client('bedrock', region_name='us-east-1')
    
    try:
        response = bedrock.list_foundation_models()
        print("\n=== Bedrock Models Available ===")
        claude_models = [m for m in response['modelSummaries'] 
                        if 'claude' in m['modelId'].lower()]
        
        for model in claude_models[:5]:  # Show first 5 Claude models
            print(f"- {model['modelId']}")
            
    except Exception as e:
        print(f"Error checking Bedrock access: {str(e)}")

if __name__ == "__main__":
    print("Checking ASPOR Intelligence System...")
    
    # Check Extract Lambda logs
    print("\n" + "="*50)
    print("EXTRACT LAMBDA LOGS")
    print("="*50)
    get_recent_logs('/aws/lambda/AsporIntelligenceStack-ExtractLambda*', hours_back=2)
    
    # Check Lambda configuration
    print("\n" + "="*50)
    print("LAMBDA CONFIGURATION")
    print("="*50)
    check_lambda_configuration('AsporIntelligenceStack-ExtractLambda*')
    
    # Check Bedrock access
    print("\n" + "="*50)
    print("BEDROCK ACCESS")
    print("="*50)
    check_bedrock_access()