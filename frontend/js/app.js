/**
 * ServerPilot Main SPA Application Host & Client Router
 */
const routes = {
  '/dashboard': DashboardView,
  '/projects': ProjectsView,
  '/services': ServicesView,
  '/deployments': DeploymentsView,
  '/terminal': TerminalView,
  '/logs': LogsView,
  '/domains': DomainsView,
  '/server': ServerView,
  '/settings': SettingsView
};

let currentView = null;

async function navigateTo(path) {
  // Enforce frontend route protection
  if (!API.getToken()) {
    window.location.href = '/login.html';
    return;
  }

  if (!routes[path]) {
    path = '/dashboard';
  }

  // Highlight active sidebar navigation link
  document.querySelectorAll('.nav-item').forEach(item => {
    const link = item.querySelector('a');
    if (link && link.getAttribute('href') === `#${path}`) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Update Page Title
  const titleMap = {
    '/dashboard': 'ServerPilot Dashboard',
    '/projects': 'Project & App Management',
    '/services': 'System Services & Daemons',
    '/deployments': 'Deployment Pipeline & Logs',
    '/terminal': 'Web Terminal Console',
    '/logs': 'Real-Time System & Audit Logs',
    '/domains': 'Domain Routing & SSL',
    '/server': 'Hardware Metrics & Processes',
    '/settings': 'System Settings'
  };
  document.getElementById('page-title').innerText = titleMap[path] || 'ServerPilot Control Panel';

  // Unmount active view if cleanup is needed
  if (currentView && typeof currentView.unmount === 'function') {
    currentView.unmount();
  }

  // Render and mount new view
  currentView = routes[path];
  const contentArea = document.getElementById('content-area');
  contentArea.innerHTML = await currentView.render();
  
  if (typeof currentView.mount === 'function') {
    await currentView.mount();
  }
}

function handleHashChange() {
  const hash = window.location.hash.slice(1) || '/dashboard';
  navigateTo(hash);
}

window.addEventListener('hashchange', handleHashChange);

window.addEventListener('DOMContentLoaded', () => {
  // Mobile drawer sidebar toggle
  const sidebar = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('mobile-toggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });
  }

  // Check auth user
  if (API.getToken()) {
    API.getMe().then(user => {
      const userBadge = document.getElementById('user-badge-name');
      if (userBadge) userBadge.innerText = user.username;
    }).catch(() => {
      API.clearToken();
      window.location.href = '/login.html';
    });
  } else {
    window.location.href = '/login.html';
  }

  // Load initial view
  handleHashChange();
});
