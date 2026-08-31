FROM public.ecr.aws/lambda/python:3.11

COPY src/05_integracao_auditoria_qualidade/deployment/lambda/requirements-lambda.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --only-binary=:all: -r /tmp/requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY src "${LAMBDA_TASK_ROOT}/src"
COPY src/05_integracao_auditoria_qualidade/deployment/lambda/app.py "${LAMBDA_TASK_ROOT}/app.py"

CMD ["app.lambda_handler"]
