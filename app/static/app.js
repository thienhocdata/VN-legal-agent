const api = "/api/v1";

let caseId = null;
let busy = false;

const $ = (id) => document.getElementById(id);

async function call(path, options = {}) {
  const key = localStorage.getItem("mla_api_key");
  const response = await fetch(`${api}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(key ? { "X-API-Key": key } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 401) {
    const entered = window.prompt("Nhập API key để tiếp tục:");
    if (entered?.trim()) {
      localStorage.setItem("mla_api_key", entered.trim());
      return call(path, options);
    }
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || "Không thể kết nối với trợ lý lúc này.");
  }

  return response.json();
}

function format(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

function scrollBottom() {
  requestAnimationFrame(() => {
    const conversation = $("conversation");
    conversation.scrollTop = conversation.scrollHeight;
  });
}

function addMessage(role, text, citations = []) {
  const welcome = $("welcome");
  if (welcome) welcome.hidden = true;

  const row = document.createElement("div");
  row.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = role === "assistant" ? "ML" : "Bạn";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = format(text);

  if (citations.length) {
    const details = document.createElement("details");
    details.className = "sources";
    const summary = document.createElement("summary");
    summary.textContent = `${citations.length} nguồn pháp lý được sử dụng`;
    details.appendChild(summary);

    citations.forEach((citation) => {
      const source = document.createElement("div");
      source.className = "source";
      const title = String(citation.title || "Nguồn pháp lý");
      if (/^https?:\/\//i.test(citation.url || "")) {
        const link = document.createElement("a");
        link.href = citation.url;
        link.target = "_blank";
        link.rel = "noopener";
        link.textContent = title;
        source.appendChild(link);
      } else {
        source.appendChild(document.createTextNode(title));
      }
      source.appendChild(document.createElement("br"));
      source.appendChild(document.createTextNode(
        [citation.location, citation.version].filter(Boolean).join(" · ")
      ));
      details.appendChild(source);
    });
    bubble.appendChild(details);
  }

  if (role === "assistant") row.appendChild(avatar);
  row.appendChild(bubble);
  $("messages").appendChild(row);
  scrollBottom();
}

function showTyping(show) {
  const existing = $("typing");
  if (!show) {
    if (existing) existing.remove();
    return;
  }
  if (existing) return;

  const row = document.createElement("div");
  row.id = "typing";
  row.className = "message assistant";
  row.innerHTML = '<div class="avatar">ML</div><div class="bubble typing" aria-label="Đang trả lời"><i></i><i></i><i></i></div>';
  $("messages").appendChild(row);
  scrollBottom();
}

function setSuggestions(suggestions = []) {
  const container = $("suggestions");
  container.replaceChildren();

  suggestions.slice(0, 3).forEach((suggestion) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = suggestion;
    button.addEventListener("click", () => send(suggestion));
    container.appendChild(button);
  });
}

function statusLabel(status) {
  return {
    conversation: "Bạn cần hỗ trợ gì?",
    intake_in_progress: "Mình đang lắng nghe",
    ready_for_analysis: "Đang phân tích tình huống",
    analysis_complete: "Đã có phân tích sơ bộ",
    review_required: "Đã có phân tích sơ bộ",
    needs_expert_review: "Cần chuyên gia kiểm tra",
    ai_unavailable: "AI chưa sẵn sàng",
  }[status] || "Bạn cần hỗ trợ gì?";
}

async function send(rawText) {
  const text = String(rawText || "").trim();
  if (!text || busy) return;

  busy = true;
  $("send").disabled = true;
  $("messageInput").value = "";
  resize();
  setSuggestions();
  addMessage("user", text);
  showTyping(true);

  try {
    const data = await call("/chat", {
      method: "POST",
      body: JSON.stringify({ case_id: caseId, message: text }),
    });

    caseId = data.case_id;
    addMessage("assistant", data.answer, data.citations);
    setSuggestions(data.suggestions);
    $("caseStatus").textContent = statusLabel(data.status);
  } catch (error) {
    addMessage("assistant", `Mình gặp lỗi kết nối: ${error.message}`);
    $("caseStatus").textContent = "Chưa thể kết nối";
  } finally {
    showTyping(false);
    busy = false;
    $("send").disabled = false;
    $("messageInput").focus();
    scrollBottom();
  }
}

function newConversation() {
  caseId = null;
  $("messages").replaceChildren();
  setSuggestions();
  $("welcome").hidden = false;
  $("caseStatus").textContent = "Bạn cần hỗ trợ gì?";
  $("messageInput").value = "";
  resize();
  $("messageInput").focus();
}

function resize() {
  const input = $("messageInput");
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 160)}px`;
}

async function checkAIStatus() {
  try {
    const response = await fetch("/health");
    const health = await response.json();
    if (health.ai_chat?.mode !== "model") {
      $("caseStatus").textContent = "AI chưa được kết nối";
      $("caseStatus").title = "Cần cấu hình OPENAI_API_KEY trên server";
    }
  } catch (_) {
    $("caseStatus").textContent = "Chưa thể kết nối";
  }
}

$("composer").addEventListener("submit", (event) => {
  event.preventDefault();
  send($("messageInput").value);
});

$("messageInput").addEventListener("input", resize);
$("messageInput").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    $("composer").requestSubmit();
  }
});

$("newChat").addEventListener("click", newConversation);
$("messageInput").focus();
checkAIStatus();
