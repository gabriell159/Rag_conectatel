import os
import boto3
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path)

BUCKET_NAME = "conectatel-bucket"
PASTA_LOCAL = BASE_DIR / "data" / "raw"
PREFIXO_S3 = "data/raw"

s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    aws_session_token=os.getenv('AWS_SESSION_TOKEN')
)

def upload_pasta_para_s3(pasta_local: Path, bucket: str, prefixo: str):
    """Lê todos os arquivos de uma pasta local recursivamente e envia para o S3."""
    for filepath in pasta_local.rglob('*'):
        if filepath.is_file():
            caminho_relativo = filepath.relative_to(pasta_local)
            chave_s3 = f"{prefixo}/{caminho_relativo}".replace("\\", "/")

            print(f"Fazendo upload: {filepath.name} -> s3://{bucket}/{chave_s3}")
            s3_client.upload_file(str(filepath), bucket, chave_s3)

if __name__ == "__main__":
    print(f"Sincronizando {PASTA_LOCAL} para o S3.")

    if PASTA_LOCAL.exists():
        upload_pasta_para_s3(PASTA_LOCAL, BUCKET_NAME, PREFIXO_S3)
        print("\nSincronização com o S3 concluída com sucesso!")
    else:
        print(f"\n[ERRO] A pasta local não foi encontrada: {PASTA_LOCAL}")