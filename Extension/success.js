// success.js
const token = window.location.hash.split("=")[1];
if (token) {
  chrome.storage.local.set({ github_token: token }, () => {
    console.log("GitHub token saved!");
  });
}
