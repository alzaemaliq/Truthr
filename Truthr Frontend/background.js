// === ENABLE SIDE PANEL BEHAVIOR ON EXTENSION INSTALL ===
chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

// === LISTEN FOR YOUTUBE VIDEO PAGE LOADS ===
chrome.tabs.onUpdated.addListener(async (tabId, info, tab) => {
  if (info.status !== 'complete' || !tab.url) return;

  const url = new URL(tab.url);
  const YOUTUBE_ORIGIN = 'https://www.youtube.com';

  if (url.origin === YOUTUBE_ORIGIN && url.pathname.startsWith('/watch')) {
    await chrome.sidePanel.setOptions({
      tabId,
      path: 'sidepanel.html',
      enabled: true
    });
  } else {
    await chrome.sidePanel.setOptions({
      tabId,
      enabled: false
    });
  }
});

// === STORE LAST FETCHED BACKEND DATA ===
let lastVideoData = null;

// === HANDLE MESSAGES FROM CONTENT SCRIPT AND SIDEPANEL ===
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "VIDEO_ID" && message.videoId) {
    console.log("Video ID received:", message.videoId);

    fetch("https://zqlunrjxpapstu-8000.proxy.runpod.net/video", {
      method: "POST",
      headers: {
        "Content-Type": "text/plain"
      },
      body: `videoId=${message.videoId}`
    })
    .then(res => res.json())
    .then(data => {
      console.log("Backend response:", data);
      lastVideoData = data;
    })
    .catch(err => {
      console.error("Backend error:", err);
      lastVideoData = { error: "Failed to fetch backend data." };
    });
  }

  if (message.type === "GET_VIDEO_DATA") {
    sendResponse(lastVideoData);
  }

  return true; // Required for asynchronous sendResponse
});
