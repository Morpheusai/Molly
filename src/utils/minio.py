import os
from minio import Minio
from dotenv import load_dotenv
load_dotenv()
# MinIO configuration
minio_server = os.getenv("MINIO_SERVER")
minio_access_key = os.getenv("MINIO_ACCESS_KEY")
minio_secret_key = os.getenv("MINIO_SECRET_KEY")
minio_secure = os.getenv("MINIO_SECURE") == "True"
bucket_molly = os.getenv("MINIO_BUCKET_MOLLY","molly")
bucket_netmhcpan_results = os.getenv("MINIO_BUCKET_NETMHCPAN_RESULTS")
bucket_weblogo = os.getenv("MINIO_BUCKET_WEBLOGO")
# Initialize the MinIO client
minio_client = Minio(
    minio_server,
    access_key=minio_access_key,
    secret_key=minio_secret_key,
    secure=minio_secure,
)
