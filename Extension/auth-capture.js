(() => {
  const params = new URLSearchParams(window.location.search);
  const token = params.get("leetsave_token");

  if (!token) {
    console.warn("LeetSave auth-capture: no leetsave_token in URL");
    return;
  }

  chrome.runtime.sendMessage({ type: "SAVE_BACKEND_TOKEN", token }, (response) => {
    if (chrome.runtime.lastError) {
      console.warn("LeetSave auth-capture:", chrome.runtime.lastError.message);
      return;
    }
    console.log("LeetSave auth-capture: token saved", response);
  });
})();
