"""Deterministic safety gate for legal decision-support answers."""

from __future__ import annotations

import re
from typing import Any


AUDIT_HEADINGS = (
    "**1. Dữ kiện**",
    "**2. Ngoại lệ**",
    "**3. Hiệu lực**",
    "**4. Văn bản liên ngành**",
    "**5. Kết luận**",
    "**6. Bằng chứng trực tiếp**",
)

ALLOWED_VERDICTS = ("ĐƯỢC", "KHÔNG ĐƯỢC", "CHƯA THỂ KẾT LUẬN")

DECISION_ANSWER_CONTRACT = """
HỢP ĐỒNG OUTPUT CHO CÂU HỎI CẦN RA QUYẾT ĐỊNH
Khi người dùng hỏi một việc có được/không được, đủ điều kiện không, nên làm gì trong một tình huống cụ thể, câu trả lời bắt buộc có đúng sáu mục dưới đây theo đúng thứ tự:

**1. Dữ kiện**
- Nêu dữ kiện đã có, nguồn của dữ kiện và dữ kiện trọng yếu còn thiếu.
- Chỉ ghi "đủ" khi mọi điều kiện có khả năng quyết định kết quả đều đã có dữ liệu.

**2. Ngoại lệ**
- Nêu ngoại lệ, điều khoản chuyển tiếp, trường hợp loại trừ hoặc xung đột có thể đảo kết luận.
- Nếu corpus được cung cấp chưa đủ để kiểm tra, phải ghi rõ "chưa kiểm tra đủ", không được suy đoán là không có ngoại lệ.

**3. Hiệu lực**
- Đối chiếu ngày sự kiện với khoảng hiệu lực và địa phương của từng nguồn được dùng.
- Phân biệt quy định đang có hiệu lực hiện nay với quy định áp dụng cho một sự kiện trong quá khứ.

**4. Văn bản liên ngành**
- Ghi rõ các nhóm luật cùng điều chỉnh đã thực sự được kiểm tra từ nguồn được cung cấp.
- Nhóm chưa có trong nguồn phải ghi "chưa được kiểm tra"; không được dùng trí nhớ mô hình để lấp chỗ trống.

**5. Kết luận**
- Chỉ được chọn đúng một nhãn in đậm: **ĐƯỢC**, **KHÔNG ĐƯỢC**, hoặc **CHƯA THỂ KẾT LUẬN**.
- Phải chọn **CHƯA THỂ KẾT LUẬN** nếu thiếu dữ kiện trọng yếu, chưa kiểm tra ngoại lệ, chưa xác minh hiệu lực/địa phương, thiếu văn bản liên ngành trọng yếu, hoặc thiếu bằng chứng trực tiếp.

**6. Bằng chứng trực tiếp**
- Mỗi mệnh đề pháp lý trọng yếu phải gắn [Nguồn n] và vị trí điều/khoản tương ứng trong nguồn được cung cấp.
- Phân biệt bằng chứng trực tiếp, bằng chứng gián tiếp và khoảng trống bằng chứng.
- Không có nguồn trực tiếp thì phải ghi rõ chưa có bằng chứng trực tiếp.

Không đổi tên, bỏ mục hoặc gộp sáu mục. Không để văn phong tự nhiên làm mờ trạng thái kiểm tra.
""".strip()


def requires_decision_audit(message: str) -> bool:
    """Return True for a concrete legal eligibility or action question."""

    folded = message.lower().strip()
    if re.search(r"\b(là gì|nghĩa là gì|giải thích|khác nhau|tại sao|vì sao)\b", folded):
        return False
    patterns = (
        r"\b(có|được|đc|dc|không|ko)\s+.*\b(được|đc|dc|không|ko)\b",
        r"\b(đủ điều kiện|điều kiện|kiểm tra|kết luận|nên làm|có thể)\b",
        r"\b(chuyển nhượng|sang tên|bán đất|tách thửa|hợp thửa|thế chấp|tặng cho|thừa kế|đặt cọc)\b",
    )
    return any(re.search(pattern, folded) for pattern in patterns)


def governed_candidates(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item for item in sources[:8]
        if item.get("applicability") == "candidate"
        and item.get("governance_status") == "full_text_verified"
    ]


