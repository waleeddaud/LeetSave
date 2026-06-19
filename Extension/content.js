(() => {
  const ACCEPTED_MARKERS = ["Accepted", "accepted"];
  const seenAcceptances = new Set();
  let observer = null;

  function getProblemSlug() {
    const match = window.location.pathname.match(/\/problems\/([^/]+)/);
    return match ? match[1] : "";
  }

  function getProblemTitle() {
    const titleEl =
      document.querySelector("[data-cy='question-title']") ||
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

    const text = document.body.innerText;
    if (/\bEasy\b/.test(text)) return "Easy";
    if (/\bMedium\b/.test(text)) return "Medium";
    if (/\bHard\b/.test(text)) return "Hard";
    return null;
  }

  function getLanguage() {
    const langButton =
      document.querySelector("[data-cy='lang-select']") ||
      document.querySelector("button[id*='headlessui'] .text-label-1") ||
      document.querySelector(".ant-select-selection-item");
    const text = langButton?.textContent?.trim();
    if (text) return text.toLowerCase();

    const stored = localStorage.getItem("LEETCODE_LANGUAGE");
    return stored || "python";
  }

  function getEditorCode() {
    try {
      if (window.monaco?.editor) {
        const models = window.monaco.editor.getModels();
        if (models?.length) {
          return models[0].getValue();
        }
      }
    } catch (_err) {
      // ignore editor access errors
    }

    const textarea =
      document.querySelector("textarea[data-cy='code-area']") ||
      document.querySelector(".monaco-scrollable-element textarea");
    return textarea?.value || "";
  }

  function nodeLooksLikeAcceptedResult(node) {
    if (!(node instanceof HTMLElement)) return false;
    const text = node.textContent || "";
    if (!ACCEPTED_MARKERS.some((marker) => text.includes(marker))) return false;

    const className = node.className?.toString?.() || "";
    const likelyResultPanel =
      className.includes("result") ||
      className.includes("submit") ||
      node.closest("[data-e2e-locator*='submission']") ||
      node.closest("[class*='result']") ||
      node.closest("[class*='status']");

    return Boolean(likelyResultPanel || text.length < 200);
  }

  function buildPayload() {
    const slug = getProblemSlug();
    const code = getEditorCode();
    if (!slug || !code.trim()) return null;

    return {
      problem_slug: slug,
      problem_title: getProblemTitle(),
      difficulty: getDifficulty(),
      language: getLanguage(),
      code,
      status: "Accepted",
      leetcode_url: window.location.href.split("?")[0],
      timestamp: new Date().toISOString(),
    };
  }

  function notifyAccepted() {
    const payload = buildPayload();
    if (!payload) return;

    const key = `${payload.problem_slug}:${payload.language}:${payload.code}`;
    if (seenAcceptances.has(key)) return;
    seenAcceptances.add(key);

    chrome.runtime.sendMessage({ type: "SYNC_SUBMISSION", payload }, (response) => {
      if (chrome.runtime.lastError) {
        console.warn("LeetSave:", chrome.runtime.lastError.message);
        return;
      }
      console.log("LeetSave sync:", response);
    });
  }

  function scanForAccepted(node) {
    if (nodeLooksLikeAcceptedResult(node)) {
      notifyAccepted();
      return;
    }

    if (node instanceof HTMLElement) {
      const candidates = node.querySelectorAll("div, span, p, td");
      for (const candidate of candidates) {
        if (nodeLooksLikeAcceptedResult(candidate)) {
          notifyAccepted();
          break;
        }
      }
    }
  }

  function startObserver() {
    if (observer) return;
    observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        mutation.addedNodes.forEach((node) => scanForAccepted(node));
        if (mutation.target) scanForAccepted(mutation.target);
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startObserver);
  } else {
    startObserver();
  }
})();
