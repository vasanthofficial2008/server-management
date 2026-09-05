const DeploymentsView = {
  activeWs: null,
  currentDeployments: [],

  async render() {
    return `
      <div class="card" style="margin-bottom:24px;">
        <div class="card-header">
          <div>
            <h3 class="card-title">Real-Time Deployment Pipeline & Rollback History</h3>
            <small style="color:var(--text-muted)">Live step logs, verified release commits, and automated rollback execution</small>
          </div>
          <button class="btn btn-secondary btn-sm" onclick="DeploymentsView.loadDeployments()">🔄 Refresh</button>
        </div>
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Project</th>
                <th>Branch</th>
                <th>Target Commit</th>
                <th>Date / Time</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="deployments-tbody">
              <tr><td colspan="8">Loading deployment history...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Real-Time Log Viewer Modal -->
      <div id="deploy-log-modal" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.85); z-index:999; backdrop-filter:blur(6px); align-items:center; justify-content:center;">
        <div class="card" style="width:100%; max-width:820px; margin:20px;">
          <div class="card-header">
            <h3 class="card-title" id="log-modal-title">Live Deployment Output Console</h3>
            <button class="btn btn-secondary btn-sm" onclick="DeploymentsView.closeLogModal()">✕</button>
          </div>
          <div class="terminal-window" id="log-modal-content" style="height:420px; font-family:'JetBrains Mono', monospace; font-size:12px; line-height:1.4;"></div>
        </div>
      </div>
    `;
  },

  async mount() {
    this.loadDeployments();
  },

  unmount() {
    if (this.activeWs) {
      this.activeWs.close();
    }
  },

  async loadDeployments() {
    const tbody = document.getElementById('deployments-tbody');
    try {
      this.currentDeployments = await API.getDeployments();
      if (this.currentDeployments.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8">No deployment runs recorded. Trigger a deploy from Projects tab.</td></tr>`;
        return;
      }

      tbody.innerHTML = this.currentDeployments.map(d => {
        const isRollback = d.is_rollback || d.status === 'rollback';
        const typeBadge = isRollback 
          ? `<span style="background:rgba(245, 158, 11, 0.15); color:var(--accent-amber); border:1px solid rgba(245, 158, 11, 0.3); padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold;">🔄 Rollback</span>`
          : `<span style="background:rgba(56, 189, 248, 0.15); color:var(--accent-cyan); border:1px solid rgba(56, 189, 248, 0.3); padding:2px 8px; border-radius:12px; font-size:11px; font-weight:bold;">🚀 Release</span>`;

        const targetHash = d.target_rollback_commit || d.new_commit || d.commit_hash || 'head';
        const isKnownGood = d.status === 'success' && !isRollback;

        return `
          <tr>
            <td><strong>#${d.id}</strong></td>
            <td>${typeBadge}</td>
            <td><strong>${d.project_name}</strong></td>
            <td><code>${d.branch || 'main'}</code></td>
            <td><code>#${targetHash}</code></td>
            <td><small style="color:var(--text-muted)">${new Date(d.started_at).toLocaleString()}</small></td>
            <td><span class="status-pill ${d.status}">${d.status}</span></td>
            <td>
              <div style="display:flex; gap:6px;">
                <button class="btn btn-secondary btn-sm" onclick="DeploymentsView.streamLog(${d.id})">📋 View Logs</button>
                ${isKnownGood 
                  ? `<button class="btn btn-warning btn-sm" style="color:var(--accent-amber);" onclick="DeploymentsView.triggerRollback(${d.id}, '${d.project_name}', '${targetHash}')">🔄 Rollback</button>`
                  : `<button class="btn btn-secondary btn-sm" disabled style="opacity:0.5; cursor:not-allowed;">Rollback</button>`
                }
              </div>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="8" style="color:var(--accent-rose)">Failed to fetch deployments: ${err.message}</td></tr>`;
    }
  },

  async triggerRollback(deploymentId, projectName, commitHash) {
    if (!confirm(`⚠️ ADMINISTRATOR CONFIRMATION REQUIRED:\n\nAre you sure you want to ROLL BACK project '${projectName}' to known-good release commit #${commitHash}?`)) {
      return;
    }

    try {
      const rollbackRes = await API.request('/deployments/rollback', {
        method: 'POST',
        body: JSON.stringify({ deployment_id: deploymentId })
      });

      this.loadDeployments();
      this.streamLog(rollbackRes.id);
    } catch (err) {
      alert(`Rollback failed: ${err.message}`);
    }
  },

  streamLog(id) {
    const d = (this.currentDeployments || []).find(item => item.id === id);
    const titleEl = document.getElementById('log-modal-title');
    const contentEl = document.getElementById('log-modal-content');

    titleEl.innerText = `Deployment Output: #${id} (${d ? d.project_name : ''})`;
    contentEl.innerText = d && d.log ? d.log : 'Connecting to deployment WebSocket log stream...\n';

    if (this.activeWs) {
      this.activeWs.close();
    }

    this.activeWs = new WSManager(`/ws/deployments/${id}`, (line) => {
      contentEl.innerText += line;
      contentEl.scrollTop = contentEl.scrollHeight;
    });
    this.activeWs.connect();

    document.getElementById('deploy-log-modal').style.display = 'flex';
  },

  closeLogModal() {
    if (this.activeWs) {
      this.activeWs.close();
    }
    document.getElementById('deploy-log-modal').style.display = 'none';
  }
};
