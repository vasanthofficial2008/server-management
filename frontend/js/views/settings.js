const SettingsView = {
  async render() {
    return `
      <div class="card" style="max-width:720px;">
        <div class="card-header">
          <h3 class="card-title">ServerPilot Platform Configuration</h3>
        </div>
        <form onsubmit="SettingsView.handleSave(event)">
          <div class="form-group">
            <label class="form-label">Control Panel Title</label>
            <input type="text" id="set-title" class="form-input" value="ServerPilot Control Panel">
          </div>
          <div class="form-group">
            <label class="form-label">SSL Certificate Authority</label>
            <select id="set-ssl" class="form-select">
              <option value="Let's Encrypt / Certbot">Let's Encrypt (Production)</option>
              <option value="Self-Signed Internal">Self-Signed Internal</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Automatic System Health Check Interval</label>
            <select id="set-check" class="form-select">
              <option value="15s">Every 15 Seconds</option>
              <option value="30s">Every 30 Seconds</option>
              <option value="60s">Every 1 Minute</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" style="display:flex; align-items:center; gap:8px;">
              <input type="checkbox" id="set-autoupdate" checked style="width:auto;"> Enable background security updates
            </label>
          </div>
          <div style="display:flex; justify-content:flex-end; gap:12px; margin-top:32px;">
            <button type="submit" class="btn btn-primary">Save Settings</button>
          </div>
        </form>
      </div>
    `;
  },

  async mount() {
    try {
      const settings = await API.getSettings();
      settings.forEach(s => {
        if (s.key === 'site_title') {
          const el = document.getElementById('set-title');
          if (el) el.value = s.value;
        }
      });
    } catch (err) {
      console.warn('Failed to load settings:', err);
    }
  },

  async handleSave(e) {
    e.preventDefault();
    const titleVal = document.getElementById('set-title').value;
    try {
      await API.updateSetting('site_title', titleVal, 'general');
      alert('Settings updated successfully!');
    } catch (err) {
      alert(`Save failed: ${err.message}`);
    }
  }
};
