from aws_cdk import (
    Stack,
    RemovalPolicy,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_s3_deployment as s3_deploy,
    CfnOutput
)
from constructs import Construct

class FrontendStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, api_url: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # S3 bucket for frontend hosting
        frontend_bucket = s3.Bucket(
            self,
            "AsporFrontendBucket",
            bucket_name="aspor-intelligence-frontend",
            website_index_document="index.html",
            website_error_document="error.html",
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True
        )
        
        # CloudFront Origin Access Identity
        oai = cloudfront.OriginAccessIdentity(
            self,
            "AsporOAI",
            comment="OAI for Aspor Intelligence"
        )
        
        # Grant CloudFront access to bucket
        frontend_bucket.grant_read(oai)
        
        # CloudFront distribution
        distribution = cloudfront.Distribution(
            self,
            "AsporDistribution",
            default_root_object="index.html",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin(frontend_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD
            ),
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_page_path="/index.html",
                    response_http_status=200
                ),
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_page_path="/index.html",
                    response_http_status=200
                )
            ],
            comment="Aspor Intelligence Distribution",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100
        )
        
        # Deploy frontend build to S3
        s3_deploy.BucketDeployment(
            self,
            "AsporFrontendDeployment",
            sources=[s3_deploy.Source.asset("../frontend/out")],
            destination_bucket=frontend_bucket,
            distribution=distribution,
            distribution_paths=["/*"]
        )
        
        # Write config file with API URL
        s3_deploy.BucketDeployment(
            self,
            "AsporConfigDeployment",
            sources=[
                s3_deploy.Source.json_data(
                    "config.json",
                    {
                        "apiUrl": api_url
                    }
                )
            ],
            destination_bucket=frontend_bucket
        )
        
        # Outputs
        CfnOutput(
            self,
            "DistributionUrl",
            value=f"https://{distribution.distribution_domain_name}",
            description="CloudFront distribution URL"
        )
        
        CfnOutput(
            self,
            "FrontendBucket",
            value=frontend_bucket.bucket_name,
            description="Frontend S3 bucket name"
        )