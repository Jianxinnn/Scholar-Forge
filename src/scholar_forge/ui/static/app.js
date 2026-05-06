(function () {
  function collectRunPayload(form) {
    const data = {};
    const providers = [];
    for (const element of form.elements) {
      if (!element.name || element.disabled) continue;
      if (element.type === "checkbox") {
        if (element.name === "providers") {
          if (element.checked) providers.push(element.value);
        } else {
          data[element.name] = element.checked;
        }
        continue;
      }
      data[element.name] = element.value;
    }
    if (providers.length) data.providers = providers;
    return data;
  }

  async function createRun(form) {
    const message = form.querySelector("[data-form-message]");
    if (message) message.textContent = "Starting...";
    const response = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectRunPayload(form)),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = body.detail || "Could not start run.";
      if (message) message.textContent = detail;
      return;
    }
    window.location.href = "/runs/" + body.run_id;
  }

  for (const form of document.querySelectorAll("[data-run-form]")) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      createRun(form);
    });
  }

  const tabs = document.querySelector("[data-tabs]");
  if (tabs) {
    tabs.addEventListener("click", function (event) {
      const button = event.target.closest("[data-tab]");
      if (!button) return;
      const tab = button.dataset.tab;
      for (const item of document.querySelectorAll("[data-tab]")) item.classList.toggle("active", item === button);
      for (const panel of document.querySelectorAll("[data-panel]")) {
        panel.classList.toggle("active", panel.dataset.panel === tab);
      }
    });
  }

  const runRoot = document.querySelector("[data-run-id]");
  const runId = runRoot ? runRoot.dataset.runId : "";
  const activeStatuses = new Set(["queued", "running", "cancel_requested"]);

  function readCount(name) {
    const el = document.querySelector("[data-count-" + name + "]");
    const value = el ? parseInt(el.textContent || "0", 10) : 0;
    return Number.isFinite(value) ? value : 0;
  }

  function pageCountsKey() {
    return [readCount("sources"), readCount("evidence"), readCount("resources")].join(":");
  }

  let lastCountsKey = pageCountsKey();

  function countsKey(run) {
    const counts = run.counts || {};
    return [
      counts.sources || 0,
      counts.evidence || 0,
      counts.resources || 0,
    ].join(":");
  }

  function setCount(name, value) {
    const el = document.querySelector("[data-count-" + name + "]");
    if (el) el.textContent = value || 0;
  }

  function escapeHtml(value) {
    return value.toString().replace(/[&<>"']/g, function (char) {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        "\"": "&quot;",
        "'": "&#039;",
      }[char];
    });
  }

  function renderSteps(steps) {
    const container = document.querySelector("[data-progress-steps]");
    if (!container || !Array.isArray(steps)) return;
    container.innerHTML = steps.map(function (step) {
      return [
        '<div class="step state-' + escapeHtml(step.state || "pending") + '">',
        '<span class="step-dot"></span>',
        '<span>' + escapeHtml(step.label || step.key || "") + '</span>',
        '</div>',
      ].join("");
    }).join("");
  }

  function renderProviders(providers) {
    const container = document.querySelector("[data-provider-list]");
    if (!container || !Array.isArray(providers)) return;
    if (!providers.length) {
      container.innerHTML = '<p class="muted">Waiting for provider events...</p>';
      return;
    }
    container.innerHTML = providers.map(function (item) {
      return [
        '<div class="provider-row">',
        '<strong>' + escapeHtml(item.provider || "unknown") + '</strong>',
        '<span class="badge status-' + escapeHtml(item.last_status || "") + '">' + escapeHtml(item.last_status || "pending") + '</span>',
        '<small>' + escapeHtml((item.results || 0) + " results" + (item.errors ? ", " + item.errors + " errors" : "")) + '</small>',
        '</div>',
      ].join("");
    }).join("");
  }

  function renderEvents(events) {
    const container = document.querySelector("[data-event-list]");
    if (!container || !Array.isArray(events)) return;
    if (!events.length) {
      container.innerHTML = '<p class="muted">No events yet.</p>';
      return;
    }
    container.innerHTML = events.slice().reverse().map(function (event) {
      const query = event.query ? " · " + event.query : "";
      return [
        '<div class="event-row">',
        '<span class="badge status-' + escapeHtml(event.status || "") + '">' + escapeHtml(event.status || "unknown") + '</span>',
        '<span>' + escapeHtml((event.provider || "unknown") + query) + '</span>',
        '<small title="' + escapeHtml(event.detail || "") + '">' + escapeHtml(event.detail || "") + '</small>',
        '</div>',
      ].join("");
    }).join("");
  }

  function updateRunUI(run) {
    const statusEl = document.querySelector("[data-run-status]");
    const progressStatusEl = document.querySelector("[data-progress-status]");
    const stageEl = document.querySelector("[data-run-stage]");
    if (statusEl) {
      statusEl.textContent = run.status || "";
      statusEl.className = "badge status-" + (run.status || "");
    }
    if (progressStatusEl) {
      progressStatusEl.textContent = run.status || "";
      progressStatusEl.className = "badge status-" + (run.status || "");
    }
    if (stageEl) stageEl.textContent = run.stage || "";
    const counts = run.counts || {};
    setCount("sources", counts.sources || 0);
    setCount("evidence", counts.evidence || 0);
    setCount("resources", counts.resources || 0);
    const cancel = document.querySelector("[data-cancel-run]");
    if (cancel) cancel.disabled = !activeStatuses.has(run.status);
  }

  async function pollRun() {
    if (!runId) return;
    const response = await fetch("/api/runs/" + runId + "/progress");
    if (!response.ok) return;
    const body = await response.json();
    const run = body.run || {};
    updateRunUI(run);
    renderSteps(body.steps || []);
    renderProviders(body.providers || []);
    renderEvents(body.events || []);
    const currentCountsKey = countsKey(run);
    if (activeStatuses.has(run.status) && currentCountsKey !== lastCountsKey) {
      window.location.reload();
      return;
    }
    if (!activeStatuses.has(run.status) && window.__scholarForgeWasActive) {
      window.location.reload();
    }
    lastCountsKey = currentCountsKey;
    window.__scholarForgeWasActive = activeStatuses.has(run.status);
    if (activeStatuses.has(run.status)) window.setTimeout(pollRun, 1800);
  }

  if (runId) pollRun();

  const cancelButton = document.querySelector("[data-cancel-run]");
  if (cancelButton && runId) {
    cancelButton.addEventListener("click", async function () {
      cancelButton.disabled = true;
      await fetch("/api/runs/" + runId + "/cancel", { method: "POST" });
      pollRun();
    });
  }

  async function askBundle(payload) {
    if (!runId) return;
    const box = document.querySelector("[data-followup-answer]");
    if (box) box.textContent = "Thinking...";
    const response = await fetch("/api/runs/" + runId + "/followup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const body = await response.json().catch(() => ({}));
    if (box) box.textContent = body.answer || body.detail || "No answer.";
  }

  for (const button of document.querySelectorAll("[data-followup-intent]")) {
    button.addEventListener("click", function () {
      askBundle({
        intent: button.dataset.followupIntent,
        source_id: button.dataset.sourceId || "",
      });
    });
  }

  const followupForm = document.querySelector("[data-followup-form]");
  if (followupForm) {
    followupForm.addEventListener("submit", function (event) {
      event.preventDefault();
      const question = new FormData(followupForm).get("question") || "";
      askBundle({ question: question.toString() });
    });
  }
})();
