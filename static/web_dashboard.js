let allServers = {};
let currentView = 'dashboard';
let currentGame = null;

function showDashboard() {
    currentView = 'dashboard';
    currentGame = null;
    document.getElementById('dashboard-view').classList.add('active');
    document.getElementById('game-detail-view').classList.remove('active');
    updateBreadcrumb();
    renderDashboard();
}

function showGameDetail(gameName) {
    currentView = 'game-detail';
    currentGame = gameName;
    document.getElementById('dashboard-view').classList.remove('active');
    document.getElementById('game-detail-view').classList.add('active');
    updateBreadcrumb();
    renderGameDetail(gameName);
}

function updateBreadcrumb() {
    const breadcrumb = document.getElementById('breadcrumb');
    if (currentView === 'dashboard') {
        breadcrumb.innerHTML = '<span>Dashboard</span>';
        return;
    }
    breadcrumb.innerHTML = '<a onclick="showDashboard()">Dashboard</a> <span>></span> <span>' + currentGame + '</span>';
}

async function loadServers() {
    try {
        const response = await fetch('/api/servers?_=' + Date.now(), { credentials: 'include', cache: 'no-store' });
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await response.json();
        if (Array.isArray(data.servers)) {
            const converted = {};
            data.servers.forEach(server => {
                const sid = server.id || server.server_id || String(Object.keys(converted).length);
                converted[sid] = server;
            });
            allServers = converted;
        } else {
            allServers = data.servers || {};
        }

        updateStats();
        if (currentView === 'dashboard') {
            renderDashboard();
        } else if (currentView === 'game-detail') {
            renderGameDetail(currentGame);
        }
    } catch (error) {
        console.error('Error loading servers:', error);
    }
}

function updateStats() {
    const servers = Object.values(allServers);
    const totalServers = servers.length;
    const onlineServers = servers.filter(s => s.is_running).length;
    const offlineServers = totalServers - onlineServers;
    const totalGames = new Set(servers.map(s => s.game || 'Unknown')).size;

    document.getElementById('stat-total').textContent = totalServers;
    document.getElementById('stat-online').textContent = onlineServers;
    document.getElementById('stat-offline').textContent = offlineServers;
    document.getElementById('stat-games').textContent = totalGames;
}

function renderDashboard() {
    const grid = document.getElementById('game-grid');
    const servers = Object.values(allServers);

    if (servers.length === 0) {
        grid.innerHTML = '<div class="empty-state"><div class="empty-state-icon">No Servers</div><p>Create your first server in the desktop app</p></div>';
        return;
    }

    const gameGroups = {};
    servers.forEach(server => {
        const game = server.game || 'Unknown';
        if (!gameGroups[game]) {
            gameGroups[game] = { icon: server.icon || '*', servers: [] };
        }
        gameGroups[game].servers.push(server);
    });

    let html = '';
    Object.keys(gameGroups).sort().forEach(gameName => {
        const group = gameGroups[gameName];
        const totalCount = group.servers.length;
        const onlineCount = group.servers.filter(s => s.is_running).length;
        const offlineCount = totalCount - onlineCount;

        html += '<div class="game-card" data-game="' + encodeURIComponent(gameName) + '" onclick="showGameDetail(decodeURIComponent(this.dataset.game))">' +
                '<div class="game-header"><div class="game-icon">' + group.icon + '</div><div class="game-name">' + gameName + '</div></div>' +
                '<div class="game-stats">' +
                '<div class="game-stat-item"><div class="game-stat-value online">' + onlineCount + '</div><div class="game-stat-label">Online</div></div>' +
                '<div class="game-stat-item"><div class="game-stat-value offline">' + offlineCount + '</div><div class="game-stat-label">Offline</div></div>' +
                '<div class="game-stat-item"><div class="game-stat-value" style="color: #00d4ff;">' + totalCount + '</div><div class="game-stat-label">Total</div></div>' +
                '</div></div>';
    });

    grid.innerHTML = html;
}

function renderGameDetail(gameName) {
    const list = document.getElementById('server-list');
    const servers = Object.entries(allServers)
        .filter(([, server]) => (server.game || 'Unknown') === gameName)
        .sort((a, b) => (a[1].name || '').localeCompare(b[1].name || ''));

    let html = '';
    servers.forEach(([serverId, server]) => {
        const status = server.is_running ? 'online' : 'offline';
        const statusText = server.is_running ? 'ONLINE' : 'OFFLINE';

        html += '<div class="server-card ' + status + '">' +
                '<div class="server-header"><div class="server-info"><h3>' + (server.name || 'Server') + '</h3>' +
                '<div class="server-meta">' + (server.icon || '*') + ' ' + (server.game || 'Unknown') + '</div></div>' +
                '<div class="status-badge ' + status + '">' + statusText + '</div></div>' +
                '<div class="server-details">' +
                '<div class="detail-item"><div class="detail-label">Port</div><div class="detail-value">' + (server.port || '-') + '</div></div>' +
                '<div class="detail-item"><div class="detail-label">Max Players</div><div class="detail-value">' + (server.max_players || '-') + '</div></div>';

        if (server.map_name) {
            html += '<div class="detail-item"><div class="detail-label">Map</div><div class="detail-value">' + server.map_name + '</div></div>';
        }

        if (server.is_running && server.resources) {
            html += '<div class="detail-item"><div class="detail-label">CPU</div><div class="detail-value">' + Number(server.resources.cpu || 0).toFixed(0) + '%</div></div>' +
                    '<div class="detail-item"><div class="detail-label">RAM</div><div class="detail-value">' + Number(server.resources.ram_gb || 0).toFixed(1) + ' GB</div></div>' +
                    '<div class="detail-item"><div class="detail-label">Uptime</div><div class="detail-value">' + (server.uptime || '-') + '</div></div>';
        }

        html += '</div><div class="server-actions">';
        if (!server.is_running) {
            html += '<button class="btn start" onclick="serverAction(\'' + serverId + '\', \'start\')">Start</button>';
        } else {
            html += '<button class="btn stop" onclick="serverAction(\'' + serverId + '\', \'stop\')">Stop</button>';
        }
        html += '<button class="btn restart" onclick="serverAction(\'' + serverId + '\', \'restart\')">Restart</button>' +
                '<button class="btn backup" onclick="serverAction(\'' + serverId + '\', \'backup\')">Backup</button></div></div>';
    });

    list.innerHTML = html;
}

async function serverAction(serverId, action) {
    try {
        const response = await fetch('/api/server/' + serverId + '/' + action, { method: 'POST', credentials: 'include' });
        const data = await response.json();
        if (data.success) {
            setTimeout(loadServers, 1000);
        }
    } catch (error) {
        console.error('Action error:', error);
    }
}

function startAutoRefresh() {
    // Auto refresh disabled on user request to prevent flicker.
}

updateBreadcrumb();
loadServers();
