from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_iam as iam,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    CfnOutput
)
from constructs import Construct
import os

class ApiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 bucket: s3.Bucket, table: dynamodb.Table, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Extract Lambda Function
        extract_lambda = lambda_.Function(
            self,
            "ExtractLambda",
            code=lambda_.Code.from_asset("../backend"),
            handler="extract_lambda.handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=Duration.minutes(5),
            memory_size=1024,
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "TABLE_NAME": table.table_name
            }
        )
        
        # Analyze Lambda Function
        analyze_lambda = lambda_.Function(
            self,
            "AnalyzeLambda",
            code=lambda_.Code.from_asset("../backend"),
            handler="analyze_lambda.handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(29),  # API Gateway has a 30 second timeout limit
            memory_size=3008,  # Increased memory for faster processing
            environment={
                "BUCKET_NAME": bucket.bucket_name,
                "TABLE_NAME": table.table_name,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-sonnet-20240229-v1:0"
            }
        )
        
        # Presigned URL Lambda Function
        presigned_lambda = lambda_.Function(
            self,
            "PresignedUrlLambda",
            code=lambda_.Code.from_asset("../backend"),
            handler="presigned_lambda.handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(30),
            environment={
                "BUCKET_NAME": bucket.bucket_name
            }
        )
        
        # History Lambda Function
        history_lambda = lambda_.Function(
            self,
            "HistoryLambda",
            code=lambda_.Code.from_asset("../backend"),
            handler="history_lambda.handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": table.table_name
            }
        )
        
        # Status Lambda Function
        status_lambda = lambda_.Function(
            self,
            "StatusLambda",
            code=lambda_.Code.from_asset("../backend"),
            handler="status_lambda.handler",
            runtime=lambda_.Runtime.PYTHON_3_11,
            timeout=Duration.seconds(30),
            environment={
                "TABLE_NAME": table.table_name
            }
        )
        
        # Grant permissions
        bucket.grant_read_write(extract_lambda)
        bucket.grant_read_write(analyze_lambda)
        bucket.grant_read_write(presigned_lambda)
        
        table.grant_read_write_data(extract_lambda)
        table.grant_read_write_data(analyze_lambda)
        table.grant_read_data(history_lambda)
        table.grant_read_data(status_lambda)
        
        # Grant Textract permissions to extract lambda
        extract_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "textract:DetectDocumentText",
                    "textract:AnalyzeDocument"
                ],
                resources=["*"]
            )
        )
        
        # Grant Bedrock permissions to analyze lambda
        analyze_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )
        
        # API Gateway
        api = apigateway.RestApi(
            self,
            "AsporApi",
            rest_api_name="Aspor Intelligence API",
            description="API for document processing and analysis",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key", "X-Amz-Security-Token"],
                allow_credentials=False,
                max_age=Duration.hours(1)
            ),
            deploy_options=apigateway.StageOptions(
                throttling_rate_limit=1000,
                throttling_burst_limit=2000
            )
        )
        
        # API Resources
        upload_resource = api.root.add_resource("upload")
        extract_resource = api.root.add_resource("extract")
        analyze_resource = api.root.add_resource("analyze")
        runs_resource = api.root.add_resource("runs")
        run_resource = runs_resource.add_resource("{id}")
        history_resource = api.root.add_resource("history")
        user_history_resource = history_resource.add_resource("{userId}")
        
        # API Methods
        upload_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(presigned_lambda)
        )
        
        extract_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(extract_lambda)
        )
        
        # Analyze method with timeout handling
        analyze_integration = apigateway.LambdaIntegration(
            analyze_lambda,
            timeout=Duration.seconds(29),
            integration_responses=[
                apigateway.IntegrationResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'",
                        "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                        "method.response.header.Access-Control-Allow-Methods": "'GET,POST,OPTIONS'"
                    }
                ),
                apigateway.IntegrationResponse(
                    status_code="504",
                    selection_pattern=".*Task timed out.*",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": "'*'"
                    },
                    response_templates={
                        "application/json": '{"error": "Request timeout. Please try again or use a smaller document."}'
                    }
                )
            ]
        )
        
        analyze_resource.add_method(
            "POST",
            analyze_integration,
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True,
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True
                    }
                ),
                apigateway.MethodResponse(
                    status_code="504",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ]
        )
        
        run_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(status_lambda)
        )
        
        user_history_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(history_lambda)
        )
        
        # Store API URL
        self.api_url = api.url
        
        # Outputs
        CfnOutput(
            self,
            "ApiUrl",
            value=self.api_url,
            description="API Gateway endpoint URL"
        )