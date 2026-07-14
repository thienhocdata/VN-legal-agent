from pathlib import Path
from types import SimpleNamespace

from app.config import Settings
from app.legal_ai import LegalAI


def test_legal_ai_sends_local_history_and_governed_context_without_provider_storage():
    settings = Settings(
        root=Path("."),
        database_path=":memory:",
        auth_required=False,
        environment="test",
        allow_demo_sources=True,
        ai_model="test-model",
    )
    ai = LegalAI(settings)

    class FakeResponses:
        request = None

        def create(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(output_text="Mình hiểu câu hỏi của bạn về tách thửa.")

    responses = FakeResponses()
    ai.client = SimpleNamespace(responses=responses)
    result = ai.generate(
        history=[{"role": "user", "content": "tahc thua o tphcm la gi"}],
        facts={"locality": "TP. Hồ Chí Minh"},
        sources=[{
            "title": "Nguồn kiểm thử",
            "location": "Điều 1",
            "effective_from": "2025-01-01",
            "locality": "TP. Hồ Chí Minh",
            "applicability": "candidate",
            "summary": "Nội dung pháp lý kiểm thử.",
        }],
        source_notice=None,
    )

    assert "tách thửa" in result.answer
    assert responses.request["store"] is False
    assert responses.request["input"][-1]["content"].startswith("tahc thua o tphcm la gi")
    assert "tách thửa" in responses.request["input"][-1]["content"]
    assert "Hiểu lỗi chính tả" in responses.request["instructions"]
    assert "Nguồn kiểm thử" in responses.request["instructions"]
    assert "Không bịa điều luật" in responses.request["instructions"]


def test_legal_query_normalization_handles_missing_accents_and_typo():
    from app.knowledge import KnowledgeRepository

    assert KnowledgeRepository._fold("Tách thửa ở TP.HCM") == "tach thua o tp.hcm"
    assert KnowledgeRepository._near_token("tahc", {"tach", "thua"})


def test_provider_error_preserves_safe_error_code():
    settings = Settings(
        root=Path("."), database_path=":memory:", auth_required=False,
        environment="test", allow_demo_sources=True, ai_model="test-model",
    )
    ai = LegalAI(settings)

    class QuotaError(Exception):
        body = {"code": "insufficient_quota", "message": "sensitive provider detail"}

    class FailingResponses:
        @staticmethod
        def create(**_):
            raise QuotaError()

    ai.client = SimpleNamespace(responses=FailingResponses())
    from app.legal_ai import LegalAIError
    try:
        ai.generate(history=[{"role": "user", "content": "xin chào"}], facts={}, sources=[], source_notice=None)
        assert False, "Expected LegalAIError"
    except LegalAIError as exc:
        assert exc.code == "insufficient_quota"
        assert "sensitive provider detail" not in str(exc)


def test_gemini_receives_history_and_same_legal_instructions():
    settings = Settings(
        root=Path("."), database_path=":memory:", auth_required=False,
        environment="test", allow_demo_sources=True, ai_provider="gemini",
        gemini_model="gemini-test-model",
    )
    ai = LegalAI(settings)

    class FakeModels:
        request = None

        def generate_content(self, **kwargs):
            self.request = kwargs
            return SimpleNamespace(text="Mình hiểu bạn đang hỏi về tách thửa.")

    models = FakeModels()
    ai.client = SimpleNamespace(models=models)
    result = ai.generate(
        history=[
            {"role": "user", "content": "tahc thua la gi"},
            {"role": "assistant", "content": "Bạn đang hỏi về tách thửa phải không?"},
            {"role": "user", "content": "dung roi o tphcm"},
        ],
        facts={"locality": "TP. Hồ Chí Minh"},
        sources=[],
        source_notice="Chưa có nguồn cụ thể cho lượt này.",
    )

    assert result.provider == "gemini"
    assert result.model == "gemini-test-model"
    assert models.request["model"] == "gemini-test-model"
    assert [item.role for item in models.request["contents"]] == ["user", "model", "user"]
    assert models.request["contents"][-1].parts[0].text == "dung roi o tphcm"
    assert "Hiểu lỗi chính tả" in models.request["config"].system_instruction
    assert "Không bịa điều luật" in models.request["config"].system_instruction
    assert models.request["config"].thinking_config.thinking_level == "LOW"


def test_gemini_rate_limit_is_normalized_without_exposing_provider_detail():
    settings = Settings(
        root=Path("."), database_path=":memory:", auth_required=False,
        environment="test", allow_demo_sources=True, ai_provider="gemini",
    )
    ai = LegalAI(settings)

    class GeminiQuotaError(Exception):
        code = 429

    class FailingModels:
        @staticmethod
        def generate_content(**_):
            raise GeminiQuotaError("private provider detail")

    ai.client = SimpleNamespace(models=FailingModels())
    from app.legal_ai import LegalAIError
    try:
        ai.generate(history=[{"role": "user", "content": "xin chào"}], facts={}, sources=[], source_notice=None)
        assert False, "Expected LegalAIError"
    except LegalAIError as exc:
        assert exc.code == "rate_limit_exceeded"
        assert "private provider detail" not in str(exc)
