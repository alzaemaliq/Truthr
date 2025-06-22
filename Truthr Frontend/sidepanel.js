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
    }
  });
});
