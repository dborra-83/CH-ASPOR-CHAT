#!/usr/bin/env python3
import boto3
from datetime import datetime, timedelta

# CloudWatch client
logs = boto3.client('logs', region_name='us-east-1')

# Get logs from the last hour
end_time = datetime.now()
start_time = end_time - timedelta(hours=1)

log_group = '/aws/lambda/AsporApiStack-ExtractLambda8D90D717-dAwzKoXY8epJ'

try:
    response = logs.filter_log_events(
        logGroupName=log_group,
        startTime=int(start_time.timestamp() * 1000),
        endTime=int(end_time.timestamp() * 1000),
        limit=100
    )
    
    print(f"=== Recent logs from {log_group} ===\n")
    
    for event in response['events']:
        message = event['message'].strip()
        if 'ERROR' in message or 'Error' in message or 'error' in message or 'Failed' in message:
            print(f"[ERROR] {message}\n")
        elif 'Processing' in message or 'Event received' in message:
            print(f"[INFO] {message}\n")
            
except Exception as e:
    print(f"Error: {str(e)}")