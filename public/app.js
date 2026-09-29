let state = { targets: [], history: [] };

function badge(status) {
  return status === "Pass" ? "pill good" : "pill warn";
}

function renderTargets() {
  $("#targetCount").textContent = `${state.targets.length} configured`;
  $("#targets").innerHTML = state.targets.map((target) => `
    <article class="item target">
      <div>
        <h3>${esc(target.name)}</h3>
        <p class="mono small">${esc(target.url)}</p>
      </div>
      <button data-check="${esc(target.id)}">Run check</button>
    </article>
  `).join("");
  document.querySelectorAll("[data-check]").forEach((button) => {
    button.addEventListener("click", () => action(button, async () => {
      const result = await api("/api/check", { target_id: button.dataset.check });
      state.history = result.history;
      renderReport(result.report);
      renderHistory();
      toast(`${result.report.target.name}: ${result.report.status}`);
    }));
  });
}

function renderReport(report) {
  const missing = report.missing_headers.length ? report.missing_headers.map(esc).join(", ") : "None";
  $("#report").innerHTML = `
    <span class="${badge(report.status)}">${esc(report.status)}</span>
    <div class="stat"><span>Status</span><strong>${report.status_code || "Offline"}</strong></div>
    <div class="stat"><span>Response</span><strong>${report.duration_ms} ms</strong></div>
    <p><strong>Missing headers:</strong><br>${missing}</p>
    <p><strong>TLS days remaining:</strong><br>${report.tls_days_remaining ?? "Not HTTPS"}</p>
    <p><strong>Internal links checked:</strong><br>${report.links.length}</p>
    ${report.error ? `<p class="bad pill">${esc(report.error)}</p>` : ""}
  `;
}

function renderHistory() {
  $("#history").innerHTML = state.history.map((check) => `
    <article class="item target">
      <div>
        <span class="${badge(check.status)}">${esc(check.status)}</span>
        <h3>${esc(check.report.target.name)}</h3>
        <p class="small muted">${new Date(check.checked_at).toLocaleString()} · ${check.duration_ms} ms</p>
      </div>
      <span class="mono small">${esc(check.target_id)}</span>
    </article>
  `).join("") || '<p class="muted">No checks yet.</p>';
}

async function refresh() {
  state = await api("/api/state");
  renderTargets();
  renderHistory();
  if (state.history[0]) renderReport(state.history[0].report);
}

refresh().catch((error) => toast(error.message));
