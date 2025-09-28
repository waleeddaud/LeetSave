function loginWithGitHub() {
  fetch("http://localhost:8000/login", { method: "POST", credentials: "include" })
    .then((res) => res.json())  // convert response to JSON
    .then((data) => {
      console.log("Received data:", data);
      chrome.tabs.create({ url: data.url }); // now data.url exists
    })
    .catch((err) => console.error("Fetch error:", err));
}

// Example trigger: right-click menu or first push attempt
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "github-login",
    title: "Login with GitHub",
    contexts: ["all"],
  });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === "github-login") {
    loginWithGitHub();
  }
});


// Track submissions we've already processed
let processedSubmissions = new Set();

// Capture submit payload
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    if (details.url.includes("/submit/")) {
      let payload = details.requestBody?.raw?.[0]?.bytes;
      if (payload) {
        let text = new TextDecoder("utf-8").decode(payload);
        console.log("Submit Payload:", text);
        // TODO: Forward to backend if needed
      }
    }
  },
  { urls: ["*://leetcode.com/problems/*/submit/"] },
  ["requestBody"]
);

// Function to poll until submission gets final verdict
function pollSubmissionResult(url, submissionId, maxRetries = 5, interval = 2000) {
  let tries = 0;

  function check() {
    fetch(url, { credentials: "include" })
      .then((res) => res.json())
      .then((data) => {
        console.log("Check Response:", data);

        if (data.state === "PENDING" || data.state === "STARTED") {
          if (tries < maxRetries) {
            tries++;
            setTimeout(check, interval); // retry
          } else {
            console.warn("Submission", submissionId, "timed out without final result.");
          }
        } else {
          // Got a final result
          if (data.status_msg === "Accepted") {
            console.log(" Submission", submissionId, "was Accepted!");
            // TODO: send code + metadata to backend
          } else {
            console.log(" Submission", submissionId, "result:", data.status_msg);
          }
        }
      })
      .catch((err) => console.error("Fetch failed:", err));
  }

  check();
}

// Capture check results, but only ONCE per submission
chrome.webRequest.onCompleted.addListener(
  (details) => {
    if (details.url.includes("/check/")) {
      // Extract submission ID from URL
      let match = details.url.match(/submissions\/detail\/(\d+)\/check/);
      if (!match) return;

      let submissionId = match[1];
      if (processedSubmissions.has(submissionId)) return; // Skip duplicates
      processedSubmissions.add(submissionId);

      console.log("Submission checked:", submissionId, details.url);

      // Poll until we get a final Accepted/Rejected/etc.
      pollSubmissionResult(details.url, submissionId);
    }
  },
  { urls: ["*://leetcode.com/submissions/detail/*/check/"] }
);
