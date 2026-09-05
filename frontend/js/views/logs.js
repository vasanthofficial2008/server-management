const LogsView = {
  activeWs: null,
  autoScroll: true,
  isPaused: false,
  currentPage: 1,
  pageSize: 50,
  totalPages: 1,
  filters: {
    category: '',
    project_id: '',
    service_id: '',
    level: '',
    search: '',
    start_date: '',
    end_date: ''
  },
  projectsList: [],
  servicesList: [],

  async render() {
    return `
      <div class="card" style="display:flex; flex-direction:column; gap:16px;">
        <div class="card-header" style="flex-wrap:wrap; gap:12px;">
          <div>
            <h3 class="card-title">Centralized System & Application Log Viewer</h3>
            <small style="color:var(--text-muted)">Real-time streaming & historical logs for deployments, applications, systemd services, and audit events</small>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary btn-sm" id="pause-btn" onclick="LogsView.togglePause()">⏸️ Pause</button>
            <button class="btn btn-primary btn-sm" onclick="LogsView.downloadLogs()">📥 Download Logs</button>
            <button class="btn btn-secondary btn-sm" onclick="LogsView.loadLogs()">🔄 Refresh</button>
          </div>
        </div>

        <!-- Filter Controls Toolbar -->
        <div style="background:rgba(255,255,255,0.03); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px; display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap:12px; align-items:end;">
          <div>
            <label class="form-label" style="font-size:11px;">Category</label>
            <select class="form-select" id="log-cat-filter" onchange="LogsView.onFilterChange()" style="font-size:12px; padding:6px 10px;">
              <option value="">All Categories</option>
              <option value="deployment">🚀 Deployment Logs</option>
              <option value="application">💻 Application Logs</option>
              <option value="systemd">⚙️ Systemd Services</option>
              <option value="audit">🔒 Audit Logs</option>
            </select>
          </div>

          <div>
            <label class="form-label" style="font-size:11px;">Target Project</label>
            <select class="form-select" id="log-proj-filter" onchange="LogsView.onFilterChange()" style="font-size:12px; padding:6px 10px;">
              <option value="">All Projects</option>
            </select>
          </div>

          <div>
            <label class="form-label" style="font-size:11px;">Target Service</label>
            <select class="form-select" id="log-srv-filter" onchange="LogsView.onFilterChange()" style="font-size:12px; padding:6px 10px;">
              <option value="">All Services</option>
            </select>
          </div>

          <div>
            <label class="form-label" style="font-size:11px;">Log Level</label>
            <select class="form-select" id="log-level-filter" onchange="LogsView.onFilterChange()" style="font-size:12px; padding:6px 10px;">
              <option value="">All Levels</option>
              <option value="INFO">INFO</option>
              <option value="SUCCESS">SUCCESS</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>

          <div>
            <label class="form-label" style="font-size:11px;">Search Query</label>
            <input type="text" class="form-input" id="log-search-filter" placeholder="Search text..." oninput="LogsView.onFilterChange()" style="font-size:12px; padding:6px 10px;">
          </div>

          <div>
            <label class="form-label" style="font-size:11px;">Start Date/Time</label>
            <input type="datetime-local" class="form-input" id="log-start-date" onchange="LogsView.onFilterChange()" style="font-size:12px; padding:4px 8px;">
          </div>

          <div>
            <label class="form-label" style="font-size:11px;">End Date/Time</label>
            <input type="datetime-local" class="form-input" id="log-end-date" onchange="LogsView.onFilterChange()" style="font-size:12px; padding:4px 8px;">
          </div>
        </div>

        <!-- Log Display Window -->
        <div class="terminal-window" id="logs-stream-window" style="height:460px; font-family:'JetBrains Mono', monospace; font-size:12px; line-height:1.5; padding:16px; background:#0b0f19; overflow-y:auto;">
          <div style="color:var(--text-dim); text-align:center; padding-top:160px;">Loading centralized system logs...</div>
        </div>

        <!-- Pagination & Footer Toolbar -->
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; font-size:12px; color:var(--text-muted);">
          <div style="display:flex; align-items:center; gap:12px;">
            <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
              <input type="checkbox" id="autoscroll-chk" checked onchange="LogsView.toggleAutoScroll(this.checked)"> Auto-scroll to bottom
            </label>
            <span id="log-total-badge">Total Entries: 0</span>
          </div>

          <div style="display:flex; align-items:center; gap:8px;">
            <button class="btn btn-secondary btn-sm" onclick="LogsView.changePage(-1)" id="prev-page-btn" disabled>⏮️ Prev</button>
            <span id="page-indicator">Page 1 of 1</span>
            <button class="btn btn-secondary btn-sm" onclick="LogsView.changePage(1)" id="next-page-btn" disabled>Next ⏭️</button>
          </div>
        </div>
      </div>
    `;
  },

  async mount() {
    await this.loadDropdownOptions();
    await this.loadLogs();
    this.connectWebSocket();
  },

  unmount() {
    if (this.activeWs) {
      this.activeWs.close();
      this.activeWs = null;
    }
  },

  async loadDropdownOptions() {
    try {
      this.projectsList = await API.getProjects();
      const projSelect = document.getElementById('log-proj-filter');
      if (projSelect) {
        projSelect.innerHTML = '<option value="">All Projects</option>' + 
          this.projectsList.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
      }

      this.servicesList = await API.getServices();
      const srvSelect = document.getElementById('log-srv-filter');
      if (srvSelect) {
        srvSelect.innerHTML = '<option value="">All Services</option>' + 
          this.servicesList.map(s => `<option value="${s.id}">${s.display_name}</option>`).join('');
      }
    } catch (err) {
      console.error('Error loading log dropdown options:', err);
    }
  },

  onFilterChange() {
    this.filters.category = document.getElementById('log-cat-filter').value;
    this.filters.project_id = document.getElementById('log-proj-filter').value;
    this.filters.service_id = document.getElementById('log-srv-filter').value;
    this.filters.level = document.getElementById('log-level-filter').value;
    this.filters.search = document.getElementById('log-search-filter').value;
    this.filters.start_date = document.getElementById('log-start-date').value;
    this.filters.end_date = document.getElementById('log-end-date').value;

    this.currentPage = 1;
    this.loadLogs();

    if (this.activeWs) {
      this.activeWs.send(JSON.stringify(this.filters));
    }
  },

  async loadLogs() {
    if (this.isPaused) return;

    const queryParams = new URLSearchParams();
    if (this.filters.category) queryParams.append('category', this.filters.category);
    if (this.filters.project_id) queryParams.append('project_id', this.filters.project_id);
    if (this.filters.service_id) queryParams.append('service_id', this.filters.service_id);
    if (this.filters.level) queryParams.append('level', this.filters.level);
    if (this.filters.search) queryParams.append('search', this.filters.search);
    if (this.filters.start_date) queryParams.append('start_date', new Date(this.filters.start_date).toISOString());
    if (this.filters.end_date) queryParams.append('end_date', new Date(this.filters.end_date).toISOString());
    queryParams.append('page', this.currentPage);
    queryParams.append('page_size', this.pageSize);

    try {
      const res = await API.request(`/logs?${queryParams.toString()}`);
      this.renderLogEntries(res.items);
      this.totalPages = res.total_pages;
      this.updatePaginationUI(res.total, res.page, res.total_pages);
    } catch (err) {
      const windowEl = document.getElementById('logs-stream-window');
      if (windowEl) {
        windowEl.innerHTML = `<div style="color:var(--accent-rose);">Error fetching logs: ${err.message}</div>`;
      }
    }
  },

  renderLogEntries(items) {
    const windowEl = document.getElementById('logs-stream-window');
    if (!windowEl) return;

    if (!items || items.length === 0) {
      windowEl.innerHTML = '<div style="color:var(--text-dim); text-align:center; padding-top:160px;">No matching log records found.</div>';
      return;
    }

    windowEl.innerHTML = items.map(entry => {
      let levelColor = '#38bdf8'; // INFO - Cyan
      if (entry.level === 'SUCCESS') levelColor = '#34d399'; // Emerald
      if (entry.level === 'WARNING') levelColor = '#fbbf24'; // Amber
      if (entry.level === 'ERROR') levelColor = '#f87171'; // Rose

      const catBadge = entry.category.toUpperCase();
      const timeStr = entry.timestamp.replace('T', ' ').substring(0, 19);

      return `
        <div style="margin-bottom:6px; word-break:break-all;">
          <span style="color:#6b7280;">[${timeStr}]</span>
          <span style="color:${levelColor}; font-weight:bold; width:65px; display:inline-block;">[${entry.level}]</span>
          <span style="color:#818cf8; width:95px; display:inline-block;">[${catBadge}]</span>
          <span style="color:#e5e7eb; font-weight:600; width:140px; display:inline-block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; vertical-align:bottom;">[${entry.source}]</span>
          <span style="color:#d1d5db;">${this.escapeHtml(entry.message)}</span>
        </div>
      `;
    }).join('');

    if (this.autoScroll && !this.isPaused) {
      windowEl.scrollTop = windowEl.scrollHeight;
    }
  },

  connectWebSocket() {
    this.activeWs = new WSManager('/ws/logs', (data) => {
      if (this.isPaused) return;
      if (data && data.items && this.currentPage === 1) {
        this.renderLogEntries(data.items);
        if (data.total !== undefined) {
          this.updatePaginationUI(data.total, 1, Math.ceil(data.total / this.pageSize));
        }
      }
    });
    this.activeWs.connect();
  },

  togglePause() {
    this.isPaused = !this.isPaused;
    const btn = document.getElementById('pause-btn');
    if (btn) {
      btn.innerText = this.isPaused ? '▶️ Resume' : '⏸️ Pause';
      btn.className = this.isPaused ? 'btn btn-primary btn-sm' : 'btn btn-secondary btn-sm';
    }
    if (!this.isPaused) {
      this.loadLogs();
    }
  },

  toggleAutoScroll(enabled) {
    this.autoScroll = enabled;
  },

  changePage(delta) {
    const newPage = this.currentPage + delta;
    if (newPage >= 1 && newPage <= this.totalPages) {
      this.currentPage = newPage;
      this.loadLogs();
    }
  },

  updatePaginationUI(total, page, totalPages) {
    document.getElementById('log-total-badge').innerText = `Total Entries: ${total}`;
    document.getElementById('page-indicator').innerText = `Page ${page} of ${totalPages || 1}`;
    document.getElementById('prev-page-btn').disabled = (page <= 1);
    document.getElementById('next-page-btn').disabled = (page >= totalPages);
  },

  downloadLogs() {
    const queryParams = new URLSearchParams();
    if (this.filters.category) queryParams.append('category', this.filters.category);
    if (this.filters.project_id) queryParams.append('project_id', this.filters.project_id);
    if (this.filters.service_id) queryParams.append('service_id', this.filters.service_id);
    if (this.filters.level) queryParams.append('level', this.filters.level);
    if (this.filters.search) queryParams.append('search', this.filters.search);
    if (this.filters.start_date) queryParams.append('start_date', new Date(this.filters.start_date).toISOString());
    if (this.filters.end_date) queryParams.append('end_date', new Date(this.filters.end_date).toISOString());

    const token = API.getToken();
    window.open(`/api/logs/download?${queryParams.toString()}&token=${encodeURIComponent(token)}`, '_blank');
  },

  escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }
};
