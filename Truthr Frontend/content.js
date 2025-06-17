let lastVideoId = null;

function getYouTubeVideoId() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get("v");
}

function checkForVideoChange() {
  const currentVideoId = getYouTubeVideoId();
  if (currentVideoId && currentVideoId !== lastVideoId) {
    lastVideoId = currentVideoId;
    console.log("Sending video ID to background:", currentVideoId);
    chrome.runtime.sendMessage({ type: "VIDEO_ID", videoId: currentVideoId });
  }
}

// Initial check and then poll every second (SPA-safe)
checkForVideoChange();
setInterval(checkForVideoChange, 1000);
