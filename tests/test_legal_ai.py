import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.legal_ai import LegalAI, LegalAIError, ProviderRuntime


def settings() -> Settings:
    return Settings(
        root=Path("."), database_path=":memory:", auth_required=False,
        environment="test", allow_demo_sources=False, ai_model="test-model",
    )


def chat_response(text: str, finish_reason: str = "stop") -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(
        finish_reason=finish_reason,
        message=SimpleNamespace(content=text),
    )])


def test_legal_ai_sends_local_history_and_governed_context_without_provider_storage():
    ai = LegalAI(settings())

    class FakeResponses:
        request = None

        def create(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(
                output_text="Mình hiểu câu hỏi của bạn về tách thửa.", status="completed"
            )

    responses = FakeResponses()
    ai.providers = [ProviderRuntime(
        "openai", "test-model", "responses", SimpleNamespace(responses=responses)
    )]
    result = ai.generate(
        history=[
            {"role": "user", "content": "alo"},
            {"role": "assistant", "content": "Chào bạn"},
            {"role": "user", "content": "tahc thua o tphcm la gi"},
        ],
        facts={"locality": "TP. Hồ Chí Minh"},
        sources=[{
            "title": "Nguồn kiểm thử", "location": "Điều 1",
            "effective_from": "2025-01-01", "locality": "TP. Hồ Chí Minh",
            "applicability": "candidate", "governance_status": "full_text_verified",
            "provision_text": "Nội dung pháp lý kiểm thử.",
        }],
        source_notice=None,
    )

    assert "tách thửa" in result.answer
    assert responses.request["store"] is False
    assert len(responses.request["input"]) == 2  # old greeting was removed
    assert "tách thửa" in responses.request["input"][-1]["content"]
    assert "Nguồn kiểm thử" in responses.request["instructions"]
    assert "Không bịa điều luật" in responses.request["instructions"]


def test_legal_query_normalization_handles_missing_accents_and_typo():
    from app.knowledge import KnowledgeRepository

    assert KnowledgeRepository._fold("Tách thửa ở TP.HCM") == "tach thua o tp.hcm"
    assert KnowledgeRepository._near_token("tahc", {"tach", "thua"})


def test_provider_error_preserves_safe_error_code():
    class QuotaError(Exception):
        body = {"code": "insufficient_quota", "message": "sensitive provider detail"}

    error = LegalAI._provider_error(QuotaError())
    assert error.code == "insufficient_quota"
    assert "sensitive provider detail" not in str(error)


def test_gemini_adapter_is_sdk_independent_and_receives_same_instructions():
    ai = LegalAI(settings())

    class FakeModels:
        request = None

        def generate_content(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(text="Mình hiểu bạn đang hỏi về tách thửa.", candidates=[])

    models = FakeModels()
    ai.providers = [ProviderRuntime(
        "gemini", "gemini-test", "gemini", SimpleNamespace(models=models)
    )]
    result = ai.generate(
        history=[{"role": "user", "content": "tahc thua la gi"}],
        facts={}, sources=[], source_notice=None,
    )

    assert result.provider == "gemini"
    assert models.request["contents"][0]["role"] == "user"
    assert models.request["config"]["thinking_config"]["thinking_level"] == "LOW"
    assert "Không bịa điều luật" in models.request["config"]["system_instruction"]


def test_all_provider_protocols_receive_equivalent_governed_payload():
    captured: dict[str, dict] = {}

    class Responses:
        def create(self, **kwargs):
            captured["openai"] = kwargs
            return SimpleNamespace(output_text="Trả lời tương đương.", status="completed")

    class Models:
        def generate_content(self, **kwargs):
            captured["gemini"] = kwargs
            return SimpleNamespace(text="Trả lời tương đương.", candidates=[])

    class Completions:
        def __init__(self, provider: str):
            self.provider = provider

        def create(self, **kwargs):
            captured[self.provider] = kwargs
            return chat_response("Trả lời tương đương.")

    runtimes = [
        ProviderRuntime("openai", "openai-test", "responses", SimpleNamespace(responses=Responses())),
        ProviderRuntime("gemini", "gemini-test", "gemini", SimpleNamespace(models=Models())),
        ProviderRuntime(
            "groq", "groq-test", "chat_completions",
            SimpleNamespace(chat=SimpleNamespace(completions=Completions("groq"))),
        ),
        ProviderRuntime(
            "cloudflare", "cloudflare-test", "chat_completions",
            SimpleNamespace(chat=SimpleNamespace(completions=Completions("cloudflare"))),
        ),
    ]
    results = []
    for runtime in runtimes:
        ai = LegalAI(settings())
        ai.providers = [runtime]
        results.append(ai.generate(
            history=[{"role": "user", "content": "Tách thửa là gì?"}],
            facts={"locality": "TP. Hồ Chí Minh"},
            sources=[{
                "title": "Nguồn kiểm thử", "location": "Điều 1",
                "effective_from": "2025-01-01", "locality": "TP. Hồ Chí Minh",
                "applicability": "candidate", "governance_status": "full_text_verified",
                "provision_text": "Nội dung pháp lý kiểm thử.",
            }],
            source_notice=None,
        ))

    system_instructions = [
        captured["openai"]["instructions"],
        captured["gemini"]["config"]["system_instruction"],
        captured["groq"]["messages"][0]["content"],
        captured["cloudflare"]["messages"][0]["content"],
    ]
    user_messages = [
        captured["openai"]["input"],
        captured["gemini"]["contents"],
        captured["groq"]["messages"][1:],
        captured["cloudflare"]["messages"][1:],
    ]
    assert all(value == system_instructions[0] for value in system_instructions)
    assert all(rows[0]["role"] == "user" for rows in user_messages)
    assert all("Tách thửa là gì?" in str(rows[0]) for rows in user_messages)
    assert all(result.answer == "Trả lời tương đương." for result in results)
    assert [result.provider for result in results] == [
        "openai", "gemini", "groq", "cloudflare",
    ]


class FakeChatCompletions:
    def __init__(self, outcome):
        self.outcome = outcome
        self.calls = 0

    def create(self, **_):
        self.calls += 1
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return chat_response(self.outcome)


def chat_client(outcome):
    completions = FakeChatCompletions(outcome)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions)), completions


