"""Cloud Object Storage Adapter (AWS S3 / Google Cloud Storage / Local Fallback).

Provides unified cloud file upload, presigned URL generation, and deletion for employee documents,
avatars, ID cards, and generated payslip PDFs.
"""
import os
import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger("attendance")

S3_BUCKET = os.environ.get("AWS_S3_BUCKET", "maghr-cloud-documents")
S3_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")


def _get_s3_client():
    """Initializes and returns boto3 S3 client if credentials exist."""
    if AWS_ACCESS_KEY and AWS_SECRET_KEY:
        return boto3.client(
            "s3",
            region_name=S3_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
    return None


def upload_file_to_cloud(file_bytes, destination_path, content_type="application/octet-stream"):
    """Uploads file bytes to AWS S3 bucket or falls back to local storage."""
    s3 = _get_s3_client()
    if s3:
        try:
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=destination_path,
                Body=file_bytes,
                ContentType=content_type
            )
            cloud_url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{destination_path}"
            logger.info(f"[CloudStorage] Uploaded to S3: {cloud_url}")
            return cloud_url
        except (BotoCoreError, ClientError) as ex:
            logger.error(f"[CloudStorage] S3 upload error: {ex}")

    # Fallback to local storage
    local_dir = os.path.join("static", "uploads", os.path.dirname(destination_path))
    os.makedirs(local_dir, exist_ok=True)
    local_full_path = os.path.join("static", "uploads", destination_path)
    with open(local_full_path, "wb") as f:
        f.write(file_bytes)
    return f"/static/uploads/{destination_path}"


def generate_presigned_url(cloud_key, expires_in=3600):
    """Generates a secure presigned download URL for private documents."""
    s3 = _get_s3_client()
    if s3 and not cloud_key.startswith("/static/"):
        try:
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": S3_BUCKET, "Key": cloud_key},
                ExpiresIn=expires_in
            )
            return url
        except Exception as ex:
            logger.error(f"[CloudStorage] Error generating presigned URL: {ex}")
    return cloud_key
