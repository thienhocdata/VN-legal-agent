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
    mortgage_duties = source("civil-code-91-2015-qh13-art-320")
    mortgage_rights = source("civil-code-91-2015-qh13-art-321")
    if not land_conditions:
        return safe_inconclusive_answer(facts=facts, sources=sources, source_notice=source_notice)

    condition_index, condition_item = land_conditions
    question_text = question.strip()
    question_ending = "" if question_text.endswith((".", "?", "!")) else "."
    known = [
        f"- Yêu cầu hiện tại: {question_text}{question_ending}",
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
    if facts.get("mortgage_status") is True:
        known.append("- Bạn cung cấp: quyền sử dụng đất vẫn đang thế chấp tại ngân hàng.")
    if facts.get("mortgagee_consent_status") is False:
        known.append("- Bạn cung cấp: ngân hàng chưa có văn bản đồng ý cho chuyển nhượng.")
    if facts.get("contract_notarized_status") is True:
        known.append("- Bạn cung cấp: hợp đồng chuyển nhượng đã được công chứng.")

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
    if mortgage_duties:
        index, item = mortgage_duties
        evidence.append(
            f"- Nghĩa vụ của bên thế chấp khi định đoạt tài sản: [Nguồn {index}], {item.get('location')}."
        )
    if mortgage_rights:
        index, item = mortgage_rights
        evidence.append(
            f"- Trường hợp được bán tài sản đang thế chấp: [Nguồn {index}], {item.get('location')}."
        )

    interdisciplinary = ["Luật Đất đai đã được kiểm tra trực tiếp"]
    if notarization_process:
        interdisciplinary.append("Luật Công chứng đã được kiểm tra ở phần thủ tục công chứng hợp đồng")
    if registration_file or registration_process:
        interdisciplinary.append("Nghị định 101/2024/NĐ-CP về đăng ký biến động đã được kiểm tra")
    if mortgage_duties or mortgage_rights:
        interdisciplinary.append("Bộ luật Dân sự đã được kiểm tra ở phần quyền và nghĩa vụ của bên thế chấp")

    relevant_date = facts.get("relevant_date") or "ngày liên quan chưa xác định"
    if facts.get("mortgage_status") is True and facts.get("mortgagee_consent_status") is False:
        conclusion = (
            "**CHƯA THỂ KẾT LUẬN** — dữ kiện và nguồn hiện có chưa hỗ trợ việc nộp hồ sơ "
            "sang tên ngay. Tài sản vẫn đang thế chấp và bên nhận thế chấp chưa đồng ý; cần "
            "kiểm tra thêm hợp đồng thế chấp, trạng thái đăng ký biện pháp bảo đảm và liệu có "
            "quy định đặc thù nào cho phép chuyển nhượng mà không cần sự đồng ý hay không."
        )
    else:
        conclusion = (
            "**CHƯA THỂ KẾT LUẬN** — các dữ kiện bạn nêu đang phù hợp với phần lớn điều kiện "
            "cơ bản để chuyển nhượng, nhưng còn ba điểm có thể đảo kết luận: biện pháp khẩn cấp "
            "tạm thời, nghĩa vụ tài chính còn ghi nợ và quyền của vợ/chồng hoặc đồng chủ sử dụng. "
            "Nếu ba điểm này đều không vướng, về nguyên tắc bạn có thể ký hợp đồng có công "
            "chứng/chứng thực rồi thực hiện đăng ký biến động."
        )

    return (
        "**1. Dữ kiện**\n"
        + "\n".join(known)
        + "\n- Chưa đủ để chốt giao dịch. Cần xác minh thêm: " + "; ".join(missing) + ".\n\n"
        "**2. Ngoại lệ**\n"
        f"- [Nguồn {condition_index}], {condition_item.get('location')} có các ngoại lệ và điều kiện bổ sung theo loại đất, chủ thể nhận chuyển nhượng và trường hợp nghĩa vụ tài chính còn ghi nợ.\n"
        "- Nếu chỉ chuyển nhượng một phần thửa đất, phải kiểm tra thêm điều kiện tách thửa của TP.HCM; nguồn hiện có trong lượt này chưa đủ để kết luận phần đó.\n\n"
        "**3. Hiệu lực**\n"
        f"- [Nguồn {condition_index}] áp dụng từ {condition_item.get('effective_from')} đến {condition_item.get('effective_to') or 'nay'} trên phạm vi toàn quốc, phù hợp ngày {relevant_date}.\n"
        + (f"- [Nguồn {land_form[0]}] áp dụng tại cùng thời điểm và phạm vi.\n" if land_form else "")
        + (f"- [Nguồn {notarization_process[0]}] áp dụng từ {notarization_process[1].get('effective_from')} đến nay.\n" if notarization_process else "")
        + "\n**4. Văn bản liên ngành**\n- " + "; ".join(interdisciplinary) + ".\n"
        "- Thuế, lệ phí và chế độ tài sản vợ chồng chưa có đủ nguồn trực tiếp trong 8 kết quả của lượt này nên chưa chốt số tiền hoặc quyền ký.\n\n"
        "**5. Kết luận**\n"
        f"{conclusion}\n\n"
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
    cited = {
        int(value) for value in re.findall(r"\[Nguồn\s+(\d+)\]", answer, flags=re.IGNORECASE)
    }
    for index in cited:
        if index < 1 or index > len(sources):
            errors.append("invalid_source_index")
            continue
        source = sources[index - 1]
        if (
            source.get("applicability") != "candidate"
            or source.get("governance_status") != "full_text_verified"
        ):
            errors.append("citation_not_governed_candidate")

    if len(verdict_matches) != 1:
        errors.append("invalid_verdict_count")
    else:
        verdict = verdict_matches[0].upper()
        if verdict not in ALLOWED_VERDICTS:
            errors.append("invalid_verdict")
        if verdict != "CHƯA THỂ KẾT LUẬN":
            candidates = governed_candidates(sources)
            governed_cited = [
                index for index in cited
                if 1 <= index <= len(sources)
                and sources[index - 1].get("applicability") == "candidate"
                and sources[index - 1].get("governance_status") == "full_text_verified"
            ]
            if not candidates or not governed_cited:
                errors.append("conclusive_verdict_without_direct_evidence")
    return not errors, list(dict.fromkeys(errors))


def safe_inconclusive_answer(
    *, facts: dict[str, Any], sources: list[dict[str, Any]], source_notice: str | None,
    question: str | None = None,
) -> str:
    """Produce a complete six-part answer when the model/source gate cannot safely conclude."""

    candidates = governed_candidates(sources)
    fact_labels = {
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
    if question and question.strip():
        question_text = question.strip()
        ending = "" if question_text.endswith((".", "?", "!")) else "."
        known_rows.append(f"- Yêu cầu hiện tại: {question_text}{ending}")
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


def _section(answer: str, number: int) -> str:
    """Extract one internal audit section without exposing its heading."""

    heading = AUDIT_HEADINGS[number - 1]
    start = answer.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    end = answer.find(AUDIT_HEADINGS[number], start) if number < len(AUDIT_HEADINGS) else len(answer)
    return answer[start:end].strip()


def _source_by_provision(
    sources: list[dict[str, Any]], provision_id: str,
) -> tuple[int, dict[str, Any]] | None:
    return next(
        (
            (index, item)
            for index, item in enumerate(sources[:8], 1)
            if item.get("provision_id") == provision_id
            and item.get("applicability") == "candidate"
            and item.get("governance_status") == "full_text_verified"
        ),
        None,
    )


def compose_user_facing_answer(
    *, audit_answer: str, question: str, facts: dict[str, Any],
    sources: list[dict[str, Any]], source_notice: str | None,
) -> str:
    """Turn the validated six-gate audit into a natural, still constrained answer."""

    mortgage_duties = _source_by_provision(sources, "civil-code-91-2015-qh13-art-320")
    mortgage_rights = _source_by_provision(sources, "civil-code-91-2015-qh13-art-321")
    land_form = _source_by_provision(sources, "land-law-consolidated-44-2026-vbhn-vpqh-art-27")
    registration = _source_by_provision(sources, "decree-101-2024-nd-cp-art-30")
    if (
        facts.get("mortgage_status") is True
        and facts.get("mortgagee_consent_status") is False
        and (mortgage_duties or mortgage_rights)
    ):
        rule_parts = []
        if mortgage_duties:
            index, item = mortgage_duties
            rule_parts.append(
                f"[Nguồn {index}], {item.get('location')} quy định bên thế chấp không được bán "
                "tài sản thế chấp, trừ các trường hợp luật cho phép"
            )
        if mortgage_rights:
            index, item = mortgage_rights
            rule_parts.append(
                f"[Nguồn {index}], {item.get('location')} cho phép bán tài sản không phải hàng "
                "hóa luân chuyển khi bên nhận thế chấp đồng ý hoặc luật có quy định khác"
            )
        form_note = ""
        if land_form:
            index, item = land_form
            form_note = (
                f" Việc hợp đồng đã được công chứng đáp ứng một phần yêu cầu về hình thức "
                f"([Nguồn {index}], {item.get('location')}), nhưng không tự làm chấm dứt thế chấp."
            )
        registration_note = ""
        if registration:
            index, item = registration
            registration_note = (
                f" Thành phần hồ sơ đăng ký biến động còn phải được đối chiếu theo "
                f"[Nguồn {index}], {item.get('location')}."
            )
        return (
            "Với dữ kiện bạn nêu, **bạn chưa nên nộp hồ sơ sang tên ngay**. "
            + "; trong khi ".join(rule_parts)
            + ". Ngân hàng chưa có văn bản đồng ý nên hồ sơ hiện chưa chứng minh được ngoại lệ này."
            + form_note
            + registration_note
            + "\n\nMình chưa khẳng định rằng mọi trường hợp đều bắt buộc phải giải chấp trước, vì còn phải "
            "kiểm tra hợp đồng thế chấp, trạng thái đăng ký biện pháp bảo đảm và khả năng áp dụng "
            "một cơ chế khác được ngân hàng chấp thuận. Nhưng với tình trạng hiện tại, chưa có đủ "
            "căn cứ để coi việc sang tên ngay là an toàn hoặc chắc chắn được tiếp nhận."
            + "\n\nTrước mắt, bạn nên làm việc với ngân hàng để xác định một trong các phương án: văn bản "
            "đồng ý chuyển nhượng, giải chấp, thay thế tài sản bảo đảm hoặc thỏa thuận ba bên. Sau "
            "đó mới đối chiếu hồ sơ đăng ký biến động tương ứng. Bạn có hợp đồng thế chấp và thông "
            "tin đăng ký thế chấp hiện tại để mình kiểm tra tiếp không?"
        )

    verdict_match = re.search(
        r"\*\*(ĐƯỢC|KHÔNG ĐƯỢC|CHƯA THỂ KẾT LUẬN)\*\*",
        audit_answer,
        flags=re.IGNORECASE,
    )
    verdict = verdict_match.group(1).upper() if verdict_match else "CHƯA THỂ KẾT LUẬN"
    conclusion = _section(audit_answer, 5)
    conclusion = re.sub(
        r"^\*\*(?:ĐƯỢC|KHÔNG ĐƯỢC|CHƯA THỂ KẾT LUẬN)\*\*\s*[—:-]?\s*",
        "",
        conclusion,
        flags=re.IGNORECASE,
    ).strip()
    if "cổng dữ kiện" in conclusion.lower():
        conclusion = (
            "Một số dữ kiện, ngoại lệ và căn cứ trực tiếp có thể làm thay đổi kết quả vẫn chưa "
            "được xác minh."
        )
    if verdict == "ĐƯỢC":
        direct = "Với dữ kiện và nguồn đã kiểm tra trong lượt này, hướng xử lý này có căn cứ để thực hiện."
    elif verdict == "KHÔNG ĐƯỢC":
        direct = "Với dữ kiện và nguồn đã kiểm tra trong lượt này, hướng xử lý này chưa đáp ứng điều kiện pháp lý."
    else:
        direct = "Với thông tin hiện có, mình chưa thể đưa ra một kết luận chắc chắn."
    if conclusion:
        direct += f" {conclusion}"

    evidence = _section(audit_answer, 6)
    facts_and_gaps = "\n".join(
        part for part in (_section(audit_answer, 1), _section(audit_answer, 2), _section(audit_answer, 4))
        if part
    )
    parts = [direct]
    if evidence and governed_candidates(sources):
        parts.append("**Căn cứ đã kiểm tra**\n\n" + evidence)
    if facts_and_gaps:
        parts.append("**Trước khi quyết định, bạn cần làm rõ thêm**\n\n" + facts_and_gaps)
    if not governed_candidates(sources):
        parts.append(
            "Corpus đã kiểm chứng hiện chưa có đủ nguồn trực tiếp cho tình huống này. Mình vẫn có "
            "thể giúp bạn xác định tài liệu cần chuẩn bị, nhưng sẽ không tự điền quy định còn thiếu "
            "bằng trí nhớ mô hình."
        )
    elif source_notice:
        parts.append(f"Lưu ý về phạm vi nguồn: {source_notice}")
    return "\n\n".join(parts)
