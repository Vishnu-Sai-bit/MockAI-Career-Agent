document.addEventListener("DOMContentLoaded", () => {
  const autofillBtn = document.getElementById("autofill-btn");
  const dashboardBtn = document.getElementById("dashboard-btn");
  const statusText = document.getElementById("status-text");

  // Fetch active candidate data from local AI Job Agent if online
  fetch("http://127.0.0.1:5000/api/candidate-profile")
    .then(r => r.json())
    .then(data => {
      if (data && data.full_name) {
        document.getElementById("cand-name").textContent = data.full_name;
        document.getElementById("cand-email").textContent = data.email || "beerevishnusai...";
      }
    })
    .catch(() => {
      // Default offline profile
    });

  dashboardBtn.addEventListener("click", () => {
    chrome.tabs.create({ url: "http://127.0.0.1:5000/dashboard" });
  });

  autofillBtn.addEventListener("click", () => {
    statusText.textContent = "Auto-filling application fields...";
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs[0]) return;
      chrome.tabs.sendMessage(tabs[0].id, { action: "AUTOFILL_APPLICATION" }, (resp) => {
        if (chrome.runtime.lastError) {
          statusText.textContent = "Please open a supported application form (Greenhouse, Lever, etc.)";
        } else if (resp && resp.success) {
          statusText.textContent = `Auto-filled ${resp.fieldsFilled} form fields!`;
          statusText.style.color = "#16a34a";
        } else {
          statusText.textContent = "No standard application inputs detected on this page.";
        }
      });
    });
  });
});
