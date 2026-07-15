"""Deterministic safety gate for legal decision-support answers."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


DECISION_JSON_CONTRACT = """
HỢP ĐỒNG OUTPUT NỘI BỘ CHO CÂU HỎI CẦN RA QUYẾT ĐỊNH
Chỉ trả về một JSON object hợp lệ, không dùng Markdown và không thêm văn bản ngoài JSON:
{
  "issues": [
    {
      "issue": "một vấn đề pháp lý cụ thể",
      "status": "supported | not_supported | partially_supported | insufficient_basis",
      "finding": "nhận định ngắn, dễ hiểu và không vượt quá nguồn",
      "known_facts": ["dữ kiện và mức xác nhận/provenance tương ứng"],
      "missing_facts": ["dữ kiện trọng yếu còn thiếu"],
      "exceptions": ["ngoại lệ/chuyển tiếp chưa kiểm tra hoặc đã tìm thấy"],
      "effectiveness_check": "ngày sự kiện, khoảng hiệu lực và địa phương đã đối chiếu",
      "interdisciplinary_checks": ["nhóm văn bản đã kiểm tra hoặc còn thiếu"],
      "evidence": [
        {"source": 1, "location": "Điều/Khoản/Điểm", "supports": "mệnh đề được nguồn hỗ trợ"}
      ]
    }
  ],
  "overall_caution": "giới hạn chung còn lại",
  "follow_up_question": "tối đa một câu hỏi làm rõ quan trọng nhất hoặc chuỗi rỗng"
}

