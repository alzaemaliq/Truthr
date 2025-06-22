document.addEventListener("DOMContentLoaded", () => {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "ANALYSIS_RESULT") {
      console.log("Received analysis result:", message.data);
    }
  });
});
