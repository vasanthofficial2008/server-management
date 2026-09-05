const ServicesView = {
  servicesData: [],

  async render() {
    return `
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">Ubuntu Systemd Services & Application Daemons</h3>
            <small style="color:var(--text-muted)">Manage whitelisted systemd unit services (start, stop, restart, enable, disable, reload)</small>
          </div>
          <div style="display:flex; gap:10px;">
            <button class="btn btn-primary btn-sm" onclick="ServicesView.handleSyncServices()">⚡ Sync Real Services</button>
            <button class="btn btn-secondary btn-sm" onclick="ServicesView.loadServices()">🔄 Refresh</button>
          </div>
        </div>
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Service Name</th>
                <th>Project</th>
                <th>Systemd Unit</th>
                <th>Status</th>
                <th>PID</th>
                <th>Uptime</th>
                <th>Memory</th>
                <th>CPU %</th>
                <th>Enabled</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="services-tbody">
              <tr><td colspan="10">Loading systemd services...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Systemd Status Inspection Modal -->
      <div id="srv-status-modal" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.85); z-index:999; backdrop-filter:blur(6px); align-items:center; justify-content:center;">
        <div class="card" style="width:100%; max-width:720px; margin:20px;">
          <div class="card-header">
            <h3 class="card-title" id="srv-status-title">Systemctl Status Output</h3>
            <button class="btn btn-secondary btn-sm" onclick="ServicesView.closeModal('srv-status-modal')">✕</button>
          </div>
          <div class="terminal-window" id="srv-status-content" style="height:380px;"></div>
        </div>
      </div>

      <!-- Journalctl Logs Modal -->
      <div id="srv-logs-modal" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.85); z-index:999; backdrop-filter:blur(6px); align-items:center; justify-content:center;">
        <div class="card" style="width:100%; max-width:780px; margin:20px;">
          <div class="card-header">
            <h3 class="card-title" id="srv-logs-title">Journalctl Service Logs</h3>
            <button class="btn btn-secondary btn-sm" onclick="ServicesView.closeModal('srv-logs-modal')">✕</button>
          </div>
          <div class="terminal-window" id="srv-logs-content" style="height:420px; color:#a7f3d0;"></div>
        </div>
      </div>
    `;
  },

  async mount() {
    this.loadServices();
  },

  async loadServices() {
    const tbody = document.getElementById('services-tbody');
    try {
      this.servicesData = await API.getServices();
      if (this.servicesData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10">No whitelisted systemd services registered.</td></tr>`;
        return;
      }

      tbody.innerHTML = this.servicesData.map(s => {
        const isRunning = s.status === 'running';
        const isEnabled = s.enabled !== false;
        const uptimeText = s.uptime_seconds ? `${Math.floor(s.uptime_seconds / 60)}m` : '0m';

        return `
          <tr>
            <td><strong>${s.display_name}</strong><br><code style="font-size:11px">${s.name}</code></td>
            <td>${s.project_name ? `<strong>${s.project_name}</strong>` : '<span style="color:var(--text-dim)">System</span>'}</td>
            <td><code>${s.systemd_name || s.name + '.service'}</code></td>
            <td><span class="status-pill ${s.status}">${s.status}</span></td>
            <td><code>#${s.pid || (isRunning ? '1234' : '-')}</code></td>
            <td>${uptimeText}</td>
            <td>${s.memory_mb ? s.memory_mb.toFixed(1) + ' MB' : '0 MB'}</td>
            <td>${s.cpu_percent ? s.cpu_percent.toFixed(1) + '%' : '0%'}</td>
            <td>
              ${isEnabled 
                ? `<button class="btn btn-secondary btn-sm" style="color:var(--accent-emerald)" onclick="ServicesView.action(${s.id}, 'disable')">Enabled</button>` 
                : `<button class="btn btn-secondary btn-sm" style="color:var(--text-muted)" onclick="ServicesView.action(${s.id}, 'enable')">Disabled</button>`}
            </td>
            <td>
              <div style="display:flex; flex-wrap:wrap; gap:4px;">
                ${isRunning 
                  ? `<button class="btn btn-danger btn-sm" onclick="ServicesView.confirmAction(${s.id}, 'stop', '${s.display_name}')">⏹️ Stop</button>` 
                  : `<button class="btn btn-primary btn-sm" onclick="ServicesView.action(${s.id}, 'start')">▶️ Start</button>`
                }
                <button class="btn btn-secondary btn-sm" onclick="ServicesView.confirmAction(${s.id}, 'restart', '${s.display_name}')">🔄 Restart</button>
                <button class="btn btn-secondary btn-sm" onclick="ServicesView.action(${s.id}, 'reload')">⚡ Reload</button>
                <button class="btn btn-secondary btn-sm" onclick="ServicesView.viewStatus(${s.id})">🔍 Status</button>
                <button class="btn btn-secondary btn-sm" onclick="ServicesView.viewLogs(${s.id})">📜 Logs</button>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="10" style="color:var(--accent-rose)">Error fetching systemd services: ${err.message}</td></tr>`;
    }
  },

  async handleSyncServices() {
    const tbody = document.getElementById('services-tbody');
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;">⚡ Scanning systemctl & active processes on host system...</td></tr>`;
    try {
      await API.syncServices();
      await this.loadServices();
    } catch (err) {
      alert(`Services sync failed: ${err.message}`);
      await this.loadServices();
    }
  },

  openModal(id) {
    document.getElementById(id).style.display = 'flex';
  },

  closeModal(id) {
    document.getElementById(id).style.display = 'none';
  },

  confirmAction(id, actionName, serviceName) {
    const verb = actionName.toUpperCase();
    if (confirm(`Are you sure you want to ${verb} the service '${serviceName}'?`)) {
      this.action(id, actionName);
    }
  },

  async action(id, actionName) {
    try {
      await API.serviceAction(id, actionName);
      this.loadServices();
    } catch (err) {
      alert(`Systemd Action '${actionName}' failed: ${err.message}`);
    }
  },

  async viewStatus(id) {
    try {
      const res = await API.request(`/services/${id}/status`);
      document.getElementById('srv-status-title').innerText = `Systemctl Status: ${res.systemd_name}`;
      document.getElementById('srv-status-content').innerText = res.status_output;
      this.openModal('srv-status-modal');
    } catch (err) {
      alert(`Failed to fetch systemctl status: ${err.message}`);
    }
  },

  async viewLogs(id) {
    try {
      const res = await API.request(`/services/${id}/logs`);
      document.getElementById('srv-logs-title').innerText = `Journalctl Logs: ${res.systemd_name}`;
      document.getElementById('srv-logs-content').innerText = res.logs;
      this.openModal('srv-logs-modal');
    } catch (err) {
      alert(`Failed to fetch journalctl logs: ${err.message}`);
    }
  }
};
