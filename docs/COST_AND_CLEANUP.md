# AWS Backup & Recovery Lab — Cost & Cleanup Guide

This guide documents the AWS resources deployed by the project, the main cost considerations, and how to safely clean up the environment when the demonstration is no longer required.

**AWS Region:** `ap-southeast-1` (Asia Pacific — Singapore)

**CloudFormation Stack:** `AwsBackupRecoveryLabStack`

**S3 Bucket:** `awsbackuprecoverylabstack-backupbucket26b8e51c-p3qt3di7zjem`

## 1. AWS Resources

The project provisions a dedicated Amazon S3 bucket using AWS CDK and AWS CloudFormation.

| Resource / Configuration | Purpose |
|---|---|
| Amazon S3 bucket | Stores backup files and checksum manifests |
| S3 Versioning | Retains previous object versions |
| SSE-S3 encryption | Encrypts objects at rest |
| S3 Block Public Access | Prevents public access through the bucket's public-access controls |
| S3 bucket policy | Denies requests that use insecure transport |
| CloudFormation stack | Manages the infrastructure defined by AWS CDK |
| CDK bootstrap resources | Existing account-level resources used by CDK deployments; shared with other projects |

The application also creates local backup, download, and recovery directories. These are not AWS resources and are excluded from Git.

## 2. Cost Considerations

This project is intentionally small and does not provision EC2 instances, NAT gateways, load balancers, RDS databases, or other application hosting infrastructure.

However, **AWS usage is not guaranteed to be free**. Charges depend on current pricing, account eligibility, storage consumed, and API usage.

Potential cost sources include:

- **S3 storage:** Backup objects and manifests occupy storage.
- **S3 requests:** Upload, download, listing, and other API operations may incur request charges.
- **S3 Versioning:** Previous object versions may continue to consume storage after newer versions are uploaded or current objects are deleted.
- **CloudFormation:** The stack itself does not normally have a separate stack-management charge, but the resources it manages may incur charges.
- **CDK bootstrap resources:** The existing bootstrap bucket and other shared resources belong to the wider AWS environment. Do not remove them as part of this project's cleanup.

The project does not configure an automated retention policy or scheduled backup job. Uploaded backups therefore remain until they are explicitly removed or another retention mechanism is introduced.

### Cost-conscious operating practices

- Keep demo files small.
- Avoid uploading repeated test backups unnecessarily.
- Review S3 object versions before deleting data.
- Remove the project's AWS resources when the live demonstration is no longer needed.
- Review AWS billing and Cost Explorer for actual usage and charges.
- Do not assume that deleting the CloudFormation stack removes the S3 bucket.

## 3. Inspect the Deployed Resources

Run these commands from a terminal with the appropriate AWS CLI profile configured.

Set the project variables:

```bash
export AWS_PROFILE=portfolio-dev
export AWS_REGION=ap-southeast-1

export STACK_NAME=AwsBackupRecoveryLabStack
export BUCKET_NAME=awsbackuprecoverylabstack-backupbucket26b8e51c-p3qt3di7zjem
```

Verify the active AWS identity:

```bash
aws sts get-caller-identity \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
```

List the CloudFormation stack resources:

```bash
aws cloudformation describe-stack-resources \
  --stack-name "$STACK_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
```

List current objects:

```bash
aws s3 ls \
  "s3://$BUCKET_NAME/" \
  --recursive \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
```

These commands inspect the environment without changing or deleting resources.

## 4. Option A — Keep the Demonstration Deployed

Choose this option if you intend to demonstrate the live S3 workflow again.

1. Keep the CloudFormation stack and S3 bucket.
2. Retain a small sample backup if useful.
3. Periodically review the bucket's current objects and previous versions.
4. Review AWS billing for any applicable charges.

You can continue using the CLI to create, upload, download, and restore backups.

Remember that S3 Versioning may retain previous object versions even after a current object is deleted.

## 5. Option B — Remove the Project's AWS Resources

Choose this option if you have finished demonstrating the live project and want to reduce ongoing AWS usage.

