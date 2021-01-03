import os
from storages.backends.s3boto3 import S3Boto3Storage


class S3Storage(S3Boto3Storage):
    bucket_name = os.environ.get("AWS_BUCKET_NAME")
    location = 'xyz/abc'

