const DashboardView = {
  activeWs: null,

  async render() {
    return `
      <!-- Gauges Grid -->
      <div class="grid-4">
        <div class="card metric-card">
          <div class="metric-icon cpu">⚡</div>
          <div class="metric-data" style="flex:1">
            <span class="metric-label">CPU Usage</span>
            <span class="metric-value" id="dash-cpu-val">0.0%</span>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill fill-cpu" id="dash-cpu-bar" style="width: 0%"></div>
            </div>
            <small style="color:var(--text-dim); font-size:11px; margin-top:4px;" id="dash-cpu-sub">0 Cores</small>
          </div>
        </div>

        <div class="card metric-card">
          <div class="metric-icon ram">🧠</div>
          <div class="metric-data" style="flex:1">
            <span class="metric-label">RAM Memory</span>
            <span class="metric-value" id="dash-ram-val">0.0%</span>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill fill-ram" id="dash-ram-bar" style="width: 0%"></div>
            </div>
            <small style="color:var(--text-dim); font-size:11px; margin-top:4px;" id="dash-ram-sub">Used: 0GB | Free: 0GB</small>
          </div>
        </div>

        <div class="card metric-card">
          <div class="metric-icon disk">💾</div>
          <div class="metric-data" style="flex:1">
            <span class="metric-label">Disk Storage</span>
            <span class="metric-value" id="dash-disk-val">0.0%</span>
            <div class="progress-bar-bg">
              <div class="progress-bar-fill fill-disk" id="dash-disk-bar" style="width: 0%"></div>
            </div>
            <small style="color:var(--text-dim); font-size:11px; margin-top:4px;" id="dash-disk-sub">Used: 0GB | Free: 0GB</small>
          </div>
        </div>

        <div class="card metric-card">
          <div class="metric-icon uptime">⏱️</div>
          <div class="metric-data">
            <span class="metric-label">Server Uptime</span>
            <span class="metric-value" id="dash-uptime-val">--</span>
            <small style="color:var(--text-dim); font-size:11px; margin-top:4px;" id="dash-sys-sub">Ubuntu Server</small>
          </div>
        </div>
      </div>

      <!-- Network & System Summary Banner -->
      <div class="card" style="margin-bottom:24px; padding:16px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
        <div style="display:flex; gap:24px;">
          <div><span style="color:var(--text-muted); font-size:12px;">HOSTNAME</span><br><strong id="dash-net-host">--</strong></div>
          <div><span style="color:var(--text-muted); font-size:12px;">OS INFO</span><br><strong id="dash-net-os">--</strong></div>
          <div><span style="color:var(--text-muted); font-size:12px;">PYTHON RUNTIME</span><br><strong id="dash-net-py">--</strong></div>
        </div>
        <div style="display:flex; gap:24px;">
          <div><span style="color:var(--text-muted); font-size:12px;">NETWORK TRAFFIC</span><br><span style="color:var(--accent-cyan); font-weight:600;" id="dash-net-io">↑ 0 MB | ↓ 0 MB</span></div>
          <div><span style="color:var(--text-muted); font-size:12px;">LOAD AVG</span><br><span style="color:var(--accent-primary); font-weight:600;" id="dash-net-load">0.00, 0.00, 0.00</span></div>
        </div>
      </div>

      <div class="grid-2">
        <!-- Active Projects -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Projects Overview</h3>
            <a href="#/projects" class="btn btn-secondary btn-sm">Manage Projects</a>
          </div>
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Project Name</th>
                  <th>Framework</th>
                  <th>Status</th>
                  <th>Port</th>
                </tr>
              </thead>
              <tbody id="dash-projects-tbody">
                <tr><td colspan="4">Loading projects...</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- System Services -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Running Services</h3>
            <a href="#/services" class="btn btn-secondary btn-sm">View All Services</a>
          </div>
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Memory</th>
                </tr>
              </thead>
              <tbody id="dash-services-tbody">
                <tr><td colspan="4">Loading services...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="grid-2">
        <!-- Recent Deployments -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Recent Deployments</h3>
            <a href="#/deployments" class="btn btn-secondary btn-sm">All History</a>
          </div>
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Commit</th>
                  <th>Status</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody id="dash-deployments-tbody">
                <tr><td colspan="4">Loading deployments...</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Recent System Events -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">System Activity Log</h3>
            <a href="#/logs" class="btn btn-secondary btn-sm">Live Stream</a>
          </div>
          <div id="dash-events-list">
            <div style="padding: 10px; color: var(--text-muted)">Loading activity...</div>
          </div>
        </div>
      </div>
    `;
  },

  async mount() {
    this.loadStaticData();

    // Setup WebSocket for live metrics push
    this.activeWs = new WSManager('/ws/stats', (data) => {
      document.getElementById('dash-cpu-val').innerText = `${data.cpu_percent.toFixed(1)}%`;
      document.getElementById('dash-cpu-bar').style.width = `${data.cpu_percent}%`;
      document.getElementById('dash-cpu-sub').innerText = `${data.cpu_cores || 1} CPU Cores`;

      document.getElementById('dash-ram-val').innerText = `${data.memory_percent.toFixed(1)}%`;
      document.getElementById('dash-ram-bar').style.width = `${data.memory_percent}%`;
      document.getElementById('dash-ram-sub').innerText = `Used: ${data.memory_used_gb} GB | Free: ${data.memory_free_gb || 0.0} GB`;

      document.getElementById('dash-disk-val').innerText = `${data.disk_percent.toFixed(1)}%`;
      document.getElementById('dash-disk-bar').style.width = `${data.disk_percent}%`;
      document.getElementById('dash-disk-sub').innerText = `Used: ${data.disk_used_gb} GB | Free: ${data.disk_free_gb || 0.0} GB`;

      document.getElementById('dash-uptime-val').innerText = data.uptime_human;
      document.getElementById('dash-sys-sub').innerText = data.platform || 'Ubuntu Server';

      document.getElementById('dash-net-host').innerText = data.hostname || 'ubuntu';
      document.getElementById('dash-net-os').innerText = data.platform || 'Linux';
      document.getElementById('dash-net-py').innerText = `Python ${data.python_version || '3.x'}`;

      if (data.network) {
        document.getElementById('dash-net-io').innerText = `↑ ${data.network.bytes_sent_mb} MB | ↓ ${data.network.bytes_recv_mb} MB`;
      }
      if (data.load_avg) {
        document.getElementById('dash-net-load').innerText = data.load_avg.map(l => l.toFixed(2)).join(', ');
      }
    });
    this.activeWs.connect();
  },

  unmount() {
    if (this.activeWs) {
      this.activeWs.close();
    }
  },

  async loadStaticData() {
    try {
      const [projects, services, deployments, events] = await Promise.all([
        API.getProjects(),
        API.getServices(),
        API.getDeployments(),
        API.getEvents()
      ]);

      // Populate projects
      const projTbody = document.getElementById('dash-projects-tbody');
      if (projects.length === 0) {
        projTbody.innerHTML = `<tr><td colspan="4">No projects registered yet.</td></tr>`;
      } else {
        projTbody.innerHTML = projects.slice(0, 5).map(p => `
          <tr>
            <td><strong>${p.name}</strong></td>
            <td>${p.framework}</td>
            <td><span class="status-pill ${p.status}">${p.status}</span></td>
            <td>${p.port || 'N/A'}</td>
          </tr>
        `).join('');
      }

      // Populate services
      const srvTbody = document.getElementById('dash-services-tbody');
      srvTbody.innerHTML = services.slice(0, 5).map(s => `
        <tr>
          <td><strong>${s.display_name}</strong></td>
          <td><span style="text-transform:uppercase; font-size:11px; font-weight:600">${s.type}</span></td>
          <td><span class="status-pill ${s.status}">${s.status}</span></td>
          <td>${s.memory_mb.toFixed(1)} MB</td>
        </tr>
      `).join('');

      // Populate deployments
      const depTbody = document.getElementById('dash-deployments-tbody');
      if (deployments.length === 0) {
        depTbody.innerHTML = `<tr><td colspan="4">No deployments executed yet.</td></tr>`;
      } else {
        depTbody.innerHTML = deployments.slice(0, 5).map(d => `
          <tr>
            <td><strong>${d.project_name}</strong></td>
            <td><code>#${d.commit_hash}</code></td>
            <td><span class="status-pill ${d.status}">${d.status}</span></td>
            <td>${d.duration_seconds}s</td>
          </tr>
        `).join('');
      }

      // Populate system events
      const eventsList = document.getElementById('dash-events-list');
      eventsList.innerHTML = events.slice(0, 5).map(e => `
        <div class="event-item">
          <div class="event-dot ${e.level}"></div>
          <div>
            <div class="event-text">${e.message}</div>
            <div class="event-time">${new Date(e.timestamp).toLocaleTimeString()} • ${e.category}</div>
          </div>
        </div>
      `).join('');

    } catch (err) {
      console.error('Error loading dashboard data:', err);
    }
  }
};
