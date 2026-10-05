import os
import boto3
from dotenv import load_dotenv

load_dotenv()
s3 = boto3.client('s3', 
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
)

prefixo_geral = "sellers/AKIAS3CAQLRALQDSSYV2/recUat6mSQSsbwZzp/"
print("A analisar ficheiros do validador...")

resposta = s3.list_objects_v2(Bucket="databoutique.com", Prefix=prefixo_geral)

if 'Contents' in resposta:
    for item in resposta['Contents']:
        if "refused" in item['Key'].lower():
            print(f"Encontrado ficheiro de recusa: {item['Key']}")
            # Fazer download do ficheiro para a tua pasta src
            s3.download_file("databoutique.com", item['Key'], "erro_validador.txt")
            print("Ficheiro descarregado e guardado como 'erro_validador.txt'!")
else:
    print("Nenhum ficheiro encontrado.")