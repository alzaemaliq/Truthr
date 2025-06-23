document.addEventListener("DOMContentLoaded", () => {
  const analyzeBtn = document.getElementById("analyze-btn");

  analyzeBtn.addEventListener("click", () => {
    console.log("Analyze button was clicked");

    // 🔁 Send message to content.js in the active tab
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      chrome.tabs.sendMessage(tabs[0].id, { type: "REQUEST_VIDEO_ID" });
    });
  });

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "ANALYSIS_RESULT") {
      console.log("Received analysis result:", message.data);

      const output = document.getElementById("claims-output");

      if (output) {
        if (message.data.error) {
          output.innerHTML = `<div class="error-msg">Error: ${message.data.error}</div>`;
        } else if (Array.isArray(message.data.claims)) {
          output.innerHTML = message.data.claims.map((item, index) => {
            return `
              <div class="claim-card">
                <p><strong>${index + 1}. Claim:</strong> ${item.Claim}</p>
                <p><strong>Status:</strong> <span class="status ${item.Status.toLowerCase()}">${item.Status}</span></p>
                <p><strong>Correction:</strong> ${item.Correction || "N/A"}</p>
              </div>
            `;
          }).join("");
        } else {
          output.innerHTML = `<div class="error-msg">Unexpected response format.</div>`;
        }
      }
    }
  });
});
