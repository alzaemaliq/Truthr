document.addEventListener("DOMContentLoaded", () => {
  const analyzeBtn = document.getElementById("analyze-btn");

  analyzeBtn.addEventListener("click", () => {
    console.log("Analyze button was clicked");

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tabId = tabs[0].id;

      // ⏱ Inject content.js before sending message
      chrome.scripting.executeScript({
        target: { tabId },
        files: ["content.js"]
      }, () => {
        console.log("content.js injected");

        // ✅ Now safely send message
        chrome.tabs.sendMessage(tabId, { type: "REQUEST_VIDEO_ID" });
      });
    });
  });

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "ANALYSIS_RESULT") {
      console.log("Received analysis result:", message.data);

      const output = document.getElementById("claims-output");

      if (output) {
        if (message.data.error) {
          output.innerHTML = `<div class="error-msg">Error: ${message.data.error}</div>`;
        } else if (Array.isArray(message.data.response)) {
          output.innerHTML = message.data.response.map((item, index) => {
            const claim = item.claim || item.Claim || "N/A";
            const status = item.status || item.Status || "Unknown";
            const correction = item.correction || item.Correction || "N/A";
            return `
            <div class="claim-card">
              <p><strong>Claim:</strong> ${claim}</p>
              <p><strong>Status:</strong> <span class="status ${status.toLowerCase()}">${status}</span></p>
              <p><strong>Correction:</strong> ${correction}</p>
            </div>
            `;
          }).join("");
        }
      } else {
        output.innerHTML = `<div class="error-msg">Unexpected response format.</div>`;
      }
    }
  });
});
