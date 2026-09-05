const TerminalView = {
  sessions: [],
  activeSessionId: null,
  activeWs: null,
  resizeObserver: null,

  async render() {
    return `
      <div class="card" style="display:flex; flex-direction:column; gap:16px;">
        <!-- Administrative Capability Security Warning Banner -->
        <div style="background:rgba(245, 158, 11, 0.12); border:1px solid rgba(245, 158, 11, 0.3); border-radius:8px; padding:12px 16px; display:flex; align-items:center; gap:12px;">
          <span style="font-size:22px;">⚠️</span>
          <div>
            <strong style="color:var(--accent-amber); font-size:14px;">ADMINISTRATIVE CAPABILITIES WARNING</strong>
            <p style="margin:2px 0 0 0; color:var(--text-muted); font-size:12px;">
              This web terminal provides interactive shell execution under restricted operating-system user <code style="color:var(--accent-emerald)">serverpilot-term</code>. Unrestricted root access is strictly disabled for system security. All terminal sessions and executed commands are logged in <strong>Audit Logs</strong>.
            </p>
          </div>
        </div>

        <!-- Terminal Header & Session Tab Bar -->
        <div class="card-header" style="flex-wrap:wrap; gap:12px; padding-bottom:8px; border-bottom:1px solid var(--border-color);">
          <div style="display:flex; align-items:center; gap:8px;" id="terminal-tabs-container">
            <span style="color:var(--text-muted); font-size:13px;">Active Sessions:</span>
            <div id="terminal-tabs" style="display:flex; gap:6px;"></div>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-primary btn-sm" onclick="TerminalView.createNewSession()">➕ New Terminal Session</button>
            <button class="btn btn-danger btn-sm" onclick="TerminalView.closeCurrentSession()" id="close-session-btn" style="display:none;">✕ Close Session</button>
          </div>
        </div>

        <!-- Terminal Screen Window -->
        <div class="terminal-window" id="terminal-screen" tabindex="0" style="height:480px; font-family:'JetBrains Mono', monospace; font-size:13px; line-height:1.4; outline:none; cursor:text; overflow-y:auto; background:#0d1117; color:#c9d1d9; border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:16px;">
          <div style="color:var(--text-dim); text-align:center; margin-top:180px;">
            No active terminal session. Click <strong>"➕ New Terminal Session"</strong> to spawn a session.
          </div>
        </div>

        <!-- Terminal Helper Bar -->
        <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; color:var(--text-muted);">
          <div style="display:flex; gap:16px;">
            <span>Restricted OS User: <strong style="color:var(--accent-emerald)" id="term-user-badge">serverpilot-term</strong></span>
            <span>Session ID: <code id="term-id-badge">None</code></span>
          </div>
          <div style="display:flex; gap:8px;">
            <button class="btn btn-secondary btn-sm" onclick="TerminalView.sendControlKey('ctrl-c')">Ctrl+C</button>
            <button class="btn btn-secondary btn-sm" onclick="TerminalView.sendControlKey('clear')">Clear Screen</button>
          </div>
        </div>
      </div>
    `;
  },

  async mount() {
    await this.loadSessions();
    this.setupKeyboardListeners();
    this.setupResizeListener();
  },

  unmount() {
    if (this.activeWs) {
      this.activeWs.close();
      this.activeWs = null;
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
  },

  async loadSessions() {
    try {
      this.sessions = await API.request('/terminal/sessions');
      this.renderTabs();

      if (this.sessions.length > 0) {
        if (!this.activeSessionId || !this.sessions.find(s => s.session_id === this.activeSessionId)) {
          this.switchSession(this.sessions[0].session_id);
        }
      } else {
        this.activeSessionId = null;
        document.getElementById('close-session-btn').style.display = 'none';
        document.getElementById('term-id-badge').innerText = 'None';
        document.getElementById('terminal-screen').innerHTML = `
          <div style="color:var(--text-dim); text-align:center; margin-top:180px;">
            No active terminal session. Click <strong>"➕ New Terminal Session"</strong> to spawn a session.
          </div>
        `;
      }
    } catch (err) {
      console.error('Error loading terminal sessions:', err);
    }
  },

  renderTabs() {
    const tabsContainer = document.getElementById('terminal-tabs');
    if (!tabsContainer) return;

    if (this.sessions.length === 0) {
      tabsContainer.innerHTML = '<span style="color:var(--text-dim); font-size:12px;">No sessions</span>';
      return;
    }

    tabsContainer.innerHTML = this.sessions.map(s => {
      const isActive = s.session_id === this.activeSessionId;
      return `
        <button class="btn btn-sm ${isActive ? 'btn-primary' : 'btn-secondary'}" onclick="TerminalView.switchSession('${s.session_id}')" style="font-family:monospace; font-size:12px;">
          💻 ${s.session_id}
        </button>
      `;
    }).join('');
  },

  async createNewSession() {
    try {
      const session = await API.request('/terminal/session', {
        method: 'POST',
        body: JSON.stringify({ cols: 80, rows: 24 })
      });
      await this.loadSessions();
      this.switchSession(session.session_id);
    } catch (err) {
      alert(`Failed to create terminal session: ${err.message}`);
    }
  },

  async closeCurrentSession() {
    if (!this.activeSessionId) return;
    try {
      await API.request(`/terminal/session/${this.activeSessionId}`, { method: 'DELETE' });
      this.activeSessionId = null;
      await this.loadSessions();
    } catch (err) {
      alert(`Failed to close session: ${err.message}`);
    }
  },

  switchSession(sessionId) {
    if (this.activeWs) {
      this.activeWs.close();
      this.activeWs = null;
    }

    this.activeSessionId = sessionId;
    const session = this.sessions.find(s => s.session_id === sessionId);
    if (!session) return;

    document.getElementById('close-session-btn').style.display = 'inline-block';
    document.getElementById('term-id-badge').innerText = session.session_id;
    document.getElementById('term-user-badge').innerText = session.os_user || 'serverpilot-term';
    
    this.renderTabs();

    const screen = document.getElementById('terminal-screen');
    screen.innerHTML = '';
    screen.focus();

    // Connect WebSocket
    const token = API.getToken();
    const wsUrl = `/ws/terminal/${sessionId}?token=${encodeURIComponent(token)}`;

    this.activeWs = new WSManager(wsUrl, (data) => {
      this.handleTerminalOutput(data);
    });
    this.activeWs.connect();
    this.sendResize();
  },

  handleTerminalOutput(data) {
    const screen = document.getElementById('terminal-screen');
    if (!screen) return;

    const raw = typeof data === 'string' ? data : (data.data || '');
    
    // Clear screen escape sequence check
    if (raw.includes('\033[2J') || raw.includes('\033[H')) {
      screen.innerText = '';
    }

    // Append text node
    screen.appendChild(document.createTextNode(raw));
    screen.scrollTop = screen.scrollHeight;
  },

  setupKeyboardListeners() {
    const screen = document.getElementById('terminal-screen');
    if (!screen) return;

    screen.addEventListener('keydown', (e) => {
      if (!this.activeWs || !this.activeSessionId) return;

      // Intercept Ctrl+C
      if (e.ctrlKey && e.key === 'c') {
        e.preventDefault();
        this.sendInput('\x03');
        return;
      }

      // Intercept Backspace
      if (e.key === 'Backspace') {
        e.preventDefault();
        this.sendInput('\x08');
        return;
      }

      // Intercept Enter
      if (e.key === 'Enter') {
        e.preventDefault();
        this.sendInput('\r');
        return;
      }

      // Intercept Tab
      if (e.key === 'Tab') {
        e.preventDefault();
        this.sendInput('\t');
        return;
      }

      // Intercept Arrow Keys
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        this.sendInput('\033[A');
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        this.sendInput('\033[B');
        return;
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        this.sendInput('\033[C');
        return;
      }
      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        this.sendInput('\033[D');
        return;
      }

      // Printable single keys
      if (e.key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
        e.preventDefault();
        this.sendInput(e.key);
      }
    });
  },

  setupResizeListener() {
    const screen = document.getElementById('terminal-screen');
    if (!screen) return;

    this.resizeObserver = new ResizeObserver(() => {
      this.sendResize();
    });
    this.resizeObserver.observe(screen);
  },

  sendResize() {
    if (!this.activeWs || !this.activeSessionId) return;
    const screen = document.getElementById('terminal-screen');
    if (!screen) return;

    // Estimate cols & rows based on screen width/height
    const cols = Math.max(20, Math.floor(screen.clientWidth / 8.5));
    const rows = Math.max(5, Math.floor(screen.clientHeight / 18));

    this.activeWs.send(JSON.stringify({
      type: 'resize',
      cols: cols,
      rows: rows
    }));
  },

  sendInput(charData) {
    if (!this.activeWs) return;
    this.activeWs.send(JSON.stringify({
      type: 'input',
      data: charData
    }));
  },

  sendControlKey(action) {
    if (action === 'ctrl-c') {
      this.sendInput('\x03');
    } else if (action === 'clear') {
      const screen = document.getElementById('terminal-screen');
      if (screen) screen.innerText = '';
      this.sendInput('\x0c');
    }
  }
};
