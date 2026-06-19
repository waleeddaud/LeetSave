import { BACKEND_BASE_URL } from "./config.js";

const SYNC_DEDUP_KEY = "synced_hashes";
const LAST_STATUS_KEY = "last_sync_status";

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
  await chrome.tabs.create({ url: `${BACKEND_BASE_URL}/api/v1/auth/github/login` });
}

export async function fetchMe() {
  const token = await getBackendToken();
  if (!token) return null;

  const response = await fetch(`${BACKEND_BASE_URL}/api/v1/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    if (response.status === 401) {
      await chrome.storage.local.remove(["backend_token"]);
    }
    return null;
  }

  return response.json();
}

export async function logout() {
  const token = await getBackendToken();
  if (token) {
    await fetch(`${BACKEND_BASE_URL}/api/v1/auth/logout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
  }
  await chrome.storage.local.remove(["backend_token", SYNC_DEDUP_KEY, LAST_STATUS_KEY]);
}

async function syncSubmission(payload) {
  const token = await getBackendToken();
  if (!token) {
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
      return failed;
    }

    if (result.status === "synced" || result.status === "already_synced") {
      await saveSyncHash(dedupKey);
    }

    await setLastStatus(result);
    return result;
  } catch (error) {
    const failed = { status: "failed", message: "Backend unavailable" };
    await setLastStatus(failed);
    return failed;
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
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
  return false;
});
