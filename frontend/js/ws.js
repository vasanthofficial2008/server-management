/**
 * ServerPilot WebSocket Connection Manager
 */
class WSManager {
  constructor(endpoint, onMessage) {
    this.endpoint = endpoint;
    this.onMessage = onMessage;
    this.socket = null;
    this.isClosed = false;
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}${this.endpoint}`;

    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.log(`[WebSocket] Connected to ${this.endpoint}`);
    };

    this.socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (this.onMessage) this.onMessage(data);
      } catch (err) {
        if (this.onMessage) this.onMessage(event.data);
      }
    };

    this.socket.onerror = (err) => {
      console.warn(`[WebSocket Error] ${this.endpoint}:`, err);
    };

    this.socket.onclose = () => {
      if (!this.isClosed) {
        setTimeout(() => this.connect(), 3000);
      }
    };
  }

  send(message) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      if (typeof message === 'object') {
        this.socket.send(JSON.stringify(message));
      } else {
        this.socket.send(message);
      }
    }
  }

  close() {
    this.isClosed = true;
    if (this.socket) {
      this.socket.close();
    }
  }
}
