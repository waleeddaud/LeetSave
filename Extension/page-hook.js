if (!window.__leetsaveSubmitHooked) {
  window.__leetsaveSubmitHooked = true;

  const originalFetch = window.fetch.bind(window);
  window.fetch = async (...args) => {
    const response = await originalFetch(...args);
    try {
      const rawUrl = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
      if (rawUrl.includes("/submit")) {
        window.postMessage({ type: "LEETSAVE_SUBMIT", source: "fetch" }, "*");
      }
    } catch (_err) {
      // ignore observer errors
    }
    return response;
  };
}
