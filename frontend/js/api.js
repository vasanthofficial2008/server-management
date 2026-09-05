/**
 * ServerPilot REST API Client
 */
const API = {
  baseUrl: '/api',

  getToken() {
    return localStorage.getItem('serverpilot_token');
  },

  setToken(token) {
    localStorage.setItem('serverpilot_token', token);
  },

  clearToken() {
    localStorage.removeItem('serverpilot_token');
  },

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const token = this.getToken();

    const headers = {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...options.headers
    };

    try {
      const response = await fetch(url, { ...options, headers });
      
      if (response.status === 401 && !endpoint.includes('/auth/login')) {
        this.clearToken();
        if (window.location.pathname !== '/login.html') {
          window.location.href = '/login.html';
        }
        throw new Error('Unauthorized session. Please log in.');
      }

      if (response.status === 204) {
        return null;
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'API Request Failed');
      }
      return data;
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  },

  // Auth Endpoints
  login(username, password) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
  },

  async logout() {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } catch (err) {
      // Ignore network errors on logout
    } finally {
      this.clearToken();
      window.location.href = '/login.html';
    }
  },

  getMe() {
    return this.request('/auth/me');
  },

  // Health
  getHealth() {
    return this.request('/health');
  },

  // Projects
  getProjects() {
    return this.request('/projects');
  },

  getProject(id) {
    return this.request(`/projects/${id}`);
  },

  createProject(project) {
    return this.request('/projects', {
      method: 'POST',
      body: JSON.stringify(project)
    });
  },

  updateProject(id, project) {
    return this.request(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(project)
    });
  },

  deleteProject(id) {
    return this.request(`/projects/${id}`, {
      method: 'DELETE'
    });
  },

  restartProject(id) {
    return this.request(`/projects/${id}/restart`, {
      method: 'POST'
    });
  },

  stopProject(id) {
    return this.request(`/projects/${id}/stop`, {
      method: 'POST'
    });
  },

  getProjectLogs(id) {
    return this.request(`/projects/${id}/logs`);
  },

  triggerDeploy(projectId, commitHash = 'head', commitMessage = 'Manual trigger deployment') {
    return this.request(`/projects/${projectId}/deploy`, {
      method: 'POST'
    });
  },

  // Services
  getServices() {
    return this.request('/services');
  },

  serviceAction(id, action) {
    return this.request(`/services/${id}/action`, {
      method: 'POST',
      body: JSON.stringify({ action })
    });
  },

  // Deployments
  getDeployments() {
    return this.request('/deployments');
  },

  // Domains
  getDomains() {
    return this.request('/domains');
  },

  createDomain(domain) {
    return this.request('/domains', {
      method: 'POST',
      body: JSON.stringify(domain)
    });
  },

  deleteDomain(id) {
    return this.request(`/domains/${id}`, {
      method: 'DELETE'
    });
  },

  // Server Stats & Audit Logs
  getServerStats() {
    return this.request('/server/stats');
  },

  getProcesses() {
    return this.request('/server/processes');
  },

  getEvents() {
    return this.request('/server/events');
  },

  getAuditLogs() {
    return this.request('/server/audit-logs');
  },

  // Settings
  getSettings() {
    return this.request('/settings');
  },

  updateSetting(key, value, category = 'general') {
    return this.request('/settings', {
      method: 'POST',
      body: JSON.stringify({ key, value, category })
    });
  },

  // Terminal Sessions
  createTerminalSession(cols = 80, rows = 24) {
    return this.request('/terminal/session', {
      method: 'POST',
      body: JSON.stringify({ cols, rows })
    });
  },

  getTerminalSessions() {
    return this.request('/terminal/sessions');
  },

  closeTerminalSession(sessionId) {
    return this.request(`/terminal/session/${sessionId}`, {
      method: 'DELETE'
    });
  }
};