def validate_decision_answer(answer: str, sources: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """Validate structure and the minimum evidence needed for a conclusive verdict."""

    errors: list[str] = []
    positions = [answer.find(heading) for heading in AUDIT_HEADINGS]
    if any(position < 0 for position in positions):
        errors.append("missing_audit_heading")
    elif positions != sorted(positions):
        errors.append("wrong_heading_order")

    verdict_matches = re.findall(
        r"\*\*(ĐƯỢC|KHÔNG ĐƯỢC|CHƯA THỂ KẾT LUẬN)\*\*",
        answer,
        flags=re.IGNORECASE,
    )
    if len(verdict_matches) != 1:
        errors.append("invalid_verdict_count")
    else:
        verdict = verdict_matches[0].upper()
        if verdict not in ALLOWED_VERDICTS:
            errors.append("invalid_verdict")
        if verdict != "CHƯA THỂ KẾT LUẬN":
            candidates = governed_candidates(sources)
            cited = {
                int(value) for value in re.findall(r"\[Nguồn\s+(\d+)\]", answer, flags=re.IGNORECASE)
            }
            if not candidates or not cited or any(index < 1 or index > len(candidates) for index in cited):
                errors.append("conclusive_verdict_without_direct_evidence")
    return not errors, errors


def safe_inconclusive_answer(
    *, facts: dict[str, Any], sources: list[dict[str, Any]], source_notice: str | None,
) -> str:
    """Produce a complete six-part answer when the model/source gate cannot safely conclude."""

    candidates = governed_candidates(sources)
    fact_labels = {
        "case_purpose": "Yêu cầu",
        "locality": "Địa phương",
        "relevant_date": "Ngày liên quan",
        "certificate_status": "Giấy chứng nhận",
        "dispute_status": "Tranh chấp",
    }
    fact_values = {
        "certificate_status": {True: "đã có", False: "chưa có"},
        "dispute_status": {True: "đang có", False: "không có theo thông tin người dùng"},
    }
    known_rows = []
    for key, value in facts.items():
        if key not in fact_labels:
            continue
        display_value = fact_values.get(key, {}).get(value, value)
        ending = "" if str(display_value).rstrip().endswith((".", "?", "!")) else "."
        known_rows.append(f"- {fact_labels[key]}: {display_value}{ending}")
    known = "\n".join(known_rows) if known_rows else "- Chưa có dữ kiện hồ sơ được ghi nhận."
    missing = []
    if not facts.get("relevant_date"):
        missing.append("ngày của giao dịch hoặc sự kiện pháp lý")
    if not facts.get("locality"):
        missing.append("địa phương của bất động sản")
    if not candidates:
        missing.append("nguồn toàn văn đã kiểm chứng trực tiếp điều chỉnh tình huống")
    missing_text = "; ".join(missing) if missing else "các dữ kiện cấu thành điều kiện pháp lý cụ thể của giao dịch"

    if candidates:
        effect_rows = []
        evidence_rows = []
        for index, item in enumerate(candidates, 1):
            interval = f"từ {item.get('effective_from') or 'chưa rõ'} đến {item.get('effective_to') or 'chưa xác định ngày kết thúc'}"
            effect_rows.append(
                f"- [Nguồn {index}] {item.get('title')} — {interval}; địa phương: {item.get('locality') or 'toàn quốc'}."
            )
            evidence_rows.append(
                f"- [Nguồn {index}] {item.get('title')}, {item.get('location')}: có nguồn trực tiếp ở cấp điều khoản, nhưng chưa đủ chuỗi bằng chứng để kết luận toàn bộ tình huống."
            )
        effect_text = "\n".join(effect_rows)
        evidence_text = "\n".join(evidence_rows)
    else:
        effect_text = "- Chưa có nguồn đủ chuẩn để xác minh hiệu lực theo ngày và địa phương của tình huống."
        evidence_text = "- Chưa có bằng chứng trực tiếp đạt chuẩn toàn văn đã kiểm chứng; không dùng dữ liệu demo hoặc trí nhớ mô hình thay thế."

    notice = source_notice or "Không có cảnh báo nguồn bổ sung."
    return (
        "**1. Dữ kiện**\n"
        f"{known}\n"
        f"- Chưa đủ dữ kiện. Còn thiếu hoặc chưa chứng minh: {missing_text}.\n\n"
        "**2. Ngoại lệ**\n"
        "- Chưa kiểm tra đủ ngoại lệ, điều khoản chuyển tiếp và trường hợp loại trừ có thể làm thay đổi kết quả.\n\n"
        "**3. Hiệu lực**\n"
        f"{effect_text}\n\n"
        "**4. Văn bản liên ngành**\n"
        "- Chưa xác nhận đủ các văn bản đất đai, dân sự, công chứng, hôn nhân gia đình, nhà ở/kinh doanh bất động sản và bảo đảm giao dịch có liên quan.\n"
        f"- Trạng thái nguồn: {notice}\n\n"
        "**5. Kết luận**\n"
        "**CHƯA THỂ KẾT LUẬN** — chưa vượt qua đầy đủ cổng dữ kiện, ngoại lệ, hiệu lực, liên ngành và bằng chứng.\n\n"
        "**6. Bằng chứng trực tiếp**\n"
        f"{evidence_text}"
    )
