if (!window.__contentScriptInitialized) {
  window.__contentScriptInitialized = true;

  console.log("Content script loaded");

  function getYouTubeVideoId() {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get("v");
  }

  // ✅ Listen for button-triggered request from sidepanel.js
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === "REQUEST_VIDEO_ID") {
      const videoId = getYouTubeVideoId();
      if (videoId) {
        console.log("Received REQUEST_VIDEO_ID, sending:", videoId);
        chrome.runtime.sendMessage({ type: "VIDEO_ID", videoId });
      } else {
        console.warn("No video ID found in URL.");
      }
    }
  });
}
