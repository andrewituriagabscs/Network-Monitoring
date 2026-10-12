<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ping Monitoring System</title>
    <link rel="stylesheet" href="/style.css">
</head>
<body>
    <div class="app-shell">
        <aside class="sidebar" aria-label="Main navigation">
            <div class="brand"><span class="brand-mark" aria-hidden="true">P</span><span>PingWatch</span></div>
            <nav class="nav-list">
                <button class="nav-item active" type="button" data-view="dashboard" aria-current="page"><span class="nav-icon" aria-hidden="true">⌂</span><span>Dashboard</span></button>
                <button class="nav-item" type="button" data-view="monitor"><span class="nav-icon" aria-hidden="true">◉</span><span>Monitor PCs</span></button>
                <button class="nav-item" type="button" data-view="alerts"><span class="nav-icon" aria-hidden="true">!</span><span>Alerts</span></button>
                <button class="nav-item" type="button" data-view="reports"><span class="nav-icon" aria-hidden="true">▤</span><span>Ping Records</span></button>
                <button class="nav-item" type="button" data-view="ml-insights"><span class="nav-icon" aria-hidden="true">⌁</span><span>ML Insights</span></button>
            </nav>
            <nav class="nav-list nav-list-bottom" aria-label="Preferences">
                <button class="nav-item" type="button" data-view="settings"><span class="nav-icon" aria-hidden="true">⚙</span><span>Settings</span></button>
                <button class="nav-item" type="button" data-view="about"><span class="nav-icon" aria-hidden="true">?</span><span>About</span></button>
            </nav>
        </aside>

        <main class="page">
            <section class="view-panel active" data-panel="dashboard">
                <header><div><p class="eyebrow">ICMP network status</p><h1>Ping Monitoring System<small id="building-name" style="font-size: 0.6em; color: #666; display: block; margin-top: 0.25em;">Loading location...</small></h1><p>Updated <span id="dashboard-updated">Waiting for live samples</span></p></div><button class="refresh-button" type="button" onclick="refreshStatus()">↻ <span>Refresh</span></button></header>
                <section class="summary-cards">
                    <div class="card"><h2>Saved PCs</h2><p id="saved-count">0</p></div>
                    <div class="card"><h2>Monitoring</h2><p id="active-count">0</p></div>
                    <div class="card"><h2>Network status</h2><p id="network-health">Waiting</p></div>
                    <div class="card"><h2>Open alerts</h2><p id="open-alerts">0</p></div>
                </section>
                <section class="metrics"><h2>Ping metrics</h2><div class="metric-grid">
                    <div class="metric-card"><strong>Average Latency</strong><span id="metric-average-latency">Loading</span><small>Live ping</small></div><div class="metric-card"><strong>Reachable</strong><span id="metric-reachable">0</span><small>Latest ping per PC</small></div><div class="metric-card"><strong>Monitoring</strong><span id="metric-monitoring">0</span><small>Selected PCs</small></div><div class="metric-card"><strong>Ping Samples</strong><span id="metric-samples">0</span><small>Recent records</small></div>
                </div></section>
                <section class="ml-overview"><div class="section-heading"><div><p class="eyebrow">Model readiness</p><h2>Machine learning</h2></div><span class="status-pill status-normal">ICMP only</span></div>
                    <div class="summary-cards ml-cards"><div class="card"><h2>Model set</h2><p id="dashboard-ml-model" class="small-value">Isolation Forest, GRU, XGBoost</p><small id="dashboard-ml-version">Loading readiness</small></div><div class="card"><h2>Valid ping samples</h2><p id="dashboard-valid-samples">0</p><small>Available for training</small></div><div class="card"><h2>Reviewed labels</h2><p id="dashboard-labeled-samples">0</p><small>For supervised classification</small></div></div>
                </section>
                <section class="alerts"><h2>Recent alerts</h2><table><thead><tr><th>Time</th><th>PC</th><th>Ping event</th></tr></thead><tbody id="alert-rows"><tr><td colspan="3">Waiting for live status...</td></tr></tbody></table><div id="alerts-pagination" style="display: flex; gap: 8px; justify-content: center; align-items: center; margin-top: 16px;"></div></section>
            </section>

            <section class="view-panel data-panel" data-panel="monitor" hidden>
                <div class="monitor-heading"><div><p class="eyebrow">Local network</p><h1>Monitor Devices</h1><p class="panel-intro">Discover responding devices (PCs and phones), select the ones to monitor, and start ping checks.</p></div><button class="refresh-button" type="button" onclick="pollNow(this)">↻ <span>Ping now</span></button></div>
                <section class="discovery-controls">
                    <label for="subnet-input">Subnet to discover</label>
                    <div class="discovery-row"><input id="subnet-input" type="text" inputmode="decimal" aria-label="Local IPv4 subnet in CIDR notation"><button class="refresh-button" id="discover-button" type="button" onclick="discoverHosts(this)">⌕ <span>Discover PCs</span></button><button class="refresh-button" id="auto-discover-toggle" type="button" onclick="toggleAutoDiscover(this)" style="display: none;">⟳ <span>Auto refresh: off</span></button></div>
                    <div class="discovery-options">
                        <div><label for="discovery-limit">Discover up to:</label><input id="discovery-limit" type="number" value="20" min="1" max="999" style="width: 60px; padding: 6px;"><select id="limit-presets" onchange="document.querySelector('#discovery-limit').value = this.value;" style="padding: 6px; margin-left: 8px;"><option value="">Presets:</option><option value="10">10</option><option value="20">20</option><option value="50">50</option><option value="100">100</option><option value="256">All</option></select></div>
                        <div style="margin-top: 8px;"><label><input type="checkbox" id="show-phones-toggle" checked onchange="filterDiscoveryRows()"> Show phones (📱)</label></div>
                    </div>
                    <p id="discovery-status" role="status"></p>
                </section>
                <section id="discovery-section" hidden><div class="section-heading"><h2>Available Devices</h2><button class="refresh-button" type="button" onclick="addSelectedHosts()">＋ <span>Add selected</span></button></div><div class="table-wrap"><table><thead><tr><th>Select</th><th>Device / hostname</th><th>IPv4 address</th><th>Device Type</th></tr></thead><tbody id="discovered-rows"></tbody></table></div></section>
                <section><div class="section-heading"><h2>Selected Devices</h2><span id="monitor-summary"></span></div>
                    <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center;">
                        <input id="monitor-search" type="text" placeholder="Search by IP or hostname..." style="flex: 1; min-width: 200px; padding: 8px; border: 1px solid #ccc; border-radius: 4px;" onkeyup="applySearchAndPagination()">
                        <select id="device-type-filter" style="padding: 8px; border: 1px solid #ccc; border-radius: 4px;" onchange="applySearchAndPagination()">
                            <option value="">All devices</option>
                            <option value="pc">💻 PCs only</option>
                            <option value="phone">📱 Phones only</option>
                            <option value="switch">🔀 Switches only</option>
                        </select>
                        <button class="refresh-button" type="button" onclick="clearMonitorSearch()" style="padding: 6px 12px;">✕ <span>Clear</span></button>
                        <button class="refresh-button" type="button" onclick="reclassifyAllDevices()" style="padding: 6px 12px; background: #2196F3;" title="Re-detect PC / Phone / Switch for all monitored devices">🔀 <span>Re-detect types</span></button>
                        <button class="refresh-button" type="button" onclick="bulkStartAll()" style="padding: 6px 12px; background: #4CAF50;">▶ <span>Start All</span></button>
                        <button class="refresh-button" type="button" onclick="bulkPauseAll()" style="padding: 6px 12px; background: #FF9800;">⏸ <span>Pause All</span></button>
                    </div>
                    <div class="chart-card"><div class="chart-heading"><div><h2>Ping latency</h2><small>Median of five ICMP replies per check; Windows may report values as &lt;1 ms.</small></div><label for="chart-device">Device</label><select id="chart-device" aria-label="Select device for latency chart" onchange="drawPingChart()"></select></div><canvas id="ping-chart" height="220"></canvas></div>
                    <div class="table-wrap"><table><thead><tr><th>Device</th><th>IPv4 address</th><th>Mac Address</th><th>Type</th><th>Latest ping</th><th>Min</th><th>Median</th><th>Max</th><th>Loss</th><th>Interval (sec)</th><th>Control</th></tr></thead><tbody id="monitored-rows"></tbody></table></div>
                    <div id="pagination-controls" style="display: flex; gap: 8px; justify-content: center; align-items: center; margin-top: 16px;"></div>
                </section>
            </section>

            <section class="view-panel data-panel" data-panel="alerts" hidden><p class="eyebrow">Ping events</p><h1>Alerts</h1><p class="panel-intro">Unreachable PCs and high-latency ping results.</p><div class="table-wrap"><table><thead><tr><th>Time</th><th>PC</th><th>Event</th><th>Status</th></tr></thead><tbody id="all-alerts-rows"><tr><td colspan="4">Waiting for live status...</td></tr></tbody></table></div><div id="all-alerts-pagination" style="display:flex;gap:8px;justify-content:center;align-items:center;margin-top:16px"></div></section>

            <section class="view-panel data-panel" data-panel="reports" hidden><p class="eyebrow">ICMP history</p><h1>Ping Records</h1><p class="panel-intro">Saved ping replies, packet loss, and latency statistics.</p><p><a class="refresh-button" href="/api/dataset.csv">Download ping dataset</a> <a class="refresh-button" href="/api/model-records.csv">Download ping records</a></p><div class="history-toolbar"><strong>History range</strong><div class="range-buttons"><button type="button" class="range-button active" data-hours="1">1 hour</button><button type="button" class="range-button" data-hours="24">24 hours</button><button type="button" class="range-button" data-hours="168">7 days</button></div></div><div class="table-wrap"><table id="reports-table"><thead><tr><th>Time</th><th>PC</th><th>IP</th><th>Replies</th><th>Loss</th><th>Min</th><th>Median</th><th>Max</th></tr></thead><tbody><tr><td colspan="8">Waiting for live ping records...</td></tr></tbody></table></div><div id="ping-records-pagination" style="display: flex; gap: 8px; justify-content: center; align-items: center; margin-top: 16px;"></div></section>

            <section class="view-panel data-panel" data-panel="ml-insights" hidden>
                <header class="ml-heading"><div><p class="eyebrow">Model training and results</p><h1>ML Insights</h1><p class="panel-intro">Train and review ping anomaly, forecast, and condition models.</p></div><button class="refresh-button" id="train-models-button" type="button" onclick="trainMlModels(this)">Train models</button></header>
                <p id="ml-status-line" class="ml-status-line" role="status">Loading model readiness...</p>
                <p id="ml-action-status" role="status"></p>
                <section class="summary-cards ml-cards">
                    <div class="card"><h2>Isolation Forest</h2><p id="if-model-state">Checking</p><small id="if-model-detail">Unsupervised anomaly detection</small></div>
                    <div class="card"><h2>GRU</h2><p id="gru-model-state">Checking</p><small id="gru-model-detail">Next-sample latency, loss, and reachability forecast</small></div>
                    <div class="card"><h2>XGBoost</h2><p id="xgb-model-state">Checking</p><small id="xgb-model-detail">Reviewed condition classification</small></div>
                </section>
                <section class="ml-results-section">
                    <h2>Condition classifier comparison</h2>
                    <p id="classifier-comparison-summary" class="panel-intro">No comparison yet. Review labels, then train to compare XGBoost with Logistic Regression and Random Forest on the same chronological holdout. XGBoost remains the live classifier.</p>
                    <div class="table-wrap"><table><thead><tr><th>Classifier</th><th>Macro-F1</th><th>Balanced accuracy</th><th>Per-condition recall / test support</th></tr></thead><tbody id="classifier-comparison-rows"><tr><td colspan="4">Waiting for a classifier comparison.</td></tr></tbody></table></div>
                </section>
                <section class="ml-results-section">
                    <div class="section-heading"><h2>Gateway and external comparison</h2><button class="range-button" id="poll-references-button" type="button" onclick="pollNetworkReferences(this)">Ping references</button></div>
                    <p class="panel-intro">Reference and PC statistics use the latest five samples, up to 25 probes. ICMP filtering can affect results; comparisons are indicators, not confirmed causes.</p>
                    <p><a class="refresh-button" href="/api/network-references.csv">Download reference samples</a></p>
                    <div class="table-wrap"><table><thead><tr><th>Reference</th><th>Target</th><th>Latest check</th><th>Rolling loss</th><th>Median latency</th><th>Latency variation</th></tr></thead><tbody id="reference-rows"><tr><td colspan="6">Loading references...</td></tr></tbody></table></div>
                    <div class="table-wrap"><table><thead><tr><th>PC</th><th>Rolling loss</th><th>Median latency</th><th>Latency variation</th><th>Comparison</th></tr></thead><tbody id="reference-device-rows"><tr><td colspan="5">Loading PC comparisons...</td></tr></tbody></table></div>
                </section>
                <section class="discovery-controls ml-training-section">
                    <h2>Review training labels</h2>
                    <p class="panel-intro">Labels describe the observed ping condition, not a verified physical root cause. Review samples before using them to train XGBoost or the normal baseline.</p>
                    <div class="table-wrap"><table><thead><tr><th>Time</th><th>PC</th><th>Latest ping</th><th>Loss</th><th>Condition label</th><th>Action</th></tr></thead><tbody id="ml-label-rows"><tr><td colspan="6">Loading samples...</td></tr></tbody></table></div>
                    <div id="ml-labels-pagination" style="display: flex; gap: 8px; justify-content: center; align-items: center; margin-top: 16px;"></div>
                </section>
                <section class="ml-results-section">
                    <div class="section-heading"><h2>Latest model outputs</h2><button class="range-button" type="button" onclick="refreshMlPanel()">Refresh</button></div>
                    <p class="panel-intro">Bottleneck, congestion, and failure are ping-based risk indicators derived from GRU forecasts, not confirmed physical causes.</p>
                    <div class="table-wrap ml-insights-scroll"><table><thead><tr><th>PC</th><th>Latest ping</th><th>Isolation Forest</th><th>GRU forecast</th><th>XGBoost condition</th><th>Predicted risks</th></tr></thead><tbody id="ml-insight-rows"><tr><td colspan="6">Loading predictions...</td></tr></tbody></table></div>
                    <div id="ml-insights-pagination" style="display: flex; gap: 8px; justify-content: center; align-items: center; margin-top: 16px;"></div>
                </section>
                <section class="ml-results-section">
                    <h2>Suggested next steps</h2>
                    <p class="panel-intro">Suggestions are advisory. Selecting one records your choice; it does not change network settings or retrain a model.</p>
                    <div class="table-wrap"><table><thead><tr><th>PC</th><th>Model</th><th>Evidence</th><th>Suggested check</th><th>Action</th></tr></thead><tbody id="ml-recommendation-rows"><tr><td colspan="5">Loading suggestions...</td></tr></tbody></table></div>
                    <div id="ml-recommendations-pagination" style="display: flex; gap: 8px; justify-content: center; align-items: center; margin-top: 16px;"></div>
                </section>
                <section class="ml-results-section">
                    <h2>Selected actions and outcomes</h2>
                    <p class="panel-intro">After performing a check, record whether it resolved the issue and any verified finding. This feedback is saved for review, not used for immediate online training.</p>
                    <p><a class="refresh-button" href="/api/ml/recommendation-feedback.csv">Download feedback</a></p>
                    <div class="table-wrap"><table><thead><tr><th>Selected</th><th>PC</th><th>Model and evidence</th><th>Action</th><th>Outcome</th><th>Verified finding</th><th>Notes</th><th>Save</th></tr></thead><tbody id="ml-feedback-rows"><tr><td colspan="8">Loading feedback...</td></tr></tbody></table></div>
                </section>
            </section>

            <section class="view-panel data-panel" data-panel="settings" hidden><p class="eyebrow">Display and monitoring</p><h1>Settings</h1><div class="settings-list"><div class="appearance-setting"><div class="theme-logo" aria-hidden="true"><span class="theme-sun">☀</span><span class="theme-moon">☾</span></div><div><strong>Appearance</strong><small id="theme-label">Light mode</small></div><label class="switch-control" for="theme-toggle"><span class="sr-only">Turn dark mode on or off</span><input id="theme-toggle" type="checkbox"><span class="switch-slider"></span></label></div><div class="building-setting"><div><strong>Building/Location name</strong><small>Identifies this monitoring instance.</small></div><div class="building-controls"><input id="building-name-input" type="text" placeholder="Building 1" value="Loading location..." aria-label="Building name"><button class="range-button" type="button" onclick="saveBuildingName()">Save</button></div></div><div class="building-setting"><div><strong>Saved databases</strong><small>Switch to a different building's database.</small></div><div class="building-controls"><select id="database-selector" aria-label="Select database"><option value="">Loading...</option></select><button class="range-button" type="button" onclick="switchDatabase()">Switch</button></div></div><div class="building-setting"><div><strong>Restart monitoring</strong><small>Restart the polling and recording service.</small></div><div class="building-controls"><button class="range-button" type="button" onclick="restartMonitoring()">Restart</button></div></div><div class="reference-setting"><div><strong>External ping reference</strong><small>IPv4 address; some hosts may block ICMP.</small></div><div class="reference-controls"><input id="external-reference-ip" type="text" inputmode="decimal" placeholder="1.1.1.1" aria-label="External reference IPv4 address"><button class="range-button" type="button" onclick="saveExternalReference()">Save</button></div></div></div><p id="reference-setting-status" role="status"></p></section>

            <section class="view-panel data-panel" data-panel="about" hidden><p class="eyebrow">ICMP monitoring</p><h1>About</h1><p class="panel-intro">This system checks PC reachability, packet loss, and round-trip latency using ping.</p></section>
        </main>
    </div>
    <script>
        let monitorDevices = [];
        let monitorHistory = [];
        let latestSampleId = null;
        let autoDiscoverTimer = null;
        let autoDiscoverActive = false;
        let allDiscoveredHosts = [];
        let discoveryDeviceTypes = {};  // Track device type overrides: {target: 'pc'|'phone'|'auto'}
        let monitorCurrentPage = 1;
        let monitorSearchQuery = '';
        let monitorDeviceTypeFilter = '';
        let allTelemetry = [];
        let allMlRecords = [];
        let allAlerts = [];
        let pingRecordsCurrentPage = 1;
        let mlInsightsCurrentPage = 1;
        let alertsCurrentPage = 1;
        let mlLabelsCurrentPage = 1;
        let mlRecommendationsCurrentPage = 1;
        let allMlLabels = [];
        let allMlRecommendations = [];
        const itemsPerPage = 10;

        async function requestJson(url, options = {}) {
            const response = await fetch(url, options);
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
            return payload;
        }

        function setStatus(message) {
            document.querySelector('#discovery-status').textContent = message;
        }

        async function saveBuildingName() {
            const input = document.querySelector('#building-name-input');
            const building_name = input.value.trim();
            if (!building_name) {
                alert('Please enter a building name');
                return;
            }
            try {
                const result = await requestJson('/api/settings/building-name', {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ building_name })
                });
                document.querySelector('#reference-setting-status').textContent = `Building "${result.building_name}" database created and activated! New monitoring records will be stored in this building's database.`;
                input.value = result.building_name;
                const bldgBadge = document.querySelector('#building-name');
                if (bldgBadge) bldgBadge.textContent = result.building_name;
                await loadDatabaseSelector();
                await refreshStatus();
                setTimeout(() => { document.querySelector('#reference-setting-status').textContent = ''; }, 6000);
            } catch (error) {
                document.querySelector('#reference-setting-status').textContent = `Error: ${error.message}`;
            }
        }

        async function discoverHosts(button, silent = false) {
            if (!silent) {
                button.disabled = true;
                setStatus('Discovering responding addresses...');
            }
            try {
                const limit = parseInt(document.querySelector('#discovery-limit').value) || 20;
                const {hosts} = await requestJson('/api/discover', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({subnet: document.querySelector('#subnet-input').value, limit: limit})});
                allDiscoveredHosts = hosts;
                const selected = new Set(monitorDevices.map((device) => device.target));
                filterDiscoveryRows();
                document.querySelector('#discovery-section').hidden = false;
                document.querySelector('#auto-discover-toggle').style.display = 'inline-block';
                if (!silent) {
                    setStatus(`${hosts.length} responding address${hosts.length === 1 ? '' : 'es'} found.`);
                }
            } catch (error) { if (!silent) { setStatus(error.message); } }
            finally { if (!silent) { button.disabled = false; } }
        }

        function filterDiscoveryRows() {
            const showPhones = document.querySelector('#show-phones-toggle').checked;
            const selected = new Set(monitorDevices.map((device) => device.target));
            const rows = allDiscoveredHosts
                .filter(host => showPhones || host.device_type !== 'phone')
                .map((host) => {
                    const icon = host.device_type === 'phone' ? '📱' : host.device_type === 'switch' ? '🔀' : '💻';
                    const deviceClass = host.device_type === 'phone' ? ' class="phone-device"' : host.device_type === 'switch' ? ' class="switch-device"' : '';
                    const currentType = discoveryDeviceTypes[host.target] || 'auto';
                    return `<tr${deviceClass}><td><input type="checkbox" value="${host.target}" ${selected.has(host.target) ? 'disabled' : ''}></td><td>${icon} ${escapeHtml(host.name)}</td><td>${host.target}</td><td><select onchange="setDiscoveryDeviceType('${host.target}', this.value)" ${selected.has(host.target) ? 'disabled' : ''}><option value="auto" ${currentType === 'auto' ? 'selected' : ''}>🔍 Auto (${host.device_type})</option><option value="pc" ${currentType === 'pc' ? 'selected' : ''}>💻 PC</option><option value="phone" ${currentType === 'phone' ? 'selected' : ''}>📱 Phone</option><option value="switch" ${currentType === 'switch' ? 'selected' : ''}>🔀 Switch</option></select></td></tr>`;
                })
                .join('') || '<tr><td colspan="4">No responding devices found.</td></tr>';
            document.querySelector('#discovered-rows').innerHTML = rows;
        }

        function toggleAutoDiscover(button) {
            autoDiscoverActive = !autoDiscoverActive;
            const subnetInput = document.querySelector('#subnet-input').value;
            
            if (autoDiscoverActive && subnetInput) {
                button.querySelector('span').textContent = 'Auto refresh: on';
                button.classList.add('active');
                discoverHosts(button, true);
                autoDiscoverTimer = setInterval(() => {
                    if (autoDiscoverActive && document.querySelector('#subnet-input').value === subnetInput) {
                        discoverHosts(button, true);
                    }
                }, 10000);
            } else {
                stopDiscoveryRefresh(button);
            }
        }

        function stopDiscoveryRefresh(button) {
            autoDiscoverActive = false;
            if (autoDiscoverTimer) {
                clearInterval(autoDiscoverTimer);
                autoDiscoverTimer = null;
            }
            button.querySelector('span').textContent = 'Auto refresh: off';
            button.classList.remove('active');
        }

        function setDiscoveryDeviceType(target, type) {
            discoveryDeviceTypes[target] = type;
        }

        async function addSelectedHosts() {
            const selected = [...document.querySelectorAll('#discovered-rows input:checked')].map((checkbox) => {
                const row = checkbox.closest('tr');
                const target = checkbox.value;
                // Find the host data from allDiscoveredHosts to get device_type
                const host = allDiscoveredHosts.find(h => h.target === target);
                const userSelectedType = discoveryDeviceTypes[target] || 'auto';
                const finalType = userSelectedType === 'auto' ? host?.device_type : userSelectedType;
                return {target: target, name: row.cells[1].textContent, device_type: finalType};
            });
            if (!selected.length) { setStatus('Select at least one device.'); return; }
            try {
                stopDiscoveryRefresh(document.querySelector('#auto-discover-toggle'));
                await requestJson('/api/devices', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({devices: selected})});
                discoveryDeviceTypes = {};  // Reset device type selections after adding
                setStatus(`${selected.length} device${selected.length === 1 ? '' : 's'} added. Start monitoring when ready.`);
                await refreshStatus();
            } catch (error) { setStatus(error.message); }
        }

        function escapeHtml(value) {
            const element = document.createElement('span');
            element.textContent = value;
            return element.innerHTML;
        }

        function escapeAttribute(value) {
            return escapeHtml(value).replaceAll('"', '&quot;').replaceAll("'", '&#39;');
        }

        async function setMonitoring(id, active) {
            try {
                await requestJson(`/api/devices/${id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({active})});
                await refreshStatus();
            } catch (error) { setStatus(error.message); }
        }

        async function setDeviceType(id, device_type) {
            try {
                await requestJson(`/api/devices/${id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({device_type})});
                await refreshStatus();
            } catch (error) { setStatus(error.message); }
        }

        async function reclassifyAllDevices() {
            try {
                setStatus('Re-detecting device types across network...');
                const res = await requestJson('/api/devices/reclassify', {method: 'POST'});
                const count = res.reclassified ? res.reclassified.length : 0;
                setStatus(`Re-detected types for ${count} device${count === 1 ? '' : 's'}.`);
                await refreshStatus();
            } catch (error) { setStatus(error.message); }
        }

        async function setIntervalSeconds(id, input) {
            const interval_seconds = Number(input.value);
            try {
                await requestJson(`/api/devices/${id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({interval_seconds})});
                input.value = Math.max(5, Math.min(3600, interval_seconds));
            } catch (error) { setStatus(error.message); }
        }

        async function removeDevice(id) {
            try { await requestJson(`/api/devices/${id}`, {method: 'DELETE'}); await refreshStatus(); }
            catch (error) { setStatus(error.message); }
        }

        function getFilteredDevices() {
            const query = monitorSearchQuery.toLowerCase().trim();
            const deviceTypeFilter = document.querySelector('#device-type-filter')?.value || '';
            monitorDeviceTypeFilter = deviceTypeFilter;
            
            return monitorDevices.filter(device => {
                // Filter by device type
                if (deviceTypeFilter && device.device_type !== deviceTypeFilter) {
                    return false;
                }
                // Filter by search query
                if (!query) return true;
                return device.name.toLowerCase().includes(query) || 
                       device.target.toLowerCase().includes(query);
            });
        }

        function renderPagination(filteredCount) {
            const totalPages = Math.ceil(filteredCount / itemsPerPage);
            const container = document.querySelector('#pagination-controls');
            
            if (totalPages <= 1) {
                container.innerHTML = '';
                return;
            }

            let html = '<button class="range-button" type="button" onclick="previousPage()" ' + (monitorCurrentPage === 1 ? 'disabled' : '') + '>← Previous</button>';
            
            for (let i = 1; i <= totalPages; i++) {
                const isCurrentPage = i === monitorCurrentPage;
                const activeClass = isCurrentPage ? 'active' : '';
                html += `<button class="range-button ${activeClass}" type="button" onclick="goToPage(${i})">${i}</button>`;
            }
            
            html += '<button class="range-button" type="button" onclick="nextPage()" ' + (monitorCurrentPage === totalPages ? 'disabled' : '') + '>Next →</button>';
            html += `<span style="margin-left: 16px; color: #666; font-size: 0.9em;">Page ${monitorCurrentPage} of ${totalPages}</span>`;
            
            container.innerHTML = html;
        }

        function renderDevices(devices) {
            monitorDevices = devices;
            const filteredDevices = getFilteredDevices();
            const totalFiltered = filteredDevices.length;
            const startIndex = (monitorCurrentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const pageDevices = filteredDevices.slice(startIndex, endIndex);
            
            const tbody = document.querySelector('#monitored-rows');
            tbody.innerHTML = pageDevices.map((device) => {
                const icon = device.device_type === 'phone' ? '📱' : device.device_type === 'switch' ? '🔀' : '💻';
                const typeLabel = device.device_type === 'phone' ? 'Phone' : device.device_type === 'switch' ? 'Switch' : 'PC';
                const deviceClass = device.device_type === 'phone' ? ' class="phone-device"' : device.device_type === 'switch' ? ' class="switch-device"' : '';
                return `<tr${deviceClass}><td>${escapeHtml(device.name)}</td><td>${device.target}</td><td>${device.mac_address || '-'}</td><td><select onchange="setDeviceType(${device.id}, this.value)" style="padding: 4px; min-width: 100px;"><option value="pc" ${device.device_type === 'pc' ? 'selected' : ''}>💻 PC</option><option value="phone" ${device.device_type === 'phone' ? 'selected' : ''}>📱 Phone</option><option value="switch" ${device.device_type === 'switch' ? 'selected' : ''}>🔀 Switch</option></select></td><td>${device.latest?.online ? 'Online' : device.latest ? 'Offline' : 'Not checked'}</td><td>${device.latest?.latency_min_display || '-'}</td><td>${device.latest?.latency_median_display || '-'}</td><td>${device.latest?.latency_max_display || '-'}</td><td>${device.latest ? `${device.latest.packet_loss}%` : '-'}</td><td><input type="number" min="5" max="3600" value="${device.interval_seconds}" aria-label="Ping interval seconds" onchange="setIntervalSeconds(${device.id}, this)"></td><td><button class="range-button" type="button" onclick="setMonitoring(${device.id}, ${!device.active})">${device.active ? 'Pause' : 'Start'}</button> <button class="range-button" type="button" onclick="removeDevice(${device.id})" aria-label="Remove ${escapeHtml(device.name)}">Remove</button></td></tr>`;
            }).join('') || '<tr><td colspan="11">Discover and add devices to monitor.</td></tr>';
            
            document.querySelector('#saved-count').textContent = devices.length;
            document.querySelector('#active-count').textContent = devices.filter((device) => device.active).length;
            document.querySelector('#monitor-summary').textContent = `${devices.filter((device) => device.active).length} active (${totalFiltered} shown)`;
            
            const chartSelect = document.querySelector('#chart-device');
            const current = chartSelect.value;
            chartSelect.innerHTML = devices.map((device) => `<option value="${device.target}">${escapeHtml(device.name)}</option>`).join('');
            if (devices.some((device) => device.target === current)) chartSelect.value = current;
            
            renderPagination(totalFiltered);
        }

        function applySearchAndPagination() {
            monitorSearchQuery = document.querySelector('#monitor-search').value;
            monitorCurrentPage = 1;
            renderDevices(monitorDevices);
        }

        function clearMonitorSearch() {
            monitorSearchQuery = '';
            document.querySelector('#monitor-search').value = '';
            document.querySelector('#device-type-filter').value = '';
            monitorCurrentPage = 1;
            renderDevices(monitorDevices);
        }

        function previousPage() {
            if (monitorCurrentPage > 1) {
                monitorCurrentPage--;
                renderDevices(monitorDevices);
            }
        }

        function nextPage() {
            const filteredDevices = getFilteredDevices();
            const totalPages = Math.ceil(filteredDevices.length / itemsPerPage);
            if (monitorCurrentPage < totalPages) {
                monitorCurrentPage++;
                renderDevices(monitorDevices);
            }
        }

        function goToPage(pageNum) {
            monitorCurrentPage = pageNum;
            renderDevices(monitorDevices);
        }

        async function bulkStartAll() {
            const filteredDevices = getFilteredDevices();
            if (!confirm(`Start monitoring on all ${filteredDevices.length} device${filteredDevices.length === 1 ? '' : 's'}?`)) return;
            try {
                for (const device of filteredDevices) {
                    if (!device.active) {
                        await requestJson(`/api/devices/${device.id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({active: true})});
                    }
                }
                setStatus(`✓ Started monitoring on ${filteredDevices.length} device${filteredDevices.length === 1 ? '' : 's'}`);
                await refreshStatus();
            } catch (error) { setStatus(error.message); }
        }

        async function bulkPauseAll() {
            const filteredDevices = getFilteredDevices();
            if (!confirm(`Pause monitoring on all ${filteredDevices.length} device${filteredDevices.length === 1 ? '' : 's'}?`)) return;
            try {
                for (const device of filteredDevices) {
                    if (device.active) {
                        await requestJson(`/api/devices/${device.id}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({active: false})});
                    }
                }
                setStatus(`✓ Paused monitoring on ${filteredDevices.length} device${filteredDevices.length === 1 ? '' : 's'}`);
                await refreshStatus();
            } catch (error) { setStatus(error.message); }
        }

        function renderPaginationForTable(containerId, currentPage, totalItems, pageChangeHandler) {
            const totalPages = Math.ceil(totalItems / itemsPerPage);
            const container = document.querySelector(containerId);
            if (!container) return;
            
            if (totalPages <= 1) {
                container.replaceChildren();
                return;
            }

            const makeButton = (label, page, {active = false, disabled = false} = {}) => {
                const button = document.createElement('button');
                button.className = `range-button${active ? ' active' : ''}`;
                button.type = 'button';
                button.textContent = label;
                button.disabled = disabled;
                if (active) {
                    button.setAttribute('aria-current', 'page');
                }
                button.addEventListener('click', () => pageChangeHandler(page));
                return button;
            };

            const controls = [makeButton('← Previous', currentPage - 1, {disabled: currentPage === 1})];
            for (let i = 1; i <= totalPages; i++) {
                controls.push(makeButton(String(i), i, {active: i === currentPage}));
            }
            controls.push(makeButton('Next →', currentPage + 1, {disabled: currentPage === totalPages}));

            const pageLabel = document.createElement('span');
            pageLabel.style.marginLeft = '16px';
            pageLabel.style.color = '#666';
            pageLabel.style.fontSize = '0.9em';
            pageLabel.textContent = `Page ${currentPage} of ${totalPages}`;
            controls.push(pageLabel);

            container.replaceChildren(...controls);
        }

        function renderPingRecords(telemetry) {
            allTelemetry = telemetry.slice().reverse();
            const startIndex = (pingRecordsCurrentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const pageRecords = allTelemetry.slice(startIndex, endIndex);
            
            const tbody = document.querySelector('#reports-table tbody');
            tbody.innerHTML = pageRecords.map((sample) => `<tr data-recorded-at="${sample.recorded_at}"><td>${sample.recorded_at}</td><td>${escapeHtml(sample.device_name)}</td><td>${sample.target}</td><td>${sample.ping_received}/${sample.ping_sent}</td><td>${sample.packet_loss}%</td><td>${sample.latency_min_display}</td><td>${sample.latency_median_display}</td><td>${sample.latency_max_display}</td></tr>`).join('') || '<tr><td colspan="8">No ping records yet.</td></tr>';
            
            renderPaginationForTable('#ping-records-pagination', pingRecordsCurrentPage, allTelemetry.length, goToPingRecordsPage);
        }

        function renderAlertsTable(alerts) {
            allAlerts = alerts;
            const startIndex = (alertsCurrentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const pageAlerts = allAlerts.slice(startIndex, endIndex);

            const rows = pageAlerts.map((alert) => `<tr><td>${alert.recorded_at}</td><td>${escapeHtml(alert.device_name)}</td><td>${escapeHtml(alert.message)}</td></tr>`).join('');
            const allRows = pageAlerts.map((alert) => `<tr><td>${alert.recorded_at}</td><td>${escapeHtml(alert.device_name)}</td><td>${escapeHtml(alert.message)}</td><td><span class="status-pill status-warning">Open</span></td></tr>`).join('');
            document.querySelector('#alert-rows').innerHTML = rows || '<tr><td colspan="3">No ping alerts.</td></tr>';
            document.querySelector('#all-alerts-rows').innerHTML = allRows || '<tr><td colspan="4">No ping alerts.</td></tr>';
            renderPaginationForTable('#alerts-pagination', alertsCurrentPage, allAlerts.length, goToAlertsPage);
            renderPaginationForTable('#all-alerts-pagination', alertsCurrentPage, allAlerts.length, goToAlertsPage);
        }

        function renderMlInsightsWithPagination(devices) {
            allMlRecords = devices;
            const startIndex = (mlInsightsCurrentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const pageDevices = allMlRecords.slice(startIndex, endIndex);
            
            const body = document.querySelector('#ml-insight-rows');
            body.innerHTML = pageDevices.map((device) => `<tr><td>${escapeHtml(device.device_name)}<br><small>${escapeHtml(device.target)}</small></td><td>${device.current.online ? `${device.current.latency_median_ms ?? '-'} ms` : 'Unreachable'}<br><small>${device.current.packet_loss}% loss</small></td><td>${escapeHtml(modelOutputText(device.isolation_forest, 'isolation_forest'))}</td><td>${escapeHtml(modelOutputText(device.gru, 'gru'))}</td><td>${escapeHtml(modelOutputText(device.xgboost, 'xgboost'))}</td><td>${escapeHtml(riskOutputText(device.gru))}</td></tr>`).join('') || '<tr><td colspan="6">No valid ping samples yet.</td></tr>';
            
            renderPaginationForTable('#ml-insights-pagination', mlInsightsCurrentPage, allMlRecords.length, goToMlInsightsPage);
        }

        function goToPingRecordsPage(pageNum) {
            pingRecordsCurrentPage = pageNum;
            renderPingRecords(allTelemetry.slice().reverse());
        }

        function goToAlertsPage(pageNum) {
            alertsCurrentPage = pageNum;
            renderAlertsTable(allAlerts);
        }

        function goToMlInsightsPage(pageNum) {
            mlInsightsCurrentPage = pageNum;
            renderMlInsightsWithPagination(allMlRecords);
        }

        function renderMlLabels(labelData) {
            allMlLabels = labelData.samples || [];
            const startIndex = (mlLabelsCurrentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const pageLabels = allMlLabels.slice(startIndex, endIndex);
            
            const labels = labelData.labels || [];
            const body = document.querySelector('#ml-label-rows');
            body.innerHTML = pageLabels.map((sample) => `<tr><td>${escapeHtml(sample.recorded_at)}</td><td>${escapeHtml(sample.device_name)}<br><small>${escapeHtml(sample.target)}</small></td><td>${sample.online ? `${sample.latency_median_ms ?? sample.latency_ms ?? '-'} ms` : 'Unreachable'}</td><td>${sample.packet_loss}%</td><td><select class="ml-label-select" aria-label="Condition label for sample ${sample.id}"><option value="">Choose label</option>${labels.map((label) => `<option value="${escapeHtml(label)}" ${sample.condition_label === label ? 'selected' : ''}>${escapeHtml(label)}</option>`).join('')}</select></td><td><button class="range-button" type="button" onclick="saveMlLabel(${sample.id}, this)">Save</button></td></tr>`).join('') || '<tr><td colspan="6">No valid ping samples available to label.</td></tr>';            
            renderPaginationForTable('#ml-labels-pagination', mlLabelsCurrentPage, allMlLabels.length, goToMlLabelsPage);
        }

        function renderMlRecommendations(devices) {
            allMlRecommendations = devices.flatMap((device) => device.suggestions.map((suggestion) => ({...suggestion, device_name: device.device_name, target: device.target, telemetry_id: device.telemetry_id}))) || [];
            renderMlRecommendationsPage();
        }

        function renderMlRecommendationsPage() {
            const startIndex = (mlRecommendationsCurrentPage - 1) * itemsPerPage;
            const endIndex = startIndex + itemsPerPage;
            const pageRecs = allMlRecommendations.slice(startIndex, endIndex);
            
            const body = document.querySelector('#ml-recommendation-rows');
            body.innerHTML = pageRecs.map((row) => `<tr><td>${escapeHtml(row.device_name)}<br><small>${escapeHtml(row.target)}</small></td><td>${escapeHtml(row.model_sources.join(', '))}</td><td>${escapeHtml(row.evidence.join(' '))}</td><td>${escapeHtml(row.action)}</td><td><button class="range-button" type="button" data-select-telemetry="${row.telemetry_id}" data-select-suggestion="${escapeHtml(row.id)}">Select</button></td></tr>`).join('') || '<tr><td colspan="5">No suggestions available.</td></tr>';            
            renderPaginationForTable('#ml-recommendations-pagination', mlRecommendationsCurrentPage, allMlRecommendations.length, goToMlRecommendationsPage);
        }

        function goToMlLabelsPage(pageNum) {
            mlLabelsCurrentPage = pageNum;
            renderMlLabels({samples: allMlLabels, labels: document.querySelector('#ml-label-rows') ? Array.from(document.querySelectorAll('#ml-label-rows select option')).filter((o, i) => i > 0 && !o.disabled).map(o => o.value).filter((v, i, a) => a.indexOf(v) === i) : []});
        }

        function goToMlRecommendationsPage(pageNum) {
            mlRecommendationsCurrentPage = pageNum;
            renderMlRecommendationsPage();
        }

        async function refreshStatus() {
            try {
                const data = await requestJson('/api/status');
                const devices = data.devices || [];
                const telemetry = data.telemetry || [];
                const alerts = data.alerts || [];
                const latestByTarget = new Map();
                telemetry.forEach((sample) => { if (!latestByTarget.has(sample.target)) latestByTarget.set(sample.target, sample); });
                renderDevices(devices.map((device) => ({...device, latest: latestByTarget.get(device.target) || null})));
                const activeDevices = devices.filter((device) => device.active);
                const reachableDevices = activeDevices.filter((device) => latestByTarget.get(device.target)?.online);
                const networkHealth = activeDevices.length === 0
                    ? 'Waiting'
                    : reachableDevices.length === activeDevices.length
                        ? 'Good'
                        : reachableDevices.length > 0 ? 'Degraded' : 'Offline';
                const latencies = [...latestByTarget.values()]
                    .map((sample) => sample.latency_median_ms ?? sample.latency_ms)
                    .filter((value) => value !== null && value !== undefined && Number.isFinite(Number(value)));
                const averageLatency = latencies.length
                    ? `${Math.round(latencies.reduce((total, value) => total + Number(value), 0) / latencies.length * 10) / 10} ms`
                    : 'N/A';
                document.querySelector('#network-health').textContent = networkHealth;
                document.querySelector('#open-alerts').textContent = alerts.length;
                document.querySelector('#metric-average-latency').textContent = averageLatency;
                document.querySelector('#metric-reachable').textContent = `${reachableDevices.length} / ${latestByTarget.size}`;
                document.querySelector('#metric-monitoring').textContent = activeDevices.length;
                document.querySelector('#metric-samples').textContent = telemetry.filter((sample) => sample.protocol === 'icmp').length;
                document.querySelector('#dashboard-updated').textContent = new Date().toLocaleString();
                const fresh = telemetry.slice().reverse();
                if (fresh.length && fresh[fresh.length - 1].id !== latestSampleId) {
                    latestSampleId = fresh[fresh.length - 1].id;
                    monitorHistory = fresh.map((sample) => ({time: sample.recorded_at, device: sample.target, latency: sample.latency_median_ms ?? sample.latency_ms, latency_min_display:sample.latency_min_display, latency_median_display:sample.latency_median_display, latency_max_display:sample.latency_max_display, ping_received:sample.ping_received, ping_sent:sample.ping_sent, online: Boolean(sample.online), packet_loss: sample.packet_loss}));
                    renderPingRecords(fresh);
                    drawPingChart();
                }
                renderAlertsTable(alerts);
            } catch (error) { setStatus(error.message); }
        }

        async function loadBuildingName() {
            try {
                const data = await requestJson('/api/settings/building-name');
                document.querySelector('#building-name').textContent = data.building_name;
                document.querySelector('#building-name-input').value = data.building_name;
            } catch (error) {
                document.querySelector('#building-name').textContent = 'Location unavailable';
            }
        }

        function modelReadinessText(status, model, dependencyNames) {
            const trained = status.models?.[model]?.state === 'trained';
            if (trained) return 'Trained';
            if (dependencyNames.some((name) => !status.dependencies[name])) return 'Dependency needed';
            return status[model]?.ready ? 'Ready to train' : 'Collecting data';
        }

        function updateModelReadiness(status) {
            const classCounts = status.label_counts || {};
            const classText = Object.entries(classCounts).map(([label, count]) => `${label}: ${count}`).join(', ') || 'no reviewed labels';
            document.querySelector('#ml-status-line').textContent = `${status.telemetry_samples} valid ping samples; ${status.labeled_samples} reviewed labels (${classText}). Training uses chronological holdouts.`;
            const trainedModels = Object.values(status.models || {}).filter((model) => model.state === 'trained').length;
            document.querySelector('#dashboard-valid-samples').textContent = status.telemetry_samples;
            document.querySelector('#dashboard-labeled-samples').textContent = status.labeled_samples;
            document.querySelector('#dashboard-ml-version').textContent = `${trainedModels}/3 trained`;

            const entries = [
                ['if', 'isolation_forest', ['scikit-learn'], `${status.isolation_forest.normal_samples}/${status.isolation_forest.required_normal_samples} reviewed Normal samples`],
                ['gru', 'gru', ['scikit-learn', 'torch'], `${status.gru.sequence_windows}/${status.gru.required_sequence_windows} sequence windows; window length ${status.gru.sequence_length}`],
                ['xgb', 'xgboost', ['scikit-learn', 'xgboost'], `Needs at least ${status.xgboost.required_samples_per_class} reviewed samples in two classes`],
            ];
            entries.forEach(([shortName, key, required, detail]) => {
                const model = status.models?.[key];
                const state = modelReadinessText(status, key, required);
                document.querySelector(`#${shortName}-model-state`).textContent = state;
                document.querySelector(`#${shortName}-model-detail`).textContent = model?.state === 'trained'
                    ? Object.entries(model).filter(([name]) => !['state', 'classifier_comparison'].includes(name)).map(([name, value]) => `${name.replaceAll('_', ' ')}: ${typeof value === 'object' ? JSON.stringify(value) : value}`).join(' | ')
                    : detail;
            });
            renderClassifierComparison(status);
            document.querySelector('#train-models-button').disabled = false;
        }

        function renderClassifierComparison(status) {
            const summary = document.querySelector('#classifier-comparison-summary');
            const body = document.querySelector('#classifier-comparison-rows');
            const comparison = status.models?.xgboost?.classifier_comparison;
            if (!comparison) {
                const xgboostStatus = status.models?.xgboost;
                summary.textContent = xgboostStatus?.reason
                    ? `Not evaluated: ${xgboostStatus.reason}`
                    : 'No comparison yet. Review labels, then train to compare XGBoost with Logistic Regression and Random Forest on the same chronological holdout. XGBoost remains the live classifier.';
                body.innerHTML = '<tr><td colspan="4">Not evaluated. Every reviewed condition must appear in both the training and test periods.</td></tr>';
                return;
            }

            summary.textContent = `${comparison.protocol}: ${comparison.train_samples} training samples and ${comparison.test_samples} later test samples from ${comparison.test_start}. This is exploratory; validate on additional future periods before selecting a model.`;
            const modelNames = {
                xgboost: 'XGBoost',
                logistic_regression: 'Logistic Regression',
                random_forest: 'Random Forest',
            };
            const formatPercent = (value) => `${(Number(value) * 100).toFixed(1)}%`;
            body.innerHTML = Object.entries(comparison.models || {}).map(([name, metrics]) => {
                const classRecall = Object.entries(metrics.per_class || {}).map(([label, values]) =>
                    `${escapeHtml(label)}: ${formatPercent(values.recall)} (n=${values.support})`
                ).join('; ');
                return `<tr><td>${modelNames[name] || escapeHtml(name)}</td><td>${formatPercent(metrics.macro_f1)}</td><td>${formatPercent(metrics.balanced_accuracy)}</td><td>${classRecall}</td></tr>`;
            }).join('') || '<tr><td colspan="4">No comparison results are available.</td></tr>';
        }

        function modelOutputText(result, modelName) {
            if (!result || result.state === 'not_trained') return 'Not trained';
            if (result.state === 'not_enough_history') return `Needs ${result.required_samples} samples`;
            if (result.state === 'retrain_required') return 'Retrain model';
            if (result.state !== 'ready') return result.reason || result.state;
            if (modelName === 'isolation_forest') return `${result.result} (score ${result.anomaly_score})`;
            if (modelName === 'gru') return `${result.next_latency_ms} ms; ${result.next_packet_loss_percent}% loss; reachability ${Math.round(result.next_reachability_probability * 100)}%`;
            return `${result.condition} (${Math.round(result.confidence * 100)}%)`;
        }

        function riskOutputText(result) {
            if (!result || result.state !== 'ready') return modelOutputText(result, 'gru');
            const risks = result.risk_indicators || {};
            return `Bottleneck: ${risks.bottleneck || 'N/A'}; congestion: ${risks.congestion || 'N/A'}; failure: ${risks.failure || 'N/A'}`;
        }

        function renderMlInsights(devices) {
            renderMlInsightsWithPagination(devices);
        }

        function renderNetworkReferences(data) {
            const referenceRows = [
                data.gateway || {name: 'Local gateway', target: 'Not detected', sample_count: 0, online: null},
                data.external || {name: 'External reference', target: data.external_reference_target, sample_count: 0, online: null},
            ];
            document.querySelector('#reference-rows').innerHTML = referenceRows.map((reference) => `<tr><td>${escapeHtml(reference.name)}</td><td>${escapeHtml(reference.target)}</td><td>${reference.sample_count ? reference.online ? 'Responding' : 'No ping reply' : 'Not checked'}</td><td>${reference.packet_loss_percent == null ? '-' : `${reference.packet_loss_percent}% (${reference.sample_count} samples)`}</td><td>${reference.latency_median_ms == null ? '-' : `${reference.latency_median_ms} ms`}</td><td>${reference.latency_variation_ms == null ? '-' : `${reference.latency_variation_ms} ms`}</td></tr>`).join('');
            document.querySelector('#reference-device-rows').innerHTML = data.devices.map((device) => `<tr><td>${escapeHtml(device.target)}</td><td>${device.packet_loss_percent == null ? '-' : `${device.packet_loss_percent}% (${device.sample_count} samples)`}</td><td>${device.latency_median_ms == null ? '-' : `${device.latency_median_ms} ms`}</td><td>${device.latency_variation_ms == null ? '-' : `${device.latency_variation_ms} ms`}</td><td>${escapeHtml(device.comparison)}</td></tr>`).join('') || '<tr><td colspan="5">No monitored PC samples yet.</td></tr>';
            const setting = document.querySelector('#external-reference-ip');
            if (document.activeElement !== setting) setting.value = data.external_reference_target || '';
        }

        async function pollNetworkReferences(button) {
            button.disabled = true;
            document.querySelector('#ml-action-status').textContent = 'Pinging gateway and external reference...';
            try {
                const data = await requestJson('/api/network-references/poll', {method: 'POST'});
                renderNetworkReferences(data);
                document.querySelector('#ml-action-status').textContent = 'Reference samples updated.';
            } catch (error) { document.querySelector('#ml-action-status').textContent = error.message; }
            finally { button.disabled = false; }
        }

        async function saveExternalReference() {
            const input = document.querySelector('#external-reference-ip');
            const status = document.querySelector('#reference-setting-status');
            try {
                const result = await requestJson('/api/settings/external-reference', {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({target: input.value})});
                input.value = result.target;
                status.textContent = 'External reference saved.';
                await refreshMlPanel();
            } catch (error) { status.textContent = error.message; }
        }

        async function loadDatabaseSelector() {
            const selector = document.querySelector('#database-selector');
            const status = document.querySelector('#reference-setting-status');
            try {
                const data = await requestJson('/api/settings/databases');
                document.querySelector('#building-name-input').value = data.current_building || '';
                const bldgBadge = document.querySelector('#building-name');
                if (bldgBadge) bldgBadge.textContent = data.current_building || 'Unknown location';
                selector.innerHTML = data.databases.map((db) => `<option value="${escapeAttribute(db.name)}" ${db.name === data.current_building ? 'selected' : ''}>${escapeHtml(db.name)}</option>`).join('') || '<option value="">No databases found</option>';
            } catch (error) { status.textContent = error.message; }
        }

        async function switchDatabase() {
            const selector = document.querySelector('#database-selector');
            const status = document.querySelector('#reference-setting-status');
            const building_name = selector.value;
            if (!building_name) {
                status.textContent = 'Select a database first.';
                return;
            }
            try {
                const result = await requestJson('/api/settings/databases/select', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ building_name })
                });
                status.textContent = result.message || 'Database switched successfully!';
                document.querySelector('#building-name-input').value = result.building_name;
                const bldgBadge = document.querySelector('#building-name');
                if (bldgBadge) bldgBadge.textContent = result.building_name;
                await loadDatabaseSelector();
                await refreshStatus();
                setTimeout(() => { status.textContent = ''; }, 5000);
            } catch (error) { status.textContent = error.message; }
        }

        async function restartMonitoring() {
            const status = document.querySelector('#reference-setting-status');
            try {
                const result = await requestJson('/api/control/restart-monitoring', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                status.textContent = result.message || 'Monitoring service restarted successfully!';
            } catch (error) { status.textContent = error.message; }
        }

        async function loadExternalReferenceSetting() {
            try {
                const data = await requestJson('/api/network-references');
                renderNetworkReferences(data);
            } catch (error) { document.querySelector('#reference-setting-status').textContent = error.message; }
        }

        function renderRecommendationFeedback(feedback) {
            const outcomes = [['resolved', 'Resolved'], ['not_resolved', 'Not resolved'], ['unknown', 'Unknown']];
            const findings = ['', 'Shared path degradation', 'Device-specific issue', 'ICMP blocked', 'No issue found', 'Other / unknown'];
            const body = document.querySelector('#ml-feedback-rows');
            body.innerHTML = feedback.map((item) => `<tr><td>${escapeHtml(item.selected_at)}</td><td>${escapeHtml(item.device_name)}<br><small>${escapeHtml(item.target)}</small></td><td>${escapeHtml(item.model_sources.join(', '))}<br><small>${escapeHtml(item.evidence.join(' '))}</small></td><td>${escapeHtml(item.suggested_action)}</td><td><select class="ml-feedback-control" aria-label="Outcome for selected action ${item.id}"><option value="">Record outcome</option>${outcomes.map(([value, label]) => `<option value="${value}" ${item.outcome === value ? 'selected' : ''}>${label}</option>`).join('')}</select></td><td><select class="ml-feedback-control" aria-label="Verified finding for selected action ${item.id}">${findings.map((value) => `<option value="${escapeAttribute(value)}" ${item.verified_finding === value ? 'selected' : ''}>${escapeHtml(value || 'Not verified')}</option>`).join('')}</select></td><td><input class="ml-feedback-control ml-feedback-notes" type="text" maxlength="1000" value="${escapeAttribute(item.notes)}" aria-label="Notes for selected action ${item.id}"></td><td><button class="range-button" type="button" onclick="saveMlRecommendationOutcome(${item.id}, this)">Save</button></td></tr>`).join('') || '<tr><td colspan="8">No selected suggestions yet.</td></tr>';
        }

        async function refreshMlPanel() {
            try {
                const [status, labelData, insights, feedback, references] = await Promise.all([
                    requestJson('/api/ml/status'), requestJson('/api/ml/labels'), requestJson('/api/ml/insights'), requestJson('/api/ml/recommendation-feedback'), requestJson('/api/network-references'),
                ]);
                updateModelReadiness(status);
                renderMlLabels(labelData);
                renderMlInsights(insights.devices);
                renderMlRecommendations(insights.devices);
                renderRecommendationFeedback(feedback.feedback);
                renderNetworkReferences(references);
            } catch (error) {
                document.querySelector('#ml-action-status').textContent = error.message;
            }
        }

        async function saveMlLabel(telemetryId, button) {
            const label = button.closest('tr').querySelector('select').value;
            if (!label) { document.querySelector('#ml-action-status').textContent = 'Choose a condition label first.'; return; }
            try {
                await requestJson(`/api/ml/labels/${telemetryId}`, {method: 'PUT', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({label})});
                document.querySelector('#ml-action-status').textContent = 'Reviewed label saved.';
                await refreshMlPanel();
            } catch (error) { document.querySelector('#ml-action-status').textContent = error.message; }
        }

        async function selectMlRecommendation(telemetryId, suggestionId, button) {
            button.disabled = true;
            try {
                await requestJson(`/api/ml/recommendation-feedback/${telemetryId}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({suggestion_id: suggestionId})});
                document.querySelector('#ml-action-status').textContent = 'Selection recorded. Perform the check, then record its outcome below.';
                await refreshMlPanel();
            } catch (error) { document.querySelector('#ml-action-status').textContent = error.message; }
            finally { button.disabled = false; }
        }

        async function saveMlRecommendationOutcome(feedbackId, button) {
            const row = button.closest('tr');
            const controls = row.querySelectorAll('select');
            const outcome = controls[0].value;
            if (!outcome) { document.querySelector('#ml-action-status').textContent = 'Choose an outcome before saving.'; return; }
            try {
                await requestJson(`/api/ml/recommendation-feedback/${feedbackId}`, {method: 'PATCH', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({outcome, verified_finding: controls[1].value, notes: row.querySelector('.ml-feedback-notes').value})});
                document.querySelector('#ml-action-status').textContent = 'Action outcome saved for later review.';
                await refreshMlPanel();
            } catch (error) { document.querySelector('#ml-action-status').textContent = error.message; }
        }

        async function trainMlModels(button) {
            button.disabled = true;
            document.querySelector('#ml-action-status').textContent = 'Training models that meet their data requirements...';
            try {
                const result = await requestJson('/api/ml/train', {method: 'POST'});
                const summary = Object.entries(result.models).map(([name, value]) => `${name.replaceAll('_', ' ')}: ${value.state}`).join('; ');
                document.querySelector('#ml-action-status').textContent = summary;
                await refreshMlPanel();
                document.querySelector('#ml-action-status').textContent = summary;
            } catch (error) { document.querySelector('#ml-action-status').textContent = error.message; }
            finally { button.disabled = false; }
        }

        async function pollNow(button) {
            button.disabled = true;
            try { await requestJson('/api/monitor-now', {method: 'POST'}); await refreshStatus(); }
            catch (error) { setStatus(error.message); }
            finally { button.disabled = false; }
        }

        function drawPingChart() {
            const canvas = document.querySelector('#ping-chart');
            if (!canvas || document.querySelector('[data-panel="monitor"][hidden]')) return;
            const width = canvas.clientWidth || 600;
            const height = 220;
            const ratio = window.devicePixelRatio || 1;
            canvas.width = width * ratio;
            canvas.height = height * ratio;
            const context = canvas.getContext('2d');
            context.scale(ratio, ratio);
            context.clearRect(0, 0, width, height);
            const target = document.querySelector('#chart-device').value;
            const points = monitorHistory.filter((sample) => sample.device === target && sample.latency != null).slice(-100);
            const padding = {top: 18, right: 18, bottom: 28, left: 42};
            const maximum = Math.max(10, ...points.map((point) => point.latency));
            const x = (index) => padding.left + index / Math.max(points.length - 1, 1) * (width - padding.left - padding.right);
            const y = (value) => height - padding.bottom - value / maximum * (height - padding.top - padding.bottom);
            context.strokeStyle = getComputedStyle(document.body).getPropertyValue('--chart-grid') || '#dce6ee';
            for (let index = 0; index < 4; index += 1) { const lineY = padding.top + index * (height - padding.top - padding.bottom) / 3; context.beginPath(); context.moveTo(padding.left, lineY); context.lineTo(width - padding.right, lineY); context.stroke(); }
            if (points.length) {
                context.beginPath(); context.strokeStyle = '#1976c9'; context.lineWidth = 2.5;
                points.forEach((point, index) => index ? context.lineTo(x(index), y(point.latency)) : context.moveTo(x(index), y(point.latency)));
                context.stroke();
            }
            context.fillStyle = getComputedStyle(document.body).color;
            context.font = '12px Segoe UI';
            context.fillText(`${Math.round(maximum)} ms`, 4, padding.top + 4);
            context.fillText('0 ms', 4, height - padding.bottom + 4);
            if (!points.length) context.fillText('No ping samples yet', padding.left + 8, height / 2);
        }

        document.querySelectorAll('.range-button[data-hours]').forEach((button) => button.addEventListener('click', () => {
            const cutoff = Date.now() - Number(button.dataset.hours) * 3600000;
            document.querySelectorAll('.range-button[data-hours]').forEach((item) => item.classList.toggle('active', item === button));
            document.querySelectorAll('#reports-table tbody tr[data-recorded-at]').forEach((row) => { row.hidden = Date.parse(row.dataset.recordedAt) < cutoff; });
        }));

        const themeToggle = document.querySelector('#theme-toggle');
        function setTheme(isDark) {
            document.body.classList.toggle('dark-mode', isDark);
            themeToggle.checked = isDark;
            document.querySelector('#theme-label').textContent = isDark ? 'Dark mode' : 'Light mode';
            localStorage.setItem('network-monitor-theme', isDark ? 'dark' : 'light');
        }
        setTheme(localStorage.getItem('network-monitor-theme') === 'dark');
        themeToggle.addEventListener('change', () => { setTheme(themeToggle.checked); drawPingChart(); });

        const navItems = document.querySelectorAll('.nav-item');
        const panels = document.querySelectorAll('[data-panel]');
        navItems.forEach((item) => item.addEventListener('click', () => {
            navItems.forEach((navItem) => { const active = navItem === item; navItem.classList.toggle('active', active); if (active) navItem.setAttribute('aria-current', 'page'); else navItem.removeAttribute('aria-current'); });
            panels.forEach((panel) => { const visible = panel.dataset.panel === item.dataset.view; panel.hidden = !visible; panel.classList.toggle('active', visible); });
            if (item.dataset.view === 'monitor') { drawPingChart(); refreshStatus(); }
            if (item.dataset.view === 'ml-insights') refreshMlPanel();
            if (item.dataset.view === 'settings') { loadExternalReferenceSetting(); loadDatabaseSelector(); }
        }));

        document.querySelector('#ml-recommendation-rows').addEventListener('click', (event) => {
            const button = event.target.closest('[data-select-suggestion]');
            if (button) selectMlRecommendation(Number(button.dataset.selectTelemetry), button.dataset.selectSuggestion, button);
        });

        window.addEventListener('resize', drawPingChart);
        requestJson('/api/devices').then((data) => { document.querySelector('#subnet-input').value = data.local_network.suggested_subnet; }).catch((error) => setStatus(error.message));
        loadBuildingName();
        refreshMlPanel();
        refreshStatus();
        window.setInterval(refreshStatus, 5000);
    </script>
</body>
</html>