document.addEventListener("DOMContentLoaded", () => {
  const autofillBtn = document.getElementById("autofill-btn");
  const dashboardBtn = document.getElementById("dashboard-btn");
  const statusText = document.getElementById("status-text");
  const authAlert = document.getElementById("auth-alert");
  const candName = document.getElementById("cand-name");
  const candEmail = document.getElementById("cand-email");
  const candResume = document.getElementById("cand-resume");

  let isAuthenticated = false;

  // Fetch active candidate data from local AI Job Agent if online
  fetch("http://127.0.0.1:5000/api/v1/extension/profile", {
    credentials: "include"
  })
    .then(r => {
      if (r.status === 401) {
        throw new Error("UNAUTHORIZED");
      }
      return r.json();
    })
    .then(data => {
      if (data && data.success && data.candidate) {
        isAuthenticated = true;
        candName.textContent = data.candidate.fullName || "Candidate";
        candEmail.textContent = data.candidate.email || "--";
        candResume.textContent = data.candidate.activeResumeTitle || "Active Resume";
        if (authAlert) authAlert.style.display = "none";
        autofillBtn.disabled = false;
        statusText.textContent = "Authenticated. Ready to autofill.";
      } else {
        throw new Error("NO_PROFILE");
      }
    })
    .catch(err => {
      isAuthenticated = false;
      candName.textContent = "Sign In Required";
      candEmail.textContent = "Not Authenticated";
      candResume.textContent = "None";
      if (authAlert) authAlert.style.display = "block";
      autofillBtn.disabled = true;
      dashboardBtn.textContent = "Log In to AI Job Agent";
      statusText.textContent = "Please log in at http://127.0.0.1:5000 to autofill.";
    });

  dashboardBtn.addEventListener("click", () => {
    const targetUrl = isAuthenticated ? "http://127.0.0.1:5000/dashboard" : "http://127.0.0.1:5000/login";
    chrome.tabs.create({ url: targetUrl });
  });

  autofillBtn.addEventListener("click", () => {
    if (!isAuthenticated) {
      statusText.textContent = "Please sign in first.";
      return;
    }
    statusText.textContent = "Auto-filling application fields...";
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs || !tabs[0]) return;
      chrome.tabs.sendMessage(tabs[0].id, { action: "AUTOFILL_APPLICATION" }, (resp) => {
        if (chrome.runtime.lastError) {
          statusText.textContent = "Open a supported application form (Greenhouse, Lever, etc.)";
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