Quy tắc:
- Tách verdict riêng cho từng vấn đề; không dùng một verdict chung kéo tất cả vấn đề về cùng trạng thái.
- Chỉ dùng supported/not_supported khi có bằng chứng trực tiếp từ nguồn candidate/full_text_verified.
- Nếu thiếu dữ kiện, ngoại lệ, hiệu lực, liên ngành hoặc bằng chứng trực tiếp thì dùng partially_supported hoặc insufficient_basis.
- Mỗi evidence.source là số thứ tự [Nguồn n] được cung cấp; không tự tạo tên hoặc số Điều.
- Không dùng trí nhớ mô hình để lấp khoảng trống corpus.
""".strip()


STRUCTURED_STATUSES = {
    "supported", "not_supported", "partially_supported", "insufficient_basis",
}


def _json_object(raw: str) -> dict[str, Any] | None:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = __import__("json").loads(text)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def validate_decision_json(
    raw: str, sources: list[dict[str, Any]],
) -> tuple[bool, list[str], dict[str, Any] | None]:
    """Validate internal per-issue audit and all claim-to-source references."""

    payload = _json_object(raw)
    if payload is None:
        return False, ["invalid_json"], None
    errors: list[str] = []
    issues = payload.get("issues")
    if not isinstance(issues, list) or not issues:
        errors.append("missing_issues")
        issues = []
    if len(issues) > 8:
        errors.append("too_many_issues")
    for issue in issues:
        if not isinstance(issue, dict):
            errors.append("invalid_issue")
            continue
        if not str(issue.get("issue") or "").strip():
            errors.append("missing_issue_name")
        status = issue.get("status")
        if status not in STRUCTURED_STATUSES:
            errors.append("invalid_issue_status")
        if not str(issue.get("finding") or "").strip():
            errors.append("missing_finding")
        for key in (
            "known_facts", "missing_facts", "exceptions", "interdisciplinary_checks", "evidence",
        ):
            if not isinstance(issue.get(key), list):
                errors.append(f"invalid_{key}")
        if not isinstance(issue.get("effectiveness_check"), str):
            errors.append("invalid_effectiveness_check")
        evidence = issue.get("evidence") if isinstance(issue.get("evidence"), list) else []
        governed_evidence = 0
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("source"), int):
                errors.append("invalid_evidence")
                continue
            index = item["source"]
            if index < 1 or index > len(sources):
                errors.append("invalid_source_index")
                continue
            source = sources[index - 1]
            if (
                source.get("applicability") != "candidate"
                or source.get("governance_status") != "full_text_verified"
            ):
                errors.append("citation_not_governed_candidate")
            else:
                governed_evidence += 1
            if not str(item.get("supports") or "").strip():
                errors.append("missing_evidence_claim")
        if status in {"supported", "not_supported"} and not governed_evidence:
            errors.append("conclusive_issue_without_direct_evidence")
    if not isinstance(payload.get("overall_caution", ""), str):
        errors.append("invalid_overall_caution")
    if not isinstance(payload.get("follow_up_question", ""), str):
        errors.append("invalid_follow_up_question")
    return not errors, list(dict.fromkeys(errors)), payload


def compose_structured_user_answer(
    *, audit: dict[str, Any], sources: list[dict[str, Any]], source_notice: str | None,
) -> str:
    """Render the internal JSON audit as a natural answer without exposing its schema."""

    sections: list[str] = []
    status_openings = {
        "supported": "Có cơ sở để thực hiện",
        "not_supported": "Chưa đáp ứng điều kiện",
        "partially_supported": "Có cơ sở một phần nhưng chưa thể chốt",
        "insufficient_basis": "Chưa đủ căn cứ để kết luận",
    }
    issues = audit.get("issues") if isinstance(audit.get("issues"), list) else []
    multiple = len(issues) > 1
    for issue in issues:
        status = issue.get("status", "insufficient_basis")
        name = str(issue.get("issue") or "Vấn đề cần xem xét").strip()
        finding = str(issue.get("finding") or "").strip()
        opening = status_openings.get(status, status_openings["insufficient_basis"])
        title = f"**{name}**\n\n" if multiple else ""
        body = f"{opening}."
        if finding:
            body += f" {finding}"

        evidence_lines = []
        for evidence in issue.get("evidence") or []:
            index = evidence.get("source")
            if not isinstance(index, int) or not (1 <= index <= len(sources)):
                continue
            source = sources[index - 1]
            if (
                source.get("applicability") != "candidate"
                or source.get("governance_status") != "full_text_verified"
            ):
                continue
            location = evidence.get("location") or source.get("location")
            supports = str(evidence.get("supports") or "").strip()
            evidence_lines.append(
                f"- [Nguồn {index}], {location}: {supports}"
            )
        missing = [str(item).strip() for item in issue.get("missing_facts") or [] if str(item).strip()]
        exceptions = [str(item).strip() for item in issue.get("exceptions") or [] if str(item).strip()]
        pieces = [title + body]
        if evidence_lines:
            pieces.append("Căn cứ trực tiếp:\n" + "\n".join(evidence_lines[:4]))
        gaps = [*missing[:3], *exceptions[:2]]
        if gaps:
            pieces.append("Cần làm rõ thêm: " + "; ".join(gaps) + ".")
        sections.append("\n\n".join(pieces))

    caution = str(audit.get("overall_caution") or "").strip()
    if caution:
        sections.append(caution)
    if source_notice:
        sections.append(f"Phạm vi nguồn: {source_notice}")
    follow_up = str(audit.get("follow_up_question") or "").strip()
    if follow_up:
        sections.append(follow_up)
    return "\n\n".join(section for section in sections if section).strip()


def requires_decision_audit(message: str) -> bool:
    """Return True for a concrete legal eligibility or action question."""

    folded = "".join(
        char
        for char in unicodedata.normalize("NFD", message.lower().replace("đ", "d"))
        if unicodedata.category(char) != "Mn"
    )
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    folded = re.sub(r"\s+", " ", folded).strip()
    folded = re.sub(r"\b(k|khg|khongg|ko|hong)\b", "khong", folded)
    folded = re.sub(r"\b(dc|duoccc|duocc)\b", "duoc", folded)
    if re.search(r"\b(la gi|nghia la gi|giai thich|khac nhau|tai sao|vi sao)\b", folded):
        return False
    patterns = (
        r"\b(co|duoc|khong)\s+.*\b(duoc|khong)\b",
        r"\b(du dieu kien|dieu kien|kiem tra|ket luan|nen lam|co the)\b",
        r"\b(chuyen nhuong|sang ten|ban dat|tach thua|hop thua|the chap|tang cho|thua ke|dat coc)\b",
    )
    return any(re.search(pattern, folded) for pattern in patterns)


def classify_intent(message: str) -> str:
    """Classify conversational legal intent without treating it as a case fact."""

    folded = "".join(
        char
        for char in unicodedata.normalize("NFD", message.lower().replace("đ", "d"))
        if unicodedata.category(char) != "Mn"
    )
    folded = re.sub(r"[^a-z0-9]+", " ", folded).strip()
    if re.search(r"\b(la gi|nghia la gi|giai thich|tai sao|vi sao)\b", folded):
        return "definition"
    if re.search(r"\b(kiem tra|doc|review|xem giup).*(hop dong|giay to|van ban|so do)\b", folded):
        return "document_review"
    if re.search(r"\b(soan|viet|tao).*(don|hop dong|bien ban|van ban)\b", folded):
        return "drafting"
    if re.search(r"\b(thu tuc|ho so|nop o dau|co quan nao|mat bao lau)\b", folded):
        return "procedure"
    if requires_decision_audit(message):
        return "legal_decision"
    return "general_conversation"
