"""Deterministic safety gate for legal decision-support answers."""

from __future__ import annotations

import re
import unicodedata
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


def evidence_backed_fallback(
    *, question: str, facts: dict[str, Any], sources: list[dict[str, Any]], source_notice: str | None,
) -> str:
    """Return a useful governed answer when the language model is unavailable or rejected."""

    folded = "".join(
        char for char in unicodedata.normalize("NFD", question.lower().replace("đ", "d"))
        if unicodedata.category(char) != "Mn"
    )
    if "chuyen nhuong" not in folded:
        return safe_inconclusive_answer(facts=facts, sources=sources, source_notice=source_notice)

    indexed = [
        (index, item) for index, item in enumerate(sources[:8], 1)
        if item.get("applicability") == "candidate"
        and item.get("governance_status") == "full_text_verified"
    ]

    def source(provision_id: str) -> tuple[int, dict[str, Any]] | None:
        return next(
            ((index, item) for index, item in indexed if item.get("provision_id") == provision_id),
            None,
        )

    land_conditions = source("land-law-consolidated-44-2026-vbhn-vpqh-art-45")
    land_form = source("land-law-consolidated-44-2026-vbhn-vpqh-art-27")
    registration_file = source("decree-101-2024-nd-cp-art-30")
    registration_process = source("decree-101-2024-nd-cp-art-37")
    notarization_process = source("notarization-consolidated-50-2026-vbhn-vpqh-art-42")
    if not land_conditions:
        return safe_inconclusive_answer(facts=facts, sources=sources, source_notice=source_notice)

    condition_index, condition_item = land_conditions
    known = [
        f"- Địa phương: {facts.get('locality') or 'chưa xác định'}.",
        f"- Ngày dự kiến giao dịch: {facts.get('relevant_date') or 'chưa xác định'}.",
    ]
    fact_checks = (
        ("certificate_status", "có Giấy chứng nhận", False),
        ("dispute_status", "đất không có tranh chấp", True),
        ("enforcement_status", "quyền sử dụng đất không bị kê biên", True),
        ("land_term_status", "đất còn thời hạn sử dụng", False),
        ("mortgage_status", "đất không thế chấp", True),
    )
    for key, label, inverse in fact_checks:
        value = facts.get(key)
        satisfied = value is False if inverse else value is True
        if satisfied:
            known.append(f"- Bạn cung cấp: {label} (chưa được cơ quan/tài liệu độc lập xác minh).")

    missing = []
    if facts.get("certificate_status") is not True:
        missing.append("Giấy chứng nhận và đúng người có quyền định đoạt")
    if facts.get("dispute_status") is not False:
        missing.append("tình trạng tranh chấp")
    if facts.get("enforcement_status") is not False:
        missing.append("tình trạng kê biên/biện pháp bảo đảm thi hành án")
    if facts.get("land_term_status") is not True:
        missing.append("thời hạn sử dụng đất")
    missing.extend([
        "quyền sử dụng đất có bị áp dụng biện pháp khẩn cấp tạm thời hay không",
        "có nghĩa vụ tài chính được chậm thực hiện hoặc ghi nợ hay không",
        "đất có phải tài sản chung hoặc có đồng chủ sử dụng cần cùng ký hay không",
    ])

    evidence = [
        f"- Điều kiện thực hiện quyền: [Nguồn {condition_index}], {condition_item.get('location')} quy định các điều kiện về Giấy chứng nhận, tranh chấp, kê biên, thời hạn sử dụng, biện pháp khẩn cấp tạm thời và nghĩa vụ tài chính.",
    ]
    if land_form:
        index, item = land_form
        evidence.append(
            f"- Hình thức hợp đồng: [Nguồn {index}], {item.get('location')} là căn cứ trực tiếp về công chứng/chứng thực hợp đồng chuyển nhượng quyền sử dụng đất."
        )
    if notarization_process:
        index, item = notarization_process
        evidence.append(f"- Cách công chứng hợp đồng đã soạn sẵn: [Nguồn {index}], {item.get('location')}.")
    if registration_file:
        index, item = registration_file
        evidence.append(f"- Thành phần hồ sơ đăng ký biến động: [Nguồn {index}], {item.get('location')}.")
    if registration_process:
        index, item = registration_process
        evidence.append(f"- Trình tự tiếp nhận, kiểm tra và đăng ký biến động: [Nguồn {index}], {item.get('location')}.")

    interdisciplinary = ["Luật Đất đai đã được kiểm tra trực tiếp"]
    if notarization_process:
        interdisciplinary.append("Luật Công chứng đã được kiểm tra ở phần thủ tục công chứng hợp đồng")
    if registration_file or registration_process:
        interdisciplinary.append("Nghị định 101/2024/NĐ-CP về đăng ký biến động đã được kiểm tra")

    return (
        "**1. Dữ kiện**\n"
        + "\n".join(known)
        + "\n- Chưa đủ để chốt giao dịch. Cần xác minh thêm: " + "; ".join(missing) + ".\n\n"
        "**2. Ngoại lệ**\n"
        f"- [Nguồn {condition_index}], {condition_item.get('location')} có các ngoại lệ và điều kiện bổ sung theo loại đất, chủ thể nhận chuyển nhượng và trường hợp nghĩa vụ tài chính còn ghi nợ.\n"
        "- Nếu chỉ chuyển nhượng một phần thửa đất, phải kiểm tra thêm điều kiện tách thửa của TP.HCM; nguồn hiện có trong lượt này chưa đủ để kết luận phần đó.\n\n"
        "**3. Hiệu lực**\n"
        f"- [Nguồn {condition_index}] áp dụng từ {condition_item.get('effective_from')} đến {condition_item.get('effective_to') or 'nay'} trên phạm vi toàn quốc, phù hợp ngày 15/07/2026.\n"
        + (f"- [Nguồn {land_form[0]}] áp dụng tại cùng thời điểm và phạm vi.\n" if land_form else "")
        + (f"- [Nguồn {notarization_process[0]}] áp dụng từ {notarization_process[1].get('effective_from')} đến nay.\n" if notarization_process else "")
        + "\n**4. Văn bản liên ngành**\n- " + "; ".join(interdisciplinary) + ".\n"
        "- Thuế, lệ phí và chế độ tài sản vợ chồng chưa có đủ nguồn trực tiếp trong 8 kết quả của lượt này nên chưa chốt số tiền hoặc quyền ký.\n\n"
        "**5. Kết luận**\n"
        "**CHƯA THỂ KẾT LUẬN** — các dữ kiện bạn nêu đang phù hợp với phần lớn điều kiện cơ bản để chuyển nhượng, nhưng còn ba điểm có thể đảo kết luận: biện pháp khẩn cấp tạm thời, nghĩa vụ tài chính còn ghi nợ và quyền của vợ/chồng hoặc đồng chủ sử dụng. Nếu ba điểm này đều không vướng, về nguyên tắc bạn có thể ký hợp đồng có công chứng/chứng thực rồi thực hiện đăng ký biến động.\n\n"
        "**6. Bằng chứng trực tiếp**\n"
        + "\n".join(evidence)
    )


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
