const ServerView = {
  activeWs: null,

  async render() {
    return `
      <div class="grid-2">
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">System Infrastructure Overview</h3>
          </div>
          <table class="table">
            <tbody>
              <tr><th>Hostname</th><td id="srv-host">--</td></tr>
              <tr><th>Operating System</th><td id="srv-platform">--</td></tr>
              <tr><th>Python Version</th><td id="srv-py">--</td></tr>
              <tr><th>CPU Cores</th><td id="srv-cores">--</td></tr>
              <tr><th>RAM Total / Used / Free</th><td id="srv-ram-total">--</td></tr>
              <tr><th>Disk Total / Used / Free</th><td id="srv-disk-total">--</td></tr>
              <tr><th>Network I/O</th><td id="srv-net-io">--</td></tr>
              <tr><th>System Uptime</th><td id="srv-uptime">--</td></tr>
            </tbody>
          </table>
        </div>

        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Load Averages (1m, 5m, 15m)</h3>
          </div>
          <div style="display:flex; justify-content:space-around; align-items:center; height:180px;">
            <div style="text-align:center">
              <div style="font-size:32px; font-weight:bold; color:var(--accent-primary)" id="load-1">0.00</div>
              <div style="color:var(--text-muted); font-size:13px; margin-top:4px;">1 Min</div>
            </div>
            <div style="text-align:center">
              <div style="font-size:32px; font-weight:bold; color:var(--accent-cyan)" id="load-5">0.00</div>
              <div style="color:var(--text-muted); font-size:13px; margin-top:4px;">5 Min</div>
            </div>
            <div style="text-align:center">
              <div style="font-size:32px; font-weight:bold; color:var(--accent-emerald)" id="load-15">0.00</div>
              <div style="color:var(--text-muted); font-size:13px; margin-top:4px;">15 Min</div>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Active Process Resource Manager</h3>
          <button class="btn btn-secondary btn-sm" onclick="ServerView.loadProcesses()">Refresh Processes</button>
        </div>
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>PID</th>
                <th>Process Name</th>
                <th>User</th>
                <th>Status</th>
                <th>Memory (MB)</th>
                <th>CPU %</th>
              </tr>
            </thead>
            <tbody id="proc-tbody">
              <tr><td colspan="6">Loading active processes...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  },

  async mount() {
    this.loadProcesses();

    // Fetch initial REST overview
    try {
      const overview = await API.request('/server/overview');
      document.getElementById('srv-host').innerText = overview.hostname;
      document.getElementById('srv-platform').innerText = `${overview.os_name} ${overview.os_release} (${overview.architecture})`;
      document.getElementById('srv-py').innerText = `Python ${overview.python_version}`;
      document.getElementById('srv-cores').innerText = `${overview.cpu_cores_logical} Logical Cores (${overview.cpu_cores_physical} Physical)`;
    } catch (err) {
      console.warn('Overview REST fetch error:', err);
    }

    this.activeWs = new WSManager('/ws/stats', (data) => {
      document.getElementById('srv-host').innerText = data.hostname;
      document.getElementById('srv-platform').innerText = data.platform;
      document.getElementById('srv-py').innerText = `Python ${data.python_version || '3.x'}`;
      document.getElementById('srv-cores').innerText = `${data.cpu_cores} Logical Cores`;
      document.getElementById('srv-ram-total').innerText = `${data.memory_total_gb} GB total | ${data.memory_used_gb} GB used | ${data.memory_free_gb || 0.0} GB free (${data.memory_percent}%)`;
      document.getElementById('srv-disk-total').innerText = `${data.disk_total_gb} GB total | ${data.disk_used_gb} GB used | ${data.disk_free_gb || 0.0} GB free (${data.disk_percent}%)`;
      document.getElementById('srv-uptime').innerText = data.uptime_human;

      if (data.network) {
        document.getElementById('srv-net-io').innerText = `Sent: ${data.network.bytes_sent_mb} MB | Recv: ${data.network.bytes_recv_mb} MB | Interfaces: ${data.network.interfaces ? data.network.interfaces.join(', ') : 'eth0'}`;
      }

      if (data.load_avg && data.load_avg.length >= 3) {
        document.getElementById('load-1').innerText = data.load_avg[0].toFixed(2);
        document.getElementById('load-5').innerText = data.load_avg[1].toFixed(2);
        document.getElementById('load-15').innerText = data.load_avg[2].toFixed(2);
      }
    });
    this.activeWs.connect();
  },

  unmount() {
    if (this.activeWs) {
      this.activeWs.close();
    }
  },

  async loadProcesses() {
    const tbody = document.getElementById('proc-tbody');
    try {
      const procs = await API.getProcesses();
      tbody.innerHTML = procs.map(p => `
        <tr>
          <td><code>#${p.pid}</code></td>
          <td><strong>${p.name}</strong></td>
          <td>${p.username}</td>
          <td><span class="status-pill running">${p.status}</span></td>
          <td>${p.memory_mb} MB</td>
          <td>${p.cpu_percent.toFixed(1)}%</td>
        </tr>
      `).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="6" style="color:var(--accent-rose)">Failed to fetch process table: ${err.message}</td></tr>`;
    }
  }
};
