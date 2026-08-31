from unittest.mock import MagicMock, patch
import importlib

import pytest
from botocore.exceptions import ClientError

bedrock_client = importlib.import_module("src.03_concierge.bedrock_client")
DEFAULT_MAX_TOKENS = bedrock_client.DEFAULT_MAX_TOKENS
DEFAULT_MODEL_ID = bedrock_client.DEFAULT_MODEL_ID
DEFAULT_REGION = bedrock_client.DEFAULT_REGION
DEFAULT_TEMPERATURE = bedrock_client.DEFAULT_TEMPERATURE
DEFAULT_TOP_P = bedrock_client.DEFAULT_TOP_P
create_bedrock_client = bedrock_client.create_bedrock_client
generate_text = bedrock_client.generate_text
get_bedrock_model_id = bedrock_client.get_bedrock_model_id


@pytest.fixture(autouse=True)
def isolate_bedrock_environment(monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)


def bedrock_response(*content_blocks):
    return {
        "output": {
            "message": {
                "content": list(content_blocks),
            }
        }
    }


def test_default_model_id():
    assert get_bedrock_model_id() == DEFAULT_MODEL_ID
    assert DEFAULT_MODEL_ID == "mistral.mistral-large-3-675b-instruct"


def test_environment_model_id_overrides_default(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "custom.model")

    assert get_bedrock_model_id() == "custom.model"


@pytest.mark.parametrize("model_id", ["", "   "])
def test_empty_environment_model_id_raises_value_error(
    monkeypatch,
    model_id,
):
    monkeypatch.setenv("BEDROCK_MODEL_ID", model_id)

    with pytest.raises(ValueError, match="BEDROCK_MODEL_ID"):
        get_bedrock_model_id()


def test_create_client_uses_default_region_and_runtime_service():
    fake_session = MagicMock()
    fake_client = MagicMock()
    fake_session.client.return_value = fake_client

    with patch.object(
        bedrock_client.boto3, "Session",
        return_value=fake_session,
    ) as session_class:
        client = create_bedrock_client()

    session_class.assert_called_once_with(region_name=DEFAULT_REGION)
    fake_session.client.assert_called_once_with("bedrock-runtime")
    assert client is fake_client


def test_create_client_uses_environment_region(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "sa-east-1")

    with patch.object(
        bedrock_client.boto3, "Session"
    ) as session_class:
        create_bedrock_client()

    session_class.assert_called_once_with(region_name="sa-east-1")


@pytest.mark.parametrize("region", ["", "   "])
def test_empty_environment_region_raises_value_error(
    monkeypatch,
    region,
):
    monkeypatch.setenv("AWS_REGION", region)

    with patch.object(
        bedrock_client.boto3, "Session"
    ) as session_class:
        with pytest.raises(ValueError, match="AWS_REGION"):
            create_bedrock_client()

    session_class.assert_not_called()


def test_create_client_uses_profile_and_region(monkeypatch):
    monkeypatch.setenv("AWS_PROFILE", "conectatel")
    monkeypatch.setenv("AWS_REGION", "us-west-2")

    with patch.object(
        bedrock_client.boto3, "Session"
    ) as session_class:
        create_bedrock_client()

    session_class.assert_called_once_with(
        profile_name="conectatel",
        region_name="us-west-2",
    )


@pytest.mark.parametrize("system_prompt", ["", "   ", None, 123])
def test_invalid_system_prompt_raises_value_error(system_prompt):
    with pytest.raises(ValueError, match="system_prompt"):
        generate_text(
            system_prompt,
            "Pergunta válida",
            client=MagicMock(),
        )


@pytest.mark.parametrize("user_prompt", ["", "   ", None, 123])
def test_invalid_user_prompt_raises_value_error(user_prompt):
    with pytest.raises(ValueError, match="user_prompt"):
        generate_text(
            "Instrução válida",
            user_prompt,
            client=MagicMock(),
        )


def test_generate_text_sends_expected_converse_request(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "configured.model")
    client = MagicMock()
    client.converse.return_value = bedrock_response(
        {"text": "Resposta grounded."}
    )

    result = generate_text(
        "Use somente o contexto.",
        "Qual é o plano?",
        client=client,
    )

    assert result == "Resposta grounded."
    client.converse.assert_called_once_with(
        modelId="configured.model",
        system=[{"text": "Use somente o contexto."}],
        messages=[
            {
                "role": "user",
                "content": [{"text": "Qual é o plano?"}],
            }
        ],
        inferenceConfig={
            "maxTokens": DEFAULT_MAX_TOKENS,
            "temperature": DEFAULT_TEMPERATURE,
            "topP": DEFAULT_TOP_P,
        },
    )


def test_generate_text_creates_client_when_not_injected():
    client = MagicMock()
    client.converse.return_value = bedrock_response({"text": "Resposta"})

    with patch.object(
        bedrock_client, "create_bedrock_client",
        return_value=client,
    ) as create_client:
        result = generate_text("Sistema", "Usuário")

    create_client.assert_called_once_with()
    assert result == "Resposta"


def test_generate_text_does_not_create_client_when_injected():
    client = MagicMock()
    client.converse.return_value = bedrock_response({"text": "Resposta"})

    with patch.object(
        bedrock_client, "create_bedrock_client"
    ) as create_client:
        generate_text("Sistema", "Usuário", client=client)

    create_client.assert_not_called()
    client.converse.assert_called_once()


def test_generate_text_strips_only_response_edges():
    client = MagicMock()
    client.converse.return_value = bedrock_response(
        {"text": "  Primeira linha.\nSegunda linha.  "}
    )

    result = generate_text("Sistema", "Usuário", client=client)

    assert result == "Primeira linha.\nSegunda linha."


def test_generate_text_returns_first_valid_text_block():
    client = MagicMock()
    client.converse.return_value = bedrock_response(
        {"image": {"format": "png"}},
        {"text": "   "},
        "invalid",
        {"text": " Primeiro texto válido. "},
        {"text": "Segundo texto válido."},
    )

    result = generate_text("Sistema", "Usuário", client=client)

    assert result == "Primeiro texto válido."


@pytest.mark.parametrize(
    "invalid_response",
    [
        None,
        {},
        {"output": None},
        {"output": {}},
        {"output": {"message": None}},
        {"output": {"message": {}}},
        {"output": {"message": {"content": None}}},
        {"output": {"message": {"content": []}}},
        bedrock_response({"image": {"format": "png"}}),
        bedrock_response({"text": "   "}),
    ],
)
def test_invalid_bedrock_response_raises_runtime_error(
    invalid_response,
):
    client = MagicMock()
    client.converse.return_value = invalid_response

    with pytest.raises(RuntimeError, match="Resposta inválida"):
        generate_text("Sistema", "Usuário", client=client)


def test_sdk_exception_propagates_unchanged():
    error = ClientError(
        {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "Access denied",
            }
        },
        "Converse",
    )
    client = MagicMock()
    client.converse.side_effect = error

    with pytest.raises(ClientError) as raised:
        generate_text("Sistema", "Usuário", client=client)

    assert raised.value is error
    client.converse.assert_called_once()
