chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "VIDEO_ID" && message.videoId) {
    console.log("Video ID received:", message.videoId);

    // Send simplified POST to avoid CORS preflight issues
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
