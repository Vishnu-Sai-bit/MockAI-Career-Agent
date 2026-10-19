// Content script for detecting and auto-filling applicant fields
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "AUTOFILL_APPLICATION") {
    const candidate = {
      firstName: "Vishnu Sai",
      lastName: "Beere",
      fullName: "Beere Vishnu Sai",
      email: "beerevishnusai776600@gmail.com",
      phone: "+91-9876543210",
      location: "Bengaluru, India",
      linkedin: "https://www.linkedin.com/in/vishnusai",
      github: "https://github.com/vishnusai",
      headline: "Data Science & AI Engineer"
    };

    let filledCount = 0;

    const fillInput = (selectorList, value) => {
      for (const sel of selectorList) {
        const el = document.querySelector(sel);
        if (el && !el.value) {
          el.value = value;
          el.dispatchEvent(new Event("input", { bubbles: true }));
          el.dispatchEvent(new Event("change", { bubbles: true }));
          filledCount++;
          return true;
        }
      }
      return false;
    };

    // First name
    fillInput([
      "input#first_name", "input[name='first_name']", "input[name='firstName']",
      "input[id*='first-name']", "input[id*='firstName']", "input[name*='first_name']"
    ], candidate.firstName);

    // Last name
    fillInput([
      "input#last_name", "input[name='last_name']", "input[name='lastName']",
      "input[id*='last-name']", "input[id*='lastName']", "input[name*='last_name']"
    ], candidate.lastName);

    // Full name
    fillInput([
      "input#name", "input[name='name']", "input[name='fullName']",
      "input[id*='name']"
    ], candidate.fullName);

    // Email
    fillInput([
      "input#email", "input[name='email']", "input[type='email']",
      "input[id*='email']", "input[name*='email']"
    ], candidate.email);

    // Phone
    fillInput([
      "input#phone", "input[name='phone']", "input[type='tel']",
      "input[id*='phone']", "input[name*='phone']"
    ], candidate.phone);

    // LinkedIn
    fillInput([
      "input[name*='linkedin']", "input[id*='linkedin']", "input[placeholder*='linkedin']"
    ], candidate.linkedin);

    // GitHub / Website
    fillInput([
      "input[name*='github']", "input[id*='github']", "input[name*='website']", "input[id*='website']"
    ], candidate.github);

    // Location
    fillInput([
      "input#location", "input[name='location']", "input[id*='location']"
    ], candidate.location);

    sendResponse({ success: true, fieldsFilled: filledCount });
  }
  return true;
});
