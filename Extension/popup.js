function setStatus(text) {
  const statusEl = document.getElementById("status");
  statusEl.textContent = text;
  statusEl.classList.remove("hidden");
}

function clearStatus() {
  const statusEl = document.getElementById("status");
  statusEl.textContent = "";
  statusEl.classList.add("hidden");
}

function showLoggedIn(user) {
  document.getElementById("logged-out").classList.add("hidden");
  document.getElementById("logged-in").classList.remove("hidden");
  document.getElementById("username").textContent = user.github_username || "GitHub user";
  document.getElementById("avatar").src = user.avatar_url || "";
  document.getElementById("repo").textContent = user.repo_full_name
    ? `Repo: ${user.repo_full_name}`
    : "Repo will be created on first sync";
}

function showLoggedOut() {
  document.getElementById("logged-in").classList.add("hidden");
  document.getElementById("logged-out").classList.remove("hidden");
  document.getElementById("logout-stale-btn").classList.add("hidden");
}

function showStaleSession() {
  document.getElementById("logged-in").classList.add("hidden");
  document.getElementById("logged-out").classList.remove("hidden");
  document.getElementById("logout-stale-btn").classList.remove("hidden");
  setStatus("Session saved but not verified. Logout and sign in again if needed.");
}

function hasStoredToken() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["backend_token"], (data) => {
      resolve(Boolean(data.backend_token));
    });
  });
}

function handleLogout(button) {
  if (button) button.disabled = true;

  chrome.runtime.sendMessage({ type: "LOGOUT" }, (response) => {
    if (button) button.disabled = false;

    if (chrome.runtime.lastError) {
      setStatus(`Logout failed: ${chrome.runtime.lastError.message}`);
      return;
    }

    showLoggedOut();
    clearStatus();
    setStatus("Logged out successfully.");
  });
}

async function refresh() {
  const tokenPresent = await hasStoredToken();

  chrome.runtime.sendMessage({ type: "GET_AUTH_STATUS" }, async (response) => {
    if (chrome.runtime.lastError) {
      if (tokenPresent) {
        showStaleSession();
      } else {
        showLoggedOut();
        setStatus("Login required before LeetCode sync is enabled.");
      }
      return;
    }

    if (response?.user) {
      showLoggedIn(response.user);
    } else if (tokenPresent) {
      showStaleSession();
    } else {
      showLoggedOut();
      setStatus("Login required before LeetCode sync is enabled.");
    }
  });

  chrome.storage.local.get(["last_sync_status"], (data) => {
    const last = data.last_sync_status;
    if (!last || last.status === "logged_in") return;
    setStatus(`${last.status}: ${last.message}`);
  });
}

document.getElementById("login-btn").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "LOGIN" }, () => window.close());
});

document.getElementById("login-again-btn").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "LOGIN" }, () => window.close());
});

document.getElementById("logout-btn").addEventListener("click", (event) => {
  handleLogout(event.currentTarget);
});

document.getElementById("logout-stale-btn").addEventListener("click", (event) => {
  handleLogout(event.currentTarget);
});

chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local" || !changes.backend_token) return;
  refresh();
});

refresh();
