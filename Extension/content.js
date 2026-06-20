console.log("LeetSave content script loaded on", window.location.href);

if (!window.__leetsaveLoaded) {
  window.__leetsaveLoaded = true;

(() => {
  const seenSubmissions = new Set();

  function getProblemSlug() {
    const match = window.location.pathname.match(/\/problems\/([^/]+)/);
    return match ? match[1] : "";
  }

  function getProblemTitle() {
    const titleEl =
      document.querySelector("[data-cy='question-title']") ||
      document.querySelector("a[href*='/problems/']") ||
      document.querySelector("div[class*='question-title']") ||
      document.querySelector("h1") ||
      document.querySelector("h2");
    return titleEl?.textContent?.trim() || getProblemSlug();
  }

  function getDifficulty() {
    const easy = document.querySelector("[diff='Easy'], .text-difficulty-easy, .text-green-s");
    if (easy) return "Easy";
    const medium = document.querySelector("[diff='Medium'], .text-difficulty-medium, .text-yellow-s");
    if (medium) return "Medium";
    const hard = document.querySelector("[diff='Hard'], .text-difficulty-hard, .text-red-s");
    if (hard) return "Hard";
    return null;
  }

  function getCodeFromMonacoDom() {
    const viewLines = document.querySelectorAll(".monaco-editor .view-lines .view-line");
    if (!viewLines.length) return "";
    return Array.from(viewLines)
      .map((line) => line.textContent || "")
      .join("\n");
  }

  function getLanguage() {
    const langSelectors = [
      "[data-cy='lang-select']",
      "button[id*='headlessui'] .text-label-1",
      "[class*='lang-select']",
      ".ant-select-selection-item",
    ];

    for (const selector of langSelectors) {
      const el = document.querySelector(selector);
      const text = el?.textContent?.trim();
      if (text) return text.toLowerCase();
    }

    return "python";
  }

  function getEditorContext() {
    return {
      code: getCodeFromMonacoDom(),
      language: getLanguage(),
    };
  }

  async function buildPayload() {
    const slug = getProblemSlug();
    if (!slug) return null;

    const { code, language } = getEditorContext();
    if (!code.trim()) return null;

    return {
      problem_slug: slug,
      problem_title: getProblemTitle(),
      difficulty: getDifficulty(),
      language,
      code,
      status: "Accepted",
      leetcode_url: window.location.href.split("?")[0],
      timestamp: new Date().toISOString(),
    };
  }

  async function triggerSync(source) {
    const payload = await buildPayload();
    if (!payload) {
      console.warn("LeetSave: submit detected but code/metadata unavailable", source);
      return;
    }

    const key = `${payload.problem_slug}:${payload.language}:${payload.code}`;
    if (seenSubmissions.has(key)) return;
    seenSubmissions.add(key);

    console.log("LeetSave: triggering sync on submit", source);

    chrome.runtime.sendMessage({ type: "SYNC_SUBMISSION", payload }, (response) => {
      if (chrome.runtime.lastError) {
        console.warn("LeetSave:", chrome.runtime.lastError.message);
        return;
      }
      console.log("LeetSave sync:", response);
    });
  }

  function handleSubmitSignal(source) {
    triggerSync(source).catch((error) => {
      console.error("LeetSave sync failed:", error);
    });
  }

  function isSubmitButton(element) {
    if (!(element instanceof HTMLElement)) return false;

    const selectors = [
      "[data-cy='submit-code-btn']",
      "button[data-e2e-locator='console-submit-button']",
      "button#submit-code-btn",
    ];

    if (selectors.some((selector) => element.matches(selector) || element.closest(selector))) {
      return true;
    }

    const text = (element.textContent || "").trim().toLowerCase();
    return text === "submit" || text === "submit code";
  }

  function installSubmitListeners() {
    document.addEventListener(
      "click",
      (event) => {
        if (!isSubmitButton(event.target)) return;
        handleSubmitSignal("submit-click");
      },
      true
    );

    document.addEventListener(
      "keydown",
      (event) => {
        const isSubmitShortcut =
          (event.ctrlKey || event.metaKey) && event.key === "Enter" ||
          (event.ctrlKey || event.metaKey) && event.key === "'";
        if (!isSubmitShortcut) return;
        handleSubmitSignal("submit-shortcut");
      },
      true
    );
  }

  window.addEventListener("message", (event) => {
    if (event.source !== window || event.data?.type !== "LEETSAVE_SUBMIT") return;
    handleSubmitSignal(event.data.source || "message");
  });

  function init() {
    installSubmitListeners();
    chrome.runtime.sendMessage({ type: "INSTALL_PAGE_HOOK" });
    console.log("LeetSave: listening for submits on", window.location.pathname);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();

} else {
  console.log("LeetSave content script already active, skipping duplicate init");
}
