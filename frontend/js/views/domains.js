const DomainsView = {
  domainsData: [],
  projectsList: [],
  tunnelStatus: null,
  editingDomainId: null,

  async render() {
    return `
      <!-- Cloudflare Tunnel Status Header Card -->
      <div class="card" style="margin-bottom:24px; background:linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.9)); border:1px solid rgba(255, 255, 255, 0.1);">
        <div class="card-header" style="flex-wrap:wrap; gap:16px;">
          <div>
            <div style="display:flex; align-items:center; gap:10px;">
              <h3 class="card-title" style="margin:0;">☁️ Cloudflare Tunnel Integration</h3>
              <span class="status-pill running" id="tunnel-status-pill">Connected</span>
            </div>
            <small style="color:var(--text-muted)">Securely route external domain traffic to local application ports via controlled ingress daemon</small>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary btn-sm" onclick="DomainsView.reloadTunnel()">⚡ Reload Ingress Config</button>
            <button class="btn btn-secondary btn-sm" onclick="DomainsView.restartTunnel()">🔄 Restart Tunnel Service</button>
          </div>
        </div>

        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:16px; margin-top:16px; padding-top:16px; border-top:1px solid rgba(255,255,255,0.08);">
          <div>
            <span style="color:var(--text-muted); font-size:12px;">Managed Tunnel ID</span>
            <div style="font-family:monospace; font-weight:bold; color:var(--text-main);" id="tnl-id-val">srvpilot-tnl-7a9b3c8f</div>
          </div>
          <div>
            <span style="color:var(--text-muted); font-size:12px;">Active Ingress Routes</span>
            <div style="font-size:18px; font-weight:bold; color:var(--accent-emerald);" id="tnl-routes-val">0 Active</div>
          </div>
          <div>
            <span style="color:var(--text-muted); font-size:12px;">Security Protocol</span>
            <div style="font-size:13px; font-weight:bold; color:var(--accent-cyan);">Strict Ingress Isolation</div>
          </div>
        </div>
      </div>

      <!-- Domain Configuration Table Card -->
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">Domain Name Routing & Proxy Mappings</h3>
            <small style="color:var(--text-muted)">Validated mapping between domain → project → local port (e.g. api.example.com → 127.0.0.1:8000)</small>
          </div>
          <button class="btn btn-primary" onclick="DomainsView.openAddModal()">+ Add Domain Binding</button>
        </div>
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Domain Name</th>
                <th>Subdomain</th>
                <th>Target Project</th>
                <th>Local Endpoint</th>
                <th>HTTPS / SSL</th>
                <th>Tunnel Status</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="domains-tbody">
              <tr><td colspan="8">Loading domain mappings...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Domain Modal -->
      <div id="domain-modal" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.75); z-index:999; backdrop-filter:blur(6px); align-items:center; justify-content:center;">
        <div class="card" style="width:100%; max-width:540px; margin:20px;">
          <div class="card-header">
            <h3 class="card-title" id="dom-modal-title">Add Domain Proxy Route</h3>
            <button class="btn btn-secondary btn-sm" onclick="DomainsView.closeAddModal()">✕</button>
          </div>
          <form onsubmit="DomainsView.handleSubmit(event)">
            <div class="form-group">
              <label class="form-label">Domain Name *</label>
              <input type="text" id="dom-name" class="form-input" required placeholder="e.g. example.com or api.example.com">
              <small style="color:var(--text-muted)">Do not include http:// or https://</small>
            </div>

            <div class="form-group">
              <label class="form-label">Subdomain (Optional)</label>
              <input type="text" id="dom-sub" class="form-input" placeholder="e.g. api, www, or leave empty">
            </div>

            <div class="form-group">
              <label class="form-label">Associated Project</label>
              <select class="form-select" id="dom-project" onchange="DomainsView.onProjectSelectChange()">
                <option value="">System Router / None</option>
              </select>
            </div>

            <div style="display:grid; grid-template-columns: 2fr 1fr; gap:12px;">
              <div class="form-group">
                <label class="form-label">Local Host</label>
                <input type="text" id="dom-host" class="form-input" value="127.0.0.1" required>
              </div>
              <div class="form-group">
                <label class="form-label">Local Port *</label>
                <input type="number" id="dom-port" class="form-input" value="8000" min="1" max="65535" required>
              </div>
            </div>

            <div class="form-group">
              <label class="form-label" style="display:flex; align-items:center; gap:8px;">
                <input type="checkbox" id="dom-https" checked style="width:auto;"> Enable HTTPS & SSL Auto-Certificate
              </label>
            </div>

            <div id="validation-msg-box" style="display:none; margin-bottom:16px; padding:10px; border-radius:6px; font-size:12px;"></div>

            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:24px;">
              <button type="button" class="btn btn-secondary btn-sm" onclick="DomainsView.validateConfig()">🔍 Validate Config</button>
              <div style="display:flex; gap:12px;">
                <button type="button" class="btn btn-secondary" onclick="DomainsView.closeAddModal()">Cancel</button>
                <button type="submit" class="btn btn-primary" id="dom-submit-btn">Save Domain Route</button>
              </div>
            </div>
          </form>
        </div>
      </div>
    `;
  },

  async mount() {
    await this.loadProjectsList();
    await this.loadTunnelStatus();
    await this.loadDomains();
  },

  async loadProjectsList() {
    try {
      this.projectsList = await API.getProjects();
      const sel = document.getElementById('dom-project');
      if (sel) {
        sel.innerHTML = '<option value="">System Router / None</option>' +
          this.projectsList.map(p => `<option value="${p.id}">${p.name} (Port :${p.port || 8000})</option>`).join('');
      }
    } catch (err) {
      console.error('Error loading projects list:', err);
    }
  },

  async loadTunnelStatus() {
    try {
      const statusRes = await API.request('/domains/tunnel/status');
      this.tunnelStatus = statusRes;
      document.getElementById('tnl-id-val').innerText = statusRes.tunnel_id;
      document.getElementById('tnl-routes-val').innerText = `${statusRes.active_routes_count} Active Routes`;
      
      const pill = document.getElementById('tunnel-status-pill');
      if (pill) {
        pill.innerText = statusRes.status === 'connected' ? '🟢 Connected' : '🔴 Disconnected';
        pill.className = `status-pill ${statusRes.status === 'connected' ? 'running' : 'stopped'}`;
      }
    } catch (err) {
      console.error('Error loading tunnel status:', err);
    }
  },

  async loadDomains() {
    const tbody = document.getElementById('domains-tbody');
    try {
      this.domainsData = await API.getDomains();
      if (this.domainsData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8">No domain routes configured behind tunnel.</td></tr>`;
        return;
      }

      tbody.innerHTML = this.domainsData.map(d => `
        <tr>
          <td><strong>${d.domain_name}</strong></td>
          <td><code>${d.subdomain || '-'}</code></td>
          <td>${d.project_name ? `<strong>${d.project_name}</strong>` : '<span style="color:var(--text-dim)">System Router</span>'}</td>
          <td><code>${d.local_host || '127.0.0.1'}:${d.local_port}</code></td>
          <td>
            ${d.https_enabled || d.ssl_enabled 
              ? `<span style="color:var(--accent-emerald); font-weight:600">🔒 HTTPS / SSL</span>`
              : `<span style="color:var(--text-muted)">HTTP Only</span>`}
          </td>
          <td><span class="status-pill ${d.tunnel_status || 'connected'}">${d.tunnel_status || 'connected'}</span></td>
          <td><span class="status-pill ${d.status}">${d.status}</span></td>
          <td>
            <div style="display:flex; gap:6px;">
              <button class="btn btn-secondary btn-sm" onclick="DomainsView.openEditModal(${d.id})">Edit</button>
              <button class="btn btn-danger btn-sm" onclick="DomainsView.deleteDomain(${d.id})">Delete</button>
            </div>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="8" style="color:var(--accent-rose)">Error loading domain mappings: ${err.message}</td></tr>`;
    }
  },

  onProjectSelectChange() {
    const projId = document.getElementById('dom-project').value;
    if (projId) {
      const proj = this.projectsList.find(p => p.id == projId);
      if (proj && proj.port) {
        document.getElementById('dom-port').value = proj.port;
      }
    }
  },

  openAddModal() {
    this.editingDomainId = null;
    document.getElementById('dom-modal-title').innerText = 'Add Domain Proxy Route';
    document.getElementById('dom-name').value = '';
    document.getElementById('dom-sub').value = '';
    document.getElementById('dom-project').value = '';
    document.getElementById('dom-host').value = '127.0.0.1';
    document.getElementById('dom-port').value = '8000';
    document.getElementById('dom-https').checked = true;
    document.getElementById('validation-msg-box').style.display = 'none';
    document.getElementById('domain-modal').style.display = 'flex';
  },

  openEditModal(id) {
    const d = this.domainsData.find(dom => dom.id === id);
    if (!d) return;

    this.editingDomainId = id;
    document.getElementById('dom-modal-title').innerText = `Edit Domain Route #${id}`;
    document.getElementById('dom-name').value = d.domain_name;
    document.getElementById('dom-sub').value = d.subdomain || '';
    document.getElementById('dom-project').value = d.project_id || '';
    document.getElementById('dom-host').value = d.local_host || '127.0.0.1';
    document.getElementById('dom-port').value = d.local_port || 8000;
    document.getElementById('dom-https').checked = d.https_enabled !== false;
    document.getElementById('validation-msg-box').style.display = 'none';
    document.getElementById('domain-modal').style.display = 'flex';
  },

  closeAddModal() {
    document.getElementById('domain-modal').style.display = 'none';
  },

  async validateConfig() {
    const name = document.getElementById('dom-name').value;
    const projId = document.getElementById('dom-project').value;
    const host = document.getElementById('dom-host').value;
    const port = parseInt(document.getElementById('dom-port').value);

    const msgBox = document.getElementById('validation-msg-box');
    msgBox.style.display = 'block';

    try {
      const res = await API.request('/domains/validate', {
        method: 'POST',
        body: JSON.stringify({
          domain_name: name,
          project_id: projId ? parseInt(projId) : null,
          local_host: host,
          local_port: port
        })
      });

      msgBox.style.background = 'rgba(52, 211, 153, 0.15)';
      msgBox.style.color = '#34d399';
      msgBox.style.border = '1px solid rgba(52, 211, 153, 0.4)';
      msgBox.innerText = `✅ Valid: ${res.mapping}`;
    } catch (err) {
      msgBox.style.background = 'rgba(248, 113, 113, 0.15)';
      msgBox.style.color = '#f87171';
      msgBox.style.border = '1px solid rgba(248, 113, 113, 0.4)';
      msgBox.innerText = `❌ Validation Failed: ${err.message}`;
    }
  },

  async handleSubmit(e) {
    e.preventDefault();
    const payload = {
      domain_name: document.getElementById('dom-name').value,
      subdomain: document.getElementById('dom-sub').value,
      project_id: document.getElementById('dom-project').value ? parseInt(document.getElementById('dom-project').value) : null,
      local_host: document.getElementById('dom-host').value,
      local_port: parseInt(document.getElementById('dom-port').value),
      https_enabled: document.getElementById('dom-https').checked
    };

    try {
      if (this.editingDomainId) {
        await API.request(`/domains/${this.editingDomainId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
      } else {
        await API.createDomain(payload);
      }
      this.closeAddModal();
      await this.loadDomains();
      await this.loadTunnelStatus();
    } catch (err) {
      alert(`Save domain route failed: ${err.message}`);
    }
  },

  async reloadTunnel() {
    try {
      const res = await API.request('/domains/tunnel/reload', { method: 'POST' });
      alert(`Cloudflare Tunnel ingress configuration reloaded cleanly (${res.active_routes_count} active routes).`);
      await this.loadTunnelStatus();
    } catch (err) {
      alert(`Tunnel reload failed: ${err.message}`);
    }
  },

  async restartTunnel() {
    if (!confirm('Restart Cloudflare Tunnel daemon service?')) return;
    try {
      const res = await API.request('/domains/tunnel/restart', { method: 'POST' });
      alert(`Cloudflare Tunnel service restarted cleanly.`);
      await this.loadTunnelStatus();
    } catch (err) {
      alert(`Tunnel restart failed: ${err.message}`);
    }
  },

  async deleteDomain(id) {
    if (!confirm('Remove this domain routing assignment?')) return;
    try {
      await API.deleteDomain(id);
      await this.loadDomains();
      await this.loadTunnelStatus();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  }
};
