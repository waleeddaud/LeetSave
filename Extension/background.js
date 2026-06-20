import { BACKEND_BASE_URL } from "./config.js";

console.log("LeetSave service worker started");

const SYNC_DEDUP_KEY = "synced_hashes";
const LAST_STATUS_KEY = "last_sync_status";
const AUTH_SUCCESS_PREFIX = `${BACKEND_BASE_URL}/onboarding/success`;
const LEETCODE_PROBLEM_RE = /^https:\/\/([^/]+\.)?leetcode\.com\/problems\//;

const injectedHookTabs = new Set();
let lastSavedToken = null;

function extractTokenFromUrl(url) {
  try {
    const parsed = new URL(url);
    const queryToken = parsed.searchParams.get("leetsave_token");
    if (queryToken) return decodeURIComponent(queryToken);

    const hash = parsed.hash || "";
    if (hash.startsWith("#token=")) {
      return decodeURIComponent(hash.slice("#token=".length));
    }
  } catch (_error) {
    // ignore
  }
  return null;
}

async function saveBackendToken(token) {
  await chrome.storage.local.set({ backend_token: token });
  await setLastStatus({ status: "logged_in", message: "GitHub connected successfully" });
  lastSavedToken = token;
  console.log("LeetSave: backend_token saved to chrome.storage.local");
}

async function persistBackendToken(token, source, tabId = null) {
  if (!token) return false;
  if (token === lastSavedToken) {
    console.log("LeetSave: token already saved (%s)", source);
    return true;
  }

  await saveBackendToken(token);
  await chrome.action.setBadgeText({ text: "OK" });
  await chrome.action.setBadgeBackgroundColor({ color: "#22863a" });
  console.log("LeetSave: login token captured via %s", source);

  setTimeout(async () => {
    await chrome.action.setBadgeText({ text: "" });
    if (tabId != null) {
      try {
        await chrome.tabs.remove(tabId);
      } catch (_error) {
        // tab may already be closed
      }
    }
  }, 4000);

  return true;
}

async function injectPageHook(tabId, url = "") {
  if (!url) {
    try {
      const tab = await chrome.tabs.get(tabId);
      url = tab.url || "";
    } catch (_error) {
      return;
    }
  }
  if (!LEETCODE_PROBLEM_RE.test(url)) return;
  if (injectedHookTabs.has(tabId)) return;

  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["page-hook.js"],
      world: "MAIN",
    });
    injectedHookTabs.add(tabId);
    console.log("LeetSave: page hook injected into tab", tabId);
  } catch (error) {
    console.warn("LeetSave: could not inject page hook", error?.message || error);
  }
}

async function captureAuthFromTab(tabId, url) {
  if (!url || !url.startsWith(AUTH_SUCCESS_PREFIX)) return;

  let token = extractTokenFromUrl(url);

  if (!token) {
    try {
      const [result] = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => new URLSearchParams(window.location.search).get("leetsave_token"),
      });
      token = result?.result || null;
    } catch (error) {
      console.warn("LeetSave: could not read token from success tab", error?.message || error);
    }
  }

  await persistBackendToken(token, "tab-listener", tabId);
}

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  const url = tab.url || changeInfo.url || "";

  if (changeInfo.status === "complete") {
    injectPageHook(tabId, url);
    captureAuthFromTab(tabId, url);
  }

  if (changeInfo.url) {
    captureAuthFromTab(tabId, changeInfo.url);
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  injectedHookTabs.delete(tabId);
});

chrome.webNavigation.onHistoryStateUpdated.addListener((details) => {
  if (details.frameId !== 0) return;
  injectPageHook(details.tabId, details.url);
});

async function getBackendToken() {
  const data = await chrome.storage.local.get(["backend_token"]);
  return data.backend_token || null;
}

async function saveSyncHash(hash) {
  const data = await chrome.storage.local.get([SYNC_DEDUP_KEY]);
  const hashes = new Set(data[SYNC_DEDUP_KEY] || []);
  hashes.add(hash);
  await chrome.storage.local.set({ [SYNC_DEDUP_KEY]: [...hashes] });
}

