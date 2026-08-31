# Demonstração interna — Lambda e Amplify

## O que foi preparado

- Lambda container em `src/05_integracao_auditoria_qualidade/deployment/lambda`;
- API HTTP declarada em SAM;
- interruptor de demonstração no Parameter Store;
- interface estática em `deployment/web`, pronta para Amplify Hosting.

## Pré-requisitos locais

- AWS CLI autenticado na mesma conta e região do bucket/Bedrock;
- Docker Desktop em execução;
- AWS SAM CLI instalado;
- o vector store oficial publicado no S3.

## Publicar a API

Na raiz do repositório, substitua os nomes de bucket pelos valores reais:

```powershell
sam build --template-file src/05_integracao_auditoria_qualidade/deployment/infra/template.yaml
sam deploy --guided --template-file .aws-sam/build/template.yaml
```

Durante o assistente, informe `RagBucketName`, `AuditBucketName`, `S3Prefix` e
`AllowedOrigin`. Inicialmente use uma origem temporária ou `*`; depois de criar
o Amplify, atualize o stack com a URL exata do site.

O output `ApiUrl` é a URL a ser copiada para `deployment/web/config.js`.

## Publicar a interface no Amplify

1. Copie o `ApiUrl` para `config.js` e faça commit dessa URL pública.
2. No console AWS, abra **Amplify** → **New app** → **Host web app**.
3. Conecte o repositório GitHub e escolha a branch de demonstração.
4. Defina o diretório raiz como `src/05_integracao_auditoria_qualidade/deployment/web`.
5. Configure o build como estático, sem comando de build, com artefatos em `.`.
6. Após o deploy, copie a URL HTTPS do Amplify e atualize o parâmetro
   `AllowedOrigin` do stack SAM para essa URL.

## Ligar e desligar

O parâmetro `/conectatel/demo/enabled` inicia como `false`.

Para ligar antes da apresentação:

```powershell
aws ssm put-parameter --name /conectatel/demo/enabled --type String --value true --overwrite
```

Para desligar depois:

```powershell
aws ssm put-parameter --name /conectatel/demo/enabled --type String --value false --overwrite
```

A Lambda mantém o valor por até 30 segundos em cache. Quando desligada, ela não
faz chamadas a Bedrock nem grava auditoria.

## Teste de ponta a ponta

```powershell
$body = @{ question = 'Qual e o prazo para pedir reembolso?' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'COLE_AQUI_A_API_URL' -ContentType 'application/json' -Body $body
```

## Limpeza

Após a banca, desligue a demo. Se não precisar mais da infraestrutura, remova o
stack pelo CloudFormation/SAM e exclua as imagens não utilizadas no ECR.
