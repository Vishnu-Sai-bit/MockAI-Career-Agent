// AI Job Agent Companion v2 — DOM Autofill & Smart Screening Questions Engine

const BACKEND_BASE = "http://127.0.0.1:5000";

async function fetchCandidateProfile() {
  try {
    const res = await fetch(`${BACKEND_BASE}/api/v1/extension/profile`);
    const data = await res.json();
    if (data.success && data.candidate) {
      return data.candidate;
    }
  } catch (err) {
    console.warn("[AI Job Agent] Backend profile endpoint unavailable, using cached profile:", err);
  }
  return {
    firstName: "Vishnu Sai",
    lastName: "Beere",
    fullName: "Beere Vishnu Sai",
    email: "beerevishnusai776600@gmail.com",
    phone: "+91-9876543210",
    location: "Bengaluru, India",
    linkedin: "https://www.linkedin.com/in/vishnusai",
    github: "https://github.com/vishnusai",
    website: "https://github.com/vishnusai",
    headline: "Data Science & AI Engineer"
  };
}

async function autofillForm() {
  const candidate = await fetchCandidateProfile();
  let filledCount = 0;

  const fillInput = (selectorList, value) => {
    if (!value) return false;
    for (const sel of selectorList) {
      const el = document.querySelector(sel);
      if (el && (!el.value || el.value.trim() === "")) {
        el.value = value;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
        filledCount++;
        return true;
      }
    }
    return false;
  };

  // 1. First & Last Names
  fillInput([
    "input#first_name", "input[name='first_name']", "input[name='firstName']",
    "input[id*='first-name']", "input[id*='firstName']", "input[name*='first_name']",
    "input[data-automation-id*='legalNameSection_firstName']"
  ], candidate.firstName);

  fillInput([
    "input#last_name", "input[name='last_name']", "input[name='lastName']",
    "input[id*='last-name']", "input[id*='lastName']", "input[name*='last_name']",
    "input[data-automation-id*='legalNameSection_lastName']"
  ], candidate.lastName);

  // 2. Full Name
  fillInput([
    "input#name", "input[name='name']", "input[name='fullName']",
    "input[id*='name']"
  ], candidate.fullName);

  // 3. Email
  fillInput([
    "input#email", "input[name='email']", "input[type='email']",
    "input[id*='email']", "input[name*='email']",
    "input[data-automation-id*='email']"
  ], candidate.email);

  // 4. Phone
  fillInput([
    "input#phone", "input[name='phone']", "input[type='tel']",
    "input[id*='phone']", "input[name*='phone']",
    "input[data-automation-id*='phone']"
  ], candidate.phone);

  // 5. LinkedIn
  fillInput([
    "input[name*='linkedin']", "input[id*='linkedin']", "input[placeholder*='linkedin']",
    "input[aria-label*='LinkedIn']", "input[data-automation-id*='linkedin']"
  ], candidate.linkedin);

  // 6. GitHub / Portfolio / Website
  fillInput([
    "input[name*='github']", "input[id*='github']", "input[placeholder*='github']"
  ], candidate.github);

  fillInput([
    "input[name*='website']", "input[id*='website']", "input[placeholder*='website']",
    "input[name*='portfolio']", "input[id*='portfolio']"
  ], candidate.website);

  // 7. Location / City
  fillInput([
    "input#location", "input[name='location']", "input[id*='location']",
    "input[name*='city']", "input[id*='city']"
  ], candidate.location);

  // 8. Custom AI Screening Questions (Textareas)
  const textareas = document.querySelectorAll("textarea");
  for (const ta of textareas) {
    if (!ta.value || ta.value.trim() === "") {
      const label = document.querySelector(`label[for='${ta.id}']`) || ta.closest("label") || ta.parentElement;
      const questionText = (label ? label.textContent : "") || ta.placeholder || ta.name || "Why do you want to join?";
      if (questionText.length > 5) {
        try {
          const resp = await fetch(`${BACKEND_BASE}/api/v1/extension/answer-question`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: questionText.trim() })
          });
          const ansData = await resp.json();
          if (ansData.success && ansData.answer) {
            ta.value = ansData.answer;
            ta.dispatchEvent(new Event("input", { bubbles: true }));
            ta.dispatchEvent(new Event("change", { bubbles: true }));
            filledCount++;
          }
        } catch (e) {
          console.warn("[AI Job Agent] Question auto-answering error:", e);
        }
      }
    }
  }

  return filledCount;
}

// In-page Floating Quick Autofill Button
function injectFloatingButton() {
  if (document.getElementById("ai-job-agent-fab")) return;

  const fab = document.createElement("div");
  fab.id = "ai-job-agent-fab";
  fab.innerHTML = `
    <div style="
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 999999;
      background: linear-gradient(135deg, #2563eb, #1d4ed8);
      color: white;
      padding: 10px 16px;
      border-radius: 9999px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 13px;
      font-weight: 600;
      box-shadow: 0 10px 25px rgba(37, 99, 235, 0.4);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: all 0.2s ease;
    ">
      <span>⚡ AI Autofill Application</span>
    </div>
  `;

  fab.addEventListener("click", async () => {
    const textEl = fab.querySelector("span");
    const orig = textEl.textContent;
    textEl.textContent = "⏳ Filling Form & AI Answers...";
    try {
      const count = await autofillForm();
      textEl.textContent = `✅ Filled ${count} Fields!`;
      setTimeout(() => { textEl.textContent = orig; }, 3000);
    } catch (e) {
      textEl.textContent = "❌ Autofill Error";
      setTimeout(() => { textEl.textContent = orig; }, 3000);
    }
  });

  document.body.appendChild(fab);
}

// Listen for popup messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "AUTOFILL_APPLICATION") {
    autofillForm().then(count => {
      sendResponse({ success: true, fieldsFilled: count });
    });
    return true; // Keep sendResponse open for async
  }
});

// Auto-inject floating assistant on supported ATS pages
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", injectFloatingButton);
} else {
  injectFloatingButton();
}