@pytest.mark.parametrize("first_error", [
    type("QuotaError", (Exception,), {"status_code": 429})(),
    TimeoutError("private timeout detail"),
])
def test_infrastructure_failure_moves_to_next_provider(first_error):
    ai = LegalAI(settings())
    first, first_calls = chat_client(first_error)
    second, second_calls = chat_client("Xin chào, mình có thể hỗ trợ bạn.")
    ai.providers = [
        ProviderRuntime("groq", "groq-test", "chat_completions", first),
        ProviderRuntime("gemini", "gemini-test", "chat_completions", second),
    ]

    result = ai.generate(
        history=[{"role": "user", "content": "xin chào"}],
        facts={}, sources=[], source_notice=None,
    )
    assert result.provider == "gemini"
    assert first_calls.calls == 1
    assert second_calls.calls == 1


def test_three_provider_failover_stops_at_first_success():
    ai = LegalAI(settings())
    groq, groq_calls = chat_client(TimeoutError())
    unavailable = type("Unavailable", (Exception,), {"status_code": 503})()
    gemini, gemini_calls = chat_client(unavailable)
    cloudflare, cloudflare_calls = chat_client("Đã kết nối trợ lý.")
    ai.providers = [
        ProviderRuntime("groq", "g", "chat_completions", groq),
        ProviderRuntime("gemini", "m", "chat_completions", gemini),
        ProviderRuntime("cloudflare", "c", "chat_completions", cloudflare),
    ]

    result = ai.generate(
        history=[{"role": "user", "content": "alo"}],
        facts={}, sources=[], source_notice=None,
    )
    assert result.provider == "cloudflare"
    assert [groq_calls.calls, gemini_calls.calls, cloudflare_calls.calls] == [1, 1, 1]


def test_all_infrastructure_failures_are_reported_as_overload():
    ai = LegalAI(settings())
    one, _ = chat_client(TimeoutError())
    two, _ = chat_client(type("Unavailable", (Exception,), {"status_code": 503})())
    ai.providers = [
        ProviderRuntime("groq", "g", "chat_completions", one),
        ProviderRuntime("gemini", "m", "chat_completions", two),
    ]
    with pytest.raises(LegalAIError) as raised:
        ai.generate(
            history=[{"role": "user", "content": "xin chào"}],
            facts={}, sources=[], source_notice=None,
        )
    assert raised.value.code == "all_providers_unavailable"


def test_invalid_legal_output_repairs_same_provider_and_never_switches():
    ai = LegalAI(settings())
    bad, bad_calls = chat_client("{}")
    backup, backup_calls = chat_client(json.dumps({"issues": []}))
    ai.providers = [
        ProviderRuntime("groq", "g", "chat_completions", bad),
        ProviderRuntime("gemini", "m", "chat_completions", backup),
    ]
    with pytest.raises(LegalAIError) as raised:
        ai.generate(
            history=[{"role": "user", "content": "Tôi có sang tên đất được không?"}],
            facts={}, sources=[], source_notice=None,
        )
    assert raised.value.code == "invalid_output"
    assert bad_calls.calls == 2
    assert backup_calls.calls == 0
