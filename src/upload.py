import os
import boto3
from datetime import datetime
from dotenv import load_dotenv

# 1. Carrega as variáveis de ambiente do ficheiro .env
load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")

# 2. Detalhes exatos do teu contrato
SELLER_ID = "AKIAS3CAQLRALQDSSYV2"
CONTRACT_ID = "recUat6mSQSsbwZzp"
BUCKET_NAME = "databoutique.com"

# 3. Gerar a data atual no formato YYYY-MM-DD
today = datetime.utcnow().strftime("%Y-%m-%d")
s3_key = f"sellers/{SELLER_ID}/{CONTRACT_ID}/{today}/data_file.txt"

print("A iniciar comunicação com a AWS S3...")
print(f"Destino: s3://{BUCKET_NAME}/{s3_key}")

# 4. Iniciar cliente S3
client_kwargs = {
    'aws_access_key_id': AWS_ACCESS_KEY,
    'aws_secret_access_key': AWS_SECRET_KEY,
}
if AWS_SESSION_TOKEN:
    client_kwargs['aws_session_token'] = AWS_SESSION_TOKEN

s3 = boto3.client('s3', **client_kwargs)

# 5. Enviar o ficheiro
try:
    print("A enviar o ficheiro data_file.txt...")
    s3.upload_file("data_file.txt", BUCKET_NAME, s3_key)
    print("Sucesso! Ficheiro entregue corretamente.")
except Exception as e:
    print(f"Erro ao enviar o ficheiro: {e}")