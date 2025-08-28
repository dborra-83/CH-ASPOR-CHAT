#!/usr/bin/env python3
import os
import aws_cdk as cdk
from stacks.storage_stack import StorageStack
from stacks.api_stack import ApiStack
from stacks.frontend_stack import FrontendStack

app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT'),
    region='us-east-1'
)

# Deploy stacks
storage_stack = StorageStack(app, "AsporStorageStack", env=env)
api_stack = ApiStack(app, "AsporApiStack", 
                     bucket=storage_stack.bucket,
                     table=storage_stack.table,
                     env=env)
frontend_stack = FrontendStack(app, "AsporFrontendStack",
                               api_url=api_stack.api_url,
                               env=env)

# Add dependencies
api_stack.add_dependency(storage_stack)
frontend_stack.add_dependency(api_stack)

app.synth()