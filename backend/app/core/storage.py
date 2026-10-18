import io
import uuid
from typing import BinaryIO
import aioboto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings


class S3StorageService:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = settings.S3_ENDPOINT_URL.strip() if settings.S3_ENDPOINT_URL else None
        self.access_key = settings.S3_ACCESS_KEY.strip() if settings.S3_ACCESS_KEY else None
        self.secret_key = settings.S3_SECRET_KEY.strip() if settings.S3_SECRET_KEY else None
        self.bucket_name = settings.S3_BUCKET_NAME.strip()
        self.region = settings.S3_REGION.strip() if settings.S3_REGION else "us-east-1"

    def _get_client_context(self):
        client_kwargs = {
            "service_name": "s3",
            "region_name": self.region,
        }
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
        if self.access_key and self.secret_key:
            client_kwargs["aws_access_key_id"] = self.access_key
            client_kwargs["aws_secret_access_key"] = self.secret_key

        return self.session.client(**client_kwargs)

    async def ensure_bucket_exists(self) -> None:
        """Create bucket if missing (primarily for local MinIO / staging setups)."""
        async with self._get_client_context() as s3:
            try:
                await s3.head_bucket(Bucket=self.bucket_name)
            except ClientError as e:
                error_code = str(e.response.get("Error", {}).get("Code", ""))
                # Only create if it definitively does not exist (404 / NotFound)
                if error_code in ("404", "NoSuchBucket", "NotFound"):
                    create_params = {"Bucket": self.bucket_name}
                    if self.region != "us-east-1":
                        create_params["CreateBucketConfiguration"] = {
                            "LocationConstraint": self.region
                        }
                    await s3.create_bucket(**create_params)
                else:
                    # Log or ignore if already owned or managed externally on AWS
                    pass

    async def upload_file(
        self,
        file_obj: UploadFile | BinaryIO | bytes,
        storage_path: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Uploads file bytes or streams to S3 and returns the storage path key."""
        if isinstance(file_obj, UploadFile):
            stream = file_obj.file
            content_type = file_obj.content_type or content_type
        elif isinstance(file_obj, bytes):
            stream = io.BytesIO(file_obj)
        else:
            stream = file_obj

        async with self._get_client_context() as s3:
            await s3.upload_fileobj(
                Fileobj=stream,
                Bucket=self.bucket_name,
                Key=storage_path,
                ExtraArgs={"ContentType": content_type},
            )

        return storage_path

    async def download_bytes(self, storage_path: str) -> bytes:
        """Reads file bytes from S3 for text extraction and chunk processing."""
        async with self._get_client_context() as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=storage_path)
            async with response["Body"] as stream:
                return await stream.read()

    async def delete_file(self, storage_path: str) -> None:
        """Removes document object from S3."""
        async with self._get_client_context() as s3:
            await s3.delete_object(Bucket=self.bucket_name, Key=storage_path)


storage_service = S3StorageService()