/* ============================================
   SWINBURNE AI ADMISSION CONSULTANT — SCRIPT
   ============================================ */

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initMobileMenu();
  initChatWidget();
  initFaqChips();
});

/* ---------- 1. DARK / LIGHT MODE ---------- */
function initTheme() {
  const root = document.documentElement;
  const toggleBtn = document.getElementById("themeToggle");
  const icon = toggleBtn.querySelector(".theme-toggle__icon");

  // Load saved preference, default to dark (Swinburne red-black)
  const saved = localStorage.getItem("swin-theme") || "dark";
  root.setAttribute("data-theme", saved);
  updateIcon(saved);

  toggleBtn.addEventListener("click", () => {
    const current = root.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    localStorage.setItem("swin-theme", next);
    updateIcon(next);
  });

  function updateIcon(theme) {
    icon.textContent = theme === "dark" ? "◐" : "◑";
  }
}

/* ---------- 2. MOBILE MENU ---------- */
function initMobileMenu() {
  const menuBtn = document.getElementById("menuToggle");
  const navLinks = document.getElementById("navLinks");

  menuBtn.addEventListener("click", () => {
    navLinks.classList.toggle("open");
  });

  // Close menu when a link is clicked
  navLinks.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => navLinks.classList.remove("open"));
  });
}

/* ---------- 3. CHAT WIDGET ---------- */
function initChatWidget() {
  const fab = document.getElementById("chatFab");
  const panel = document.getElementById("chatPanel");
  const closeBtn = document.getElementById("chatClose");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const messages = document.getElementById("chatMessages");
  const suggestions = document.getElementById("chatSuggestions");

  fab.addEventListener("click", () => {
    panel.classList.toggle("open");
    panel.setAttribute("aria-hidden", !panel.classList.contains("open"));
    if (panel.classList.contains("open")) input.focus();
  });

  closeBtn.addEventListener("click", () => {
    panel.classList.remove("open");
    panel.setAttribute("aria-hidden", "true");
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;
    sendMessage(question);
    input.value = "";
  });

  suggestions.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      sendMessage(chip.dataset.question);
    });
  });

  function addMessage(text, sender) {
    const bubble = document.createElement("div");
    bubble.className = `msg msg--${sender}`;
    const p = document.createElement("p");
    p.innerHTML = marked.parse(text);
    bubble.appendChild(p);
    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
    return bubble;
  }

  async function sendMessage(question) {
    addMessage(question, "user");

    const typingBubble = addMessage("Đang soạn câu trả lời...", "bot");

    try {
      // TODO: replace with real backend endpoint, e.g. FastAPI /chat
      const answer = await fetchAIReply(question);
      typingBubble.querySelector("p").innerHTML = marked.parse(answer);
    } catch (err) {
      typingBubble.querySelector("p").textContent =
        "Xin lỗi, hiện chưa thể kết nối tới trợ lý AI. Vui lòng thử lại sau.";
      console.error("Chat error:", err);
    }
  }

  // Placeholder for backend integration.
  // Replace this with an actual fetch() call to your FastAPI /chat endpoint
  // which forwards the question to Gemini 2.5 Flash-Lite with FAQ/program context.
  async function fetchAIReply(question) {
    // Example of the real call once backend is ready:
    //
     const res = await fetch("/chat", {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify({ question, session_id: getSessionId() })
     });
     const data = await res.json();
     return data.answer;

    await new Promise((r) => setTimeout(r, 700));
    return `(Demo) Bạn vừa hỏi: "${question}". Khi backend được kết nối, trợ lý AI sẽ trả lời dựa trên dữ liệu tuyển sinh thực tế của Swinburne Việt Nam.`;
  }
}

/* ---------- 4. FAQ CHIPS ON PAGE -> OPEN CHAT WITH QUESTION ---------- */
function initFaqChips() {
  const chips = document.querySelectorAll(".faq-chip");
  const fab = document.getElementById("chatFab");
  const panel = document.getElementById("chatPanel");
  const input = document.getElementById("chatInput");
  const form = document.getElementById("chatForm");

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      panel.classList.add("open");
      panel.setAttribute("aria-hidden", "false");
      input.value = chip.dataset.question;
      form.dispatchEvent(new Event("submit", { cancelable: true }));
    });
  });
}

/* ---------- 5. SESSION ID (for chat history, used once DB is connected) ---------- */
function getSessionId() {
  let id = localStorage.getItem("swin-chat-session");
  if (!id) {
    id = "sess_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9);
    localStorage.setItem("swin-chat-session", id);
  }
  return id;
}
