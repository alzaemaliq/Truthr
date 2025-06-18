document.addEventListener("DOMContentLoaded", () => {
  chrome.runtime.sendMessage({ type: "GET_VIDEO_DATA" }, (response) => {
    const box = document.getElementById("claims-output");

    if (!response) {
      box.innerText = "No data available yet.";
      return;
    }

    if (response.error) {
      box.innerText = response.error;
      return;
    }

    const blocks = response.result_blocks || [];
    box.innerText = blocks.join("\n\n") || "No claims checked.";
  });
});
