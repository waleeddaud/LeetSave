const hash = window.location.hash || "";
const token = hash.startsWith("#token=") ? hash.slice("#token=".length) : null;

if (token) {
  chrome.storage.local.set({ backend_token: decodeURIComponent(token) }, () => {
    console.log("LeetSave backend session saved");
  });
} else {
  console.warn("LeetSave: no backend token found in redirect URL");
}
