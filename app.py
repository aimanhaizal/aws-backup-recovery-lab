#!/usr/bin/env python3
import os

import aws_cdk as cdk

from backup_recovery_stack import BackupRecoveryStack

app = cdk.App()

BackupRecoveryStack(
    app,
    "AwsBackupRecoveryLabStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION", "ap-southeast-1"),
    ),
)

app.synth()
