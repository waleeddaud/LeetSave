function setStatus(text) {
  const statusEl = document.getElementById("status");
  statusEl.textContent = text;
  statusEl.classList.remove("hidden");
}

function showLoggedIn(user) {
  document.getElementById("logged-out").classList.add("hidden");
  document.getElementById("logged-in").classList.remove("hidden");
  document.getElementById("username").textContent = user.github_username;
  document.getElementById("avatar").src = user.avatar_url || "";
  document.getElementById("repo").textContent = user.repo_full_name
    ? `Repo: ${user.repo_full_name}`
    : "Repo will be created on first sync";
}

function showLoggedOut() {
  document.getElementById("logged-in").classList.add("hidden");
  document.getElementById("logged-out").classList.remove("hidden");
}

async function refresh() {
  chrome.runtime.sendMessage({ type: "GET_AUTH_STATUS" }, (response) => {
    if (chrome.runtime.lastError) {
      showLoggedOut();
      return;
    }

    if (response?.user) {
      showLoggedIn(response.user);
    } else {
      showLoggedOut();
      setStatus("Login required before LeetCode sync is enabled.");
    }
  });

  chrome.storage.local.get(["last_sync_status"], (data) => {
    const last = data.last_sync_status;
    if (!last) return;
    setStatus(`${last.status}: ${last.message}`);
  });
}

document.getElementById("login-btn").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "LOGIN" }, () => window.close());
});

document.getElementById("logout-btn").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "LOGOUT" }, refresh);
});

refresh();
