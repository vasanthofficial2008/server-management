const ProjectsView = {
  projectsData: [],

  async render() {
    return `
      <div class="card" style="margin-bottom: 24px;">
        <div class="card-header">
          <div>
            <h3 class="card-title">Deployed Projects & Applications</h3>
            <small style="color:var(--text-muted)">Manage static sites, FastAPI, Flask, and Python applications</small>
          </div>
          <button class="btn btn-primary" onclick="ProjectsView.openCreateModal()">+ Create Project</button>
        </div>
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Project</th>
                <th>App Type</th>
                <th>Status</th>
                <th>Domain</th>
                <th>Port</th>
                <th>Branch</th>
                <th>Last Deployment</th>
                <th>Service Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="projects-tbody">
              <tr><td colspan="9">Loading project management system...</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Create Project Modal -->
      <div id="proj-create-modal" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.8); z-index:999; backdrop-filter:blur(6px); align-items:center; justify-content:center;">
        <div class="card" style="width:100%; max-width:640px; margin:20px; max-height:90vh; overflow-y:auto;">
          <div class="card-header">
            <h3 class="card-title">Create New Project</h3>
            <button class="btn btn-secondary btn-sm" onclick="ProjectsView.closeModal('proj-create-modal')">✕</button>
          </div>
          <form onsubmit="ProjectsView.handleCreate(event)">
            <div class="grid-2" style="margin:0; gap:16px;">
              <div class="form-group">
                <label class="form-label">Project Name *</label>
                <input type="text" id="c-name" class="form-input" required placeholder="e.g. Storefront API">
              </div>
              <div class="form-group">
                <label class="form-label">Application Type *</label>
                <select id="c-app-type" class="form-select" onchange="ProjectsView.onAppTypeChange('c')">
                  <option value="Python FastAPI">Python FastAPI</option>
                  <option value="Python Flask">Python Flask</option>
                  <option value="Static HTML/CSS/JavaScript">Static HTML/CSS/JavaScript</option>
                  <option value="Python Custom">Python Custom</option>
                </select>
              </div>
            </div>

            <div class="grid-2" style="margin:0; gap:16px;">
              <div class="form-group">
                <label class="form-label">Git Repository URL</label>
                <input type="text" id="c-repo" class="form-input" placeholder="https://github.com/org/repo.git">
              </div>
              <div class="form-group">
                <label class="form-label">Branch</label>
                <input type="text" id="c-branch" class="form-input" value="main">
              </div>
            </div>

            <div class="grid-2" style="margin:0; gap:16px;">
              <div class="form-group">
                <label class="form-label">Binding Port</label>
                <input type="number" id="c-port" class="form-input" value="8000">
              </div>
              <div class="form-group">
                <label class="form-label">Domain Binding</label>
                <input type="text" id="c-domain" class="form-input" placeholder="app.example.com">
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">Deployment Directory</label>
              <input type="text" id="c-dir" class="form-input" placeholder="Relative folder name (e.g. storefront-api)">
            </div>

            <div class="form-group">
              <label class="form-label">Build Command</label>
              <input type="text" id="c-cmd-build" class="form-input" placeholder="pip install -r requirements.txt">
            </div>

            <div class="form-group">
              <label class="form-label">Start Command</label>
              <input type="text" id="c-cmd-start" class="form-input" placeholder="uvicorn main:app --host 0.0.0.0 --port 8000">
            </div>

            <div style="display:flex; justify-content:flex-end; gap:12px; margin-top:24px;">
              <button type="button" class="btn btn-secondary" onclick="ProjectsView.closeModal('proj-create-modal')">Cancel</button>
              <button type="submit" class="btn btn-primary">Create Project</button>
            </div>
          </form>
        </div>
      </div>

      <!-- View Details Modal -->
      <div id="proj-view-modal" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.8); z-index:999; backdrop-filter:blur(6px); align-items:center; justify-content:center;">
        <div class="card" style="width:100%; max-width:640px; margin:20px;">
          <div class="card-header">
            <h3 class="card-title" id="v-title">Project Details</h3>
            <button class="btn btn-secondary btn-sm" onclick="ProjectsView.closeModal('proj-view-modal')">✕</button>
          </div>
          <div id="v-content" style="font-size:14px; line-height:1.8;"></div>
        </div>
      </div>

      <!-- Edit Modal -->
      <div id="proj-edit-modal" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.8); z-index:999; backdrop-filter:blur(6px); align-items:center; justify-content:center;">
        <div class="card" style="width:100%; max-width:640px; margin:20px; max-height:90vh; overflow-y:auto;">
          <div class="card-header">
            <h3 class="card-title">Edit Project Configuration</h3>
            <button class="btn btn-secondary btn-sm" onclick="ProjectsView.closeModal('proj-edit-modal')">✕</button>
          </div>
          <form onsubmit="ProjectsView.handleEdit(event)">
            <input type="hidden" id="e-id">
            <div class="form-group">
              <label class="form-label">Project Name</label>
              <input type="text" id="e-name" class="form-input" required>
            </div>
            <div class="grid-2" style="margin:0; gap:16px;">
              <div class="form-group">
                <label class="form-label">Branch</label>
                <input type="text" id="e-branch" class="form-input">
              </div>
              <div class="form-group">
                <label class="form-label">Port</label>
                <input type="number" id="e-port" class="form-input">
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">Domain Binding</label>
              <input type="text" id="e-domain" class="form-input">
            </div>
            <div class="form-group">
              <label class="form-label">Start Command</label>
              <input type="text" id="e-cmd-start" class="form-input">
            </div>
            <div style="display:flex; justify-content:flex-end; gap:12px; margin-top:24px;">
              <button type="button" class="btn btn-secondary" onclick="ProjectsView.closeModal('proj-edit-modal')">Cancel</button>
              <button type="submit" class="btn btn-primary">Save Changes</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Logs Modal -->
      <div id="proj-logs-modal" style="display:none; position:fixed; top:0; left:0; width:100vw; height:100vh; background:rgba(0,0,0,0.8); z-index:999; backdrop-filter:blur(6px); align-items:center; justify-content:center;">
        <div class="card" style="width:100%; max-width:720px; margin:20px;">
          <div class="card-header">
            <h3 class="card-title" id="logs-modal-title">Project Execution Logs</h3>
            <button class="btn btn-secondary btn-sm" onclick="ProjectsView.closeModal('proj-logs-modal')">✕</button>
          </div>
          <div class="terminal-window" id="logs-modal-content" style="height:380px;"></div>
        </div>
      </div>
    `;
  },

  async mount() {
    this.loadProjects();
  },

  async loadProjects() {
    const tbody = document.getElementById('projects-tbody');
    try {
      this.projectsData = await API.getProjects();
      if (this.projectsData.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9">No projects created. Click '+ Create Project' to deploy an app.</td></tr>`;
        return;
      }
      tbody.innerHTML = this.projectsData.map(p => {
        const lastDep = p.last_deployment 
          ? `#${p.last_deployment.commit_hash} (${p.last_deployment.status})` 
          : 'None';
        const serviceStatus = p.service_name ? `${p.service_name} (${p.status})` : p.status;

        return `
          <tr>
            <td><strong>${p.name}</strong><br><small style="color:var(--text-muted)">${p.repo_url || 'Local'}</small></td>
            <td><span style="font-size:12px; font-weight:600; background:rgba(255,255,255,0.06); padding:3px 8px; border-radius:4px;">${p.app_type}</span></td>
            <td><span class="status-pill ${p.status}">${p.status}</span></td>
            <td>${p.domain ? `🌐 ${p.domain}` : '-'}</td>
            <td>:${p.port || '8000'}</td>
            <td><code>${p.branch}</code></td>
            <td><small>${lastDep}</small></td>
            <td><small>${serviceStatus}</small></td>
            <td>
              <div style="display:flex; flex-wrap:wrap; gap:4px;">
                <button class="btn btn-secondary btn-sm" onclick="ProjectsView.viewDetails(${p.id})">👁️ View</button>
                <button class="btn btn-secondary btn-sm" onclick="ProjectsView.openEditModal(${p.id})">✏️ Edit</button>
                <button class="btn btn-primary btn-sm" onclick="ProjectsView.deployProject(${p.id})">🚀 Deploy</button>
                <button class="btn btn-secondary btn-sm" onclick="ProjectsView.restartProject(${p.id})">🔄 Restart</button>
                <button class="btn btn-danger btn-sm" onclick="ProjectsView.stopProject(${p.id})">⏹️ Stop</button>
                <button class="btn btn-secondary btn-sm" onclick="ProjectsView.viewLogs(${p.id})">📋 Logs</button>
              </div>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="9" style="color:var(--accent-rose)">Failed to load projects: ${err.message}</td></tr>`;
    }
  },

  openModal(id) {
    document.getElementById(id).style.display = 'flex';
  },

  closeModal(id) {
    document.getElementById(id).style.display = 'none';
  },

  openCreateModal() {
    this.openModal('proj-create-modal');
  },

  onAppTypeChange(prefix) {
    const appType = document.getElementById(`${prefix}-app-type`).value;
    const buildInput = document.getElementById(`${prefix}-cmd-build`);
    const startInput = document.getElementById(`${prefix}-cmd-start`);

    if (appType === 'Static HTML/CSS/JavaScript') {
      if (buildInput) buildInput.value = "echo 'Static assets ready'";
      if (startInput) startInput.value = "python3 -m http.server 8000";
    } else if (appType === 'Python FastAPI') {
      if (buildInput) buildInput.value = "pip install -r requirements.txt";
      if (startInput) startInput.value = "uvicorn main:app --host 0.0.0.0 --port 8000";
    } else if (appType === 'Python Flask') {
      if (buildInput) buildInput.value = "pip install -r requirements.txt";
      if (startInput) startInput.value = "flask run --host=0.0.0.0 --port=8000";
    }
  },

  async handleCreate(e) {
    e.preventDefault();
    const payload = {
      name: document.getElementById('c-name').value,
      app_type: document.getElementById('c-app-type').value,
      repo_url: document.getElementById('c-repo').value,
      branch: document.getElementById('c-branch').value,
      port: parseInt(document.getElementById('c-port').value),
      domain: document.getElementById('c-domain').value,
      deployment_directory: document.getElementById('c-dir').value,
      build_command: document.getElementById('c-cmd-build').value,
      start_command: document.getElementById('c-cmd-start').value
    };

    try {
      await API.createProject(payload);
      this.closeModal('proj-create-modal');
      this.loadProjects();
    } catch (err) {
      alert(`Create failed: ${err.message}`);
    }
  },

  viewDetails(id) {
    const p = this.projectsData.find(item => item.id === id);
    if (!p) return;
    document.getElementById('v-title').innerText = `Project Specifications: ${p.name}`;
    document.getElementById('v-content').innerHTML = `
      <p><strong>App Type:</strong> ${p.app_type}</p>
      <p><strong>Status:</strong> <span class="status-pill ${p.status}">${p.status}</span></p>
      <p><strong>Repository:</strong> <code>${p.repo_url || 'N/A'}</code> (Branch: <code>${p.branch}</code>)</p>
      <p><strong>Port Binding:</strong> :${p.port || 8000}</p>
      <p><strong>Domain Mapping:</strong> ${p.domain || 'None'}</p>
      <p><strong>Deployment Directory:</strong> <code>${p.deployment_directory}</code></p>
      <p><strong>Service Unit Name:</strong> <code>${p.service_name}</code></p>
      <p><strong>Start Command:</strong> <code>${p.start_command}</code></p>
      <p><strong>Build Command:</strong> <code>${p.build_command}</code></p>
      <p><strong>Created Date:</strong> ${new Date(p.created_at).toLocaleString()}</p>
    `;
    this.openModal('proj-view-modal');
  },

  openEditModal(id) {
    const p = this.projectsData.find(item => item.id === id);
    if (!p) return;
    document.getElementById('e-id').value = p.id;
    document.getElementById('e-name').value = p.name;
    document.getElementById('e-branch').value = p.branch;
    document.getElementById('e-port').value = p.port || 8000;
    document.getElementById('e-domain').value = p.domain || '';
    document.getElementById('e-cmd-start').value = p.start_command || '';
    this.openModal('proj-edit-modal');
  },

  async handleEdit(e) {
    e.preventDefault();
    const id = document.getElementById('e-id').value;
    const payload = {
      name: document.getElementById('e-name').value,
      branch: document.getElementById('e-branch').value,
      port: parseInt(document.getElementById('e-port').value),
      domain: document.getElementById('e-domain').value,
      start_command: document.getElementById('e-cmd-start').value
    };

    try {
      await API.updateProject(id, payload);
      this.closeModal('proj-edit-modal');
      this.loadProjects();
    } catch (err) {
      alert(`Update failed: ${err.message}`);
    }
  },

  async deployProject(id) {
    try {
      await API.triggerDeploy(id);
      alert('Deployment queued successfully!');
      this.loadProjects();
    } catch (err) {
      alert(`Deploy failed: ${err.message}`);
    }
  },

  async restartProject(id) {
    try {
      await API.restartProject(id);
      this.loadProjects();
    } catch (err) {
      alert(`Restart failed: ${err.message}`);
    }
  },

  async stopProject(id) {
    try {
      await API.stopProject(id);
      this.loadProjects();
    } catch (err) {
      alert(`Stop failed: ${err.message}`);
    }
  },

  async viewLogs(id) {
    try {
      const logsData = await API.getProjectLogs(id);
      document.getElementById('logs-modal-title').innerText = `Logs: ${logsData.project_name}`;
      document.getElementById('logs-modal-content').innerText = logsData.logs;
      this.openModal('proj-logs-modal');
    } catch (err) {
      alert(`Failed to fetch logs: ${err.message}`);
    }
  }
};
