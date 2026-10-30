/* Engineering sessions use their own state and polling generation. */
(() => {
  const byId = id => document.getElementById(id);
  let sessions;
  try { sessions = JSON.parse(localStorage.getItem('lite_engineering_sessions') || '[]'); }
  catch { sessions = []; }
  if (!Array.isArray(sessions)) sessions = [];
  let active = '', generation = 0, timer, status;
  const terminal = new Set(['completed', 'failed', 'cancelled']);
  const labels = {received: 'Request received', inspecting: 'Inspecting repository', planning: 'Planning',
    generating: 'Generating patch', patch_proposed: 'Validating patch', awaiting_approval: 'Awaiting approval',
    applying: 'Applying approved patch', patch_applied: 'Patch applied', testing: 'Running tests',
    diagnosing: 'Diagnosing failure', retry_planning: 'Planning retry', rolling_back: 'Restoring files',
    verifying: 'Verifying repair', cancelling: 'Stopping and restoring files', completed: 'Verified repair',
    failed: 'Failed', cancelled: 'Cancelled'};

  async function api(path, method = 'GET', body) {
    const base = location.protocol !== 'file:' ? '/api/engineering/' : `${currentBackendUrl}/engineering/`;
    const response = await fetch(base + path, {method, headers: {'Content-Type': 'application/json'},
      body: body === undefined ? undefined : JSON.stringify(body)});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data));
    return data;
  }

  function choices() {
    byId('engineeringSessions').replaceChildren();
    for (const session of sessions) {
      const option = document.createElement('option');
      option.value = session.id;
      option.textContent = session.title;
      byId('engineeringSessions').append(option);
    }
    byId('engineeringSessions').value = active;
  }

  function render(data) {
    status = data;
    const label = data.failure_category === 'policy_rejection' ? 'Safely rejected by policy' : labels[data.state] || data.state;
    byId('engineeringState').textContent = `${label} · attempt ${data.attempt}/${data.max_attempts} · ${data.session_id}`;
    byId('engineeringError').textContent = data.error_message || (data.warnings || []).join('\n');
    byId('engineeringDiff').textContent = data.current_diff || 'No validated patch yet.';
    byId('engineeringTests').textContent = JSON.stringify({tests: data.test_results,
      verification: data.verification_results, rollback: data.rollback}, null, 2);
    byId('engineeringEvents').textContent = (data.events || []).map(e => `${e.attempt}: ${labels[e.to] || e.to}`).join('\n');
    byId('engineeringApprove').disabled = data.state !== 'awaiting_approval';
    byId('engineeringReject').disabled = data.state !== 'awaiting_approval';
    byId('engineeringCancel').disabled = terminal.has(data.state);
  }

  async function poll(token) {
    clearTimeout(timer);
    if (!active || token !== generation) return;
    try {
      const data = await api(`status/${encodeURIComponent(active)}`);
      if (token !== generation) return;
      render(data);
      if (!terminal.has(data.state)) timer = setTimeout(() => poll(token), 500);
    } catch (error) {
      if (token === generation) byId('engineeringError').textContent = error.message;
    }
  }

  byId('engineeringOpen').addEventListener('click', () => {
    byId('engineeringDialog').showModal();
    if (active) poll(++generation);
  });
  byId('engineeringClose').addEventListener('click', () => byId('engineeringDialog').close());
  byId('engineeringSessions').addEventListener('change', event => {
    active = event.target.value;
    status = null;
    poll(++generation);
  });
  byId('engineeringRefresh').addEventListener('click', () => poll(++generation));
  byId('engineeringStart').addEventListener('click', async () => {
    const button = byId('engineeringStart');
    button.disabled = true;
    byId('engineeringError').textContent = '';
    try {
      const task = byId('engineeringTask').value.trim();
      const root = byId('engineeringRoot').value.trim();
      const command = byId('engineeringCommand').value.trim();
      if (!task || !root || !command) throw new Error('Enter a task, repository path, and test command.');
      const data = await api('start', 'POST', {task_prompt: task, repo_root: root, test_command: command,
        memory_enabled: byId('engineeringMemory').checked, strategy_enabled: byId('engineeringStrategy').checked,
        fallback_enabled: true});
      active = data.session_id;
      sessions.push({id: active, title: task.slice(0, 50)});
      localStorage.setItem('lite_engineering_sessions', JSON.stringify(sessions));
      choices(); render(data); poll(++generation);
    } catch (error) { byId('engineeringError').textContent = error.message; }
    finally { button.disabled = false; }
  });
  for (const action of ['approve', 'reject', 'cancel']) {
    byId(`engineering${action[0].toUpperCase() + action.slice(1)}`).addEventListener('click', async () => {
      if (!active || !status) return;
      const id = active, token = generation;
      byId('engineeringApprove').disabled = true;
      byId('engineeringReject').disabled = true;
      try {
        const query = action === 'approve' ? `?expected_patch_hash=${encodeURIComponent(status.current_patch_hash)}` : '';
        await api(`${action}/${encodeURIComponent(id)}${query}`, 'POST');
        if (id === active && token === generation) poll(token);
      } catch (error) { byId('engineeringError').textContent = error.message; }
    });
  }
  if (sessions.length) active = sessions[sessions.length - 1].id;
  choices();
  api('capabilities').then(data => {
    byId('configuredModel').textContent = data.model_name + (data.lora_enabled ? ' · LoRA enabled' : '');
    byId('configuredModel').title = 'Configured model; loading occurs when a task starts';
    byId('telemetryModel').textContent = data.model_name.split('/').pop();
    byId('telemetryAttempts').textContent = `${data.max_attempts} engineering attempts`;
    byId('telemetryMemory').textContent = data.memory_enabled ? 'Enabled by default' : 'Disabled by default';
    byId('telemetryStrategy').textContent = data.strategy_enabled ? 'Enabled by default' : 'Disabled by default';
  }).catch(() => { byId('configuredModel').textContent = 'Model configuration unavailable'; });
})();