async function hasSyncHash(hash) {
  const data = await chrome.storage.local.get([SYNC_DEDUP_KEY]);
  const hashes = data[SYNC_DEDUP_KEY] || [];
  return hashes.includes(hash);
}

async function setLastStatus(status) {
  await chrome.storage.local.set({ [LAST_STATUS_KEY]: { ...status, at: Date.now() } });
}

export async function loginWithGitHub() {
  lastSavedToken = null;
  await chrome.storage.local.remove(["backend_token", SYNC_DEDUP_KEY, LAST_STATUS_KEY]);
  await chrome.tabs.create({
    url: `${BACKEND_BASE_URL}/api/v1/auth/github/login`,
    active: true,
  });
}

export async function fetchMe() {
  const token = await getBackendToken();
  if (!token) {
    console.warn("LeetSave: fetchMe called with no backend_token in storage");
    return null;
  }

  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    if (response.status === 401) {
      await chrome.storage.local.remove(["backend_token"]);
      lastSavedToken = null;
    }
    console.warn("LeetSave: fetchMe failed", response.status);
    return null;
  }

  return response.json();
}

export async function logout() {
  const token = await getBackendToken();
  if (token) {
    try {
      await fetch(`${BACKEND_BASE_URL}/api/v1/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch (error) {
      console.warn("LeetSave logout request failed:", error);
    }
  }
  await chrome.storage.local.remove(["backend_token", SYNC_DEDUP_KEY, LAST_STATUS_KEY]);
  lastSavedToken = null;
  await chrome.action.setBadgeText({ text: "" });
  console.log("LeetSave: logged out");
  return { ok: true };
}

async function syncSubmission(payload) {
  const token = await getBackendToken();
  if (!token) {
    console.warn("LeetSave: sync blocked — no backend_token in chrome.storage.local");
    await setLastStatus({ status: "login_required", message: "Login required" });
    return { status: "login_required", message: "Login required" };
  }

  const dedupKey = `${payload.problem_slug}:${payload.language}:${payload.code.length}`;
  if (await hasSyncHash(dedupKey)) {
    const result = { status: "already_synced", message: "Already synced locally" };
    await setLastStatus(result);
    return result;
  }

  try {
    console.log("LeetSave: syncing submission to backend", payload.problem_slug);
    const response = await fetch(`${BACKEND_BASE_URL}/api/v1/submissions/leetcode`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok) {
      const failed = { status: "failed", message: result.detail || "Sync failed" };
      await setLastStatus(failed);
      console.warn("LeetSave sync failed:", failed);
      return failed;
    }

    if (result.status === "synced" || result.status === "already_synced") {
      await saveSyncHash(dedupKey);
    }

    await setLastStatus(result);
    console.log("LeetSave sync result:", result);
    return result;
  } catch (error) {
    const failed = { status: "failed", message: "Backend unavailable" };
    await setLastStatus(failed);
    console.error("LeetSave sync error:", error);
    return failed;
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "SYNC_SUBMISSION") {
    syncSubmission(message.payload).then(sendResponse);
    return true;
  }
  if (message.type === "GET_AUTH_STATUS") {
    fetchMe().then((user) => sendResponse({ user })).catch(() => sendResponse({ user: null }));
    return true;
  }
  if (message.type === "LOGIN") {
    loginWithGitHub().then(() => sendResponse({ ok: true }));
    return true;
  }
  if (message.type === "LOGOUT") {
    logout().then(() => sendResponse({ ok: true }));
    return true;
  }
  if (message.type === "SAVE_BACKEND_TOKEN") {
    persistBackendToken(message.token, "auth-capture-script", sender.tab?.id)
      .then((ok) => sendResponse({ ok }))
      .catch(() => sendResponse({ ok: false }));
    return true;
  }
  if (message.type === "INSTALL_PAGE_HOOK" && sender.tab?.id) {
    injectPageHook(sender.tab.id, sender.tab.url).then(() => sendResponse({ ok: true }));
    return true;
  }
  return false;
});

chrome.tabs.query({ url: ["https://leetcode.com/problems/*", "https://www.leetcode.com/problems/*"] }, (tabs) => {
  for (const tab of tabs) {
    if (tab.id && tab.url) {
      injectPageHook(tab.id, tab.url);
    }
  }
});
