// === ENABLE SIDE PANEL BEHAVIOR ON EXTENSION INSTALL ===
chrome.runtime.onInstalled.addListener(() => {
  chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
});

// === ENABLE SIDE PANEL ON YOUTUBE WATCH PAGES ===
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
  }
});

// === HANDLE VIDEO_ID MESSAGES FROM CONTENT SCRIPT ===
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "VIDEO_ID" && message.videoId) {
    console.log("Video ID received:", message.videoId);

    fetch(`https://7k5oajwcvkzcol-8000.proxy.runpod.net/analyze/${message.videoId}`)
      .then(res => res.json())
      .then(data => {
        console.log("Backend response:", data);
        // Optionally store this data for the side panel
      })
      .catch(err => {
        console.error("Backend error:", err);
      });
  }

  return true;
});