**Warning:** The cleanup steps below permanently delete data. Download anything you want to keep before proceeding. Do not run these commands against a bucket belonging to another project.

### Step 1 — Review the bucket contents and versions

List current objects:

```bash
aws s3 ls \
  "s3://$BUCKET_NAME/" \
  --recursive \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
```

Because versioning is enabled, inspect object versions and delete markers as well:

```bash
aws s3api list-object-versions \
  --bucket "$BUCKET_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
```

### Step 2 — Delete the bucket's objects and all retained versions

Only proceed if you have confirmed that this is the dedicated project bucket and that all data can be deleted.

The following script deletes current objects, noncurrent versions, and delete markers in batches. Review the bucket name before running it.

```bash
python - <<'PY'
import boto3
import os

bucket = "awsbackuprecoverylabstack-backupbucket26b8e51c-p3qt3di7zjem"
profile = os.getenv("AWS_PROFILE", "portfolio-dev")
region = os.getenv("AWS_REGION", "ap-southeast-1")

session = boto3.Session(profile_name=profile, region_name=region)
s3 = session.client("s3")
paginator = s3.get_paginator("list_object_versions")

for page in paginator.paginate(Bucket=bucket):
    entries = [
        {"Key": item["Key"], "VersionId": item["VersionId"]}
        for item in (
            page.get("Versions", []) + page.get("DeleteMarkers", [])
        )
    ]

    for start in range(0, len(entries), 1000):
        batch = entries[start:start + 1000]
        if batch:
            response = s3.delete_objects(
                Bucket=bucket,
                Delete={"Objects": batch, "Quiet": True},
            )
            errors = response.get("Errors", [])
            if errors:
                raise RuntimeError(f"S3 deletion errors: {errors}")

print("Finished removing listed object versions and delete markers.")
PY
```

This script deletes data in the bucket. It does not delete the bucket itself.

### Step 3 — Delete the empty S3 bucket

After confirming that the bucket is empty:

```bash
aws s3api delete-bucket \
  --bucket "$BUCKET_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
```

If deletion fails, inspect the error and verify that all versions and delete markers have been removed.

### Step 4 — Delete the CloudFormation stack

After the bucket has been deleted, remove the project stack:

```bash
aws cloudformation delete-stack \
  --stack-name "$STACK_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
```

Wait for deletion to complete:

```bash
aws cloudformation wait stack-delete-complete \
  --stack-name "$STACK_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
```

The stack's S3 bucket has a `RETAIN` deletion policy. This is why the bucket is removed explicitly before deleting the stack.

**Do not delete the CDK bootstrap stack or its asset bucket.** They may be shared with other projects in the same AWS account.

## 6. Verify Cleanup

After the cleanup completes, verify that the project stack no longer exists:

```bash
aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
```

A stack-not-found response is expected after successful deletion.

Check that the bucket is gone:

```bash
aws s3api head-bucket \
  --bucket "$BUCKET_NAME" \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"
```

A not-found response is expected once the bucket has been deleted. If the command returns an access-denied response, do not treat that alone as proof of deletion.

Finally, review AWS billing for any remaining charges or other resources. Deleting this project's stack does not remove unrelated resources or reverse charges already incurred.

## 7. Local Project Cleanup

The local repository can remain on GitHub even after the AWS resources are removed.

Local demo and recovery directories can be removed separately if they are no longer needed:

```bash
rm -rf demo-data local-backups restored-data \
       s3-recovery-test s3-restored-data
```

These commands delete only the named local directories in the current working directory. Verify your current directory before running them.

## Summary

The project uses a small S3 footprint and has no application compute infrastructure. Its main ongoing cost consideration is S3 storage, especially when versioning retains older copies of objects.

The CloudFormation stack deliberately retains its bucket on stack deletion. To fully remove this project's AWS resources, inspect and delete the bucket's objects and versions, delete the bucket, and then delete the project stack. Preserve the shared CDK bootstrap resources and any unrelated AWS resources.
