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

// === RECEIVE VIDEO ID FROM CONTENT SCRIPT AND FORWARD TO BACKEND ===
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
    .then(res => res.text())
    .then(data => console.log("Backend response:", data))
    .catch(err => console.error("Backend error:", err));
  }
});
