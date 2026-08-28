"""
hello_bedrock.py

Teste mínimo de acesso ao Amazon Bedrock a partir da conta AWS individual
do fellow. Use este script no primeiro dia do desafio para validar que:

  1. As credenciais AWS da conta (CLI configurado ou role) funcionam.
  2. O modelo Anthropic escolhido está habilitado na conta/região
     (após preencher o formulário de caso de uso no console do Bedrock).

Cada membro da squad, incluindo a conta escolhida para a
consolidação/demonstração, deve executar este script com sucesso e guardar
uma evidência (print de tela ou log) da chamada invoke_model bem-sucedida.

Uso:
    python hello_bedrock.py
"""

import json
import os
import sys

import boto3
from botocore.exceptions import ClientError

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv é opcional; variáveis de ambiente também funcionam sem ele

REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID = os.environ.get(
    "BEDROCK_GENERATION_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0"
)


def main() -> int:
    print(f"Região: {REGION}")
    print(f"Modelo:  {MODEL_ID}")
    print("Enviando chamada de teste ao Bedrock...\n")

    client = boto3.client("bedrock-runtime", region_name=REGION)

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 200,
        "messages": [
            {
                "role": "user",
                "content": "Responda em uma frase: o que é o desafio ConectaTel?",
            }
        ],
    }

    try:
        response = client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
    except ClientError as exc:
        print("FALHOU — a chamada invoke_model retornou um erro.\n")
        print(f"Código: {exc.response.get('Error', {}).get('Code')}")
        print(f"Mensagem: {exc.response.get('Error', {}).get('Message')}")
        print(
            "\nVerifique: (1) o formulário de caso de uso da Anthropic foi "
            "preenchido no console do Bedrock; (2) até ~15 minutos de "
            "propagação após o envio do formulário; (3) método de pagamento "
            "válido na conta; (4) permissões de IAM "
            "aws-marketplace:Subscribe/ViewSubscriptions; (5) região correta."
        )
        return 1

    payload = json.loads(response["body"].read())
    texto = payload.get("content", [{}])[0].get("text", "").strip()

    print("SUCESSO — resposta do modelo:\n")
    print(texto)
    print(
        "\nGuarde esta saída (print ou log) como evidência da chamada "
        "invoke_model bem-sucedida com um modelo Anthropic."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
