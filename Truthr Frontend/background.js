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

// === CACHED BACKEND RESPONSES ===
const videoCache = {}; // { [videoId]: backendResponse }

// === HELPER: Validate if backend response is correct ===
function isValidResponse(data) {
  return data && !data.error && Array.isArray(data.response);
}

// === HELPER: Retry fetch with max attempts ===
async function fetchWithRetry(videoId, attempts = 3) {
  const url = `https://7k5oajwcvkzcol-8000.proxy.runpod.net/analyze/${videoId}`;

  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(url);
      const data = await res.json();

      if (isValidResponse(data)) {
        console.log(`Valid backend response received for ${videoId}:`, data);
        chrome.storage.local.set({ [videoId]: data }); // Persist to storage
        chrome.runtime.sendMessage({ type: "ANALYSIS_RESULT", data });
        return;
      } else {
        console.warn(`Invalid response attempt ${i + 1} for ${videoId}`, data);
      }
    } catch (err) {
      console.error(`Fetch error attempt ${i + 1} for ${videoId}:`, err);
    }
  }

  // If all retries fail
  chrome.runtime.sendMessage({
    type: "ANALYSIS_RESULT",
    data: { error: "Failed to fetch valid analysis after 3 attempts." }
  });
}

// === HANDLE VIDEO_ID MESSAGES FROM CONTENT SCRIPT ===
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "VIDEO_ID" && message.videoId) {
    const videoId = message.videoId;

    console.log("Video ID received:", videoId);

    chrome.storage.local.get(videoId, (result) => {
      if (result[videoId]) {
        console.log("Using cached response from storage for", videoId);
        chrome.runtime.sendMessage({ type: "ANALYSIS_RESULT", data: result[videoId] });
      } else {
        fetchWithRetry(videoId);
      }
    });
  }

  return true;
});
