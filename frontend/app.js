const API_BASE_URL = (window.location.protocol.startsWith("http")) ? "" : "http://127.0.0.1:5000";

let fleetTimer = null;
let fleetDataCache = [];
let fleetSummaryCache = {};
let selectedDetailTxId = null;
const visibleTxMap = { "TX-001": true, "TX-002": true, "TX-003": true, "TX-004": true, "TX-005": true };

const TX_COLORS = {
    "TX-001": "#2563EB",
    "TX-002": "#06B6D4",
    "TX-003": "#EF4444",
    "TX-004": "#F59E0B",
    "TX-005": "#A855F7"
};

/* ============================================================
   PHASE 16: VIEW SWITCHING LOGIC
   ============================================================ */

function showView(viewId, element) {
    // Centralized mapping of navigation identifiers to canonical view IDs
    const viewMap = {
        overview: 'overview',
        sites: 'sites',
        assets: 'assets',
        risk: 'cascade', // Risk & Cascade view
        climate: 'climate',
        recommendations: 'predictive', // AI Recommendations map to Predictive view
        operations: 'decision', // Operations map to Decision Center
        'model-health': 'learning-p20', // Model Health maps to Learning Center
        settings: 'system', // Settings maps to System Architecture / OT Telemetry view
        // Legacy aliases for backward compatibility
        incidents: 'incidents-p19',
        facility: 'sites',
        'asset-risk': 'assets',
        'forecast-72h': 'predictive',
        action: 'decision'
    };
    const canonical = viewMap[viewId] || viewId;

    // Hide all view sections
    const sections = document.querySelectorAll('.view-section');
    sections.forEach(sec => sec.classList.remove('active'));

    // Deactivate all nav items
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(nav => nav.classList.remove('active'));

    // Show target section
    const targetSec = document.getElementById(`view-${canonical}`);
    if (targetSec) {
        targetSec.classList.add('active');
    } else {
        const overviewSec = document.getElementById('view-overview');
        if (overviewSec) overviewSec.classList.add('active');
    }

    // Set active nav item based on element or lookup
    if (element) {
        element.classList.add('active');
    } else {
        navItems.forEach(nav => {
            const onclick = nav.getAttribute('onclick') || '';
            if (onclick.includes(`'${viewId}'`) || onclick.includes(`'${canonical}'`)) {
                nav.classList.add('active');
            }
        });
    }

    // Refresh icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // Update Header Title
    const titleElem = document.getElementById('currentViewTitle');
    if (titleElem) {
        const titles = {
            overview: 'REGIONAL INFRASTRUCTURE OVERVIEW',
            sites: 'FACILITY NETWORK',
            assets: 'ASSET MONITORING — POWER TRANSFORMER, CHILLER & WATER PUMP',
            'incidents-p19': 'INCIDENT COMMAND CENTER',
            cascade: 'MULTI-INFRASTRUCTURE CASCADE RISK GRAPH',
            predictive: 'PREDICTIVE CLIMATE RISK',
            decision: 'DECISION CENTER',
            'learning-p20': 'AI LEARNING & ADAPTIVE INTELLIGENCE CENTER',
            climate: 'CLIMATE INTELLIGENCE',
            system: 'SYSTEM CONFIGURATION & DIAGNOSTICS',
            default: `${canonical.toUpperCase()} — COMMAND CENTER`
        };
        titleElem.textContent = titles[canonical] || titles['default'];
    }

    // Load view‑specific data
    if (canonical === 'overview') {
        loadOverviewData(currentSelectedSiteId);
    } else if (canonical === 'predictive') {
        loadPredictiveRiskData();
    } else if (canonical === 'decision') {
        loadDecisionCenterData();
    } else if (canonical === 'incidents-p19') {
        loadIncidentCenterData();
    } else if (canonical === 'climate') {
        fetchClimateIntelligence(currentSelectedSiteId);
    } else if (canonical === 'learning-p20') {
        loadLearningCenterData();
    } else if (canonical === 'cascade') {
        loadCascadeViewData();
    }


    // Refresh maps and charts when their container becomes visible
    if (typeof regionalMapInstance !== 'undefined' && regionalMapInstance && typeof regionalMapInstance.invalidateSize === 'function') {
        setTimeout(() => regionalMapInstance.invalidateSize(), 150);
    }
    if (typeof siteMap !== 'undefined' && siteMap && typeof siteMap.invalidateSize === 'function') {
        setTimeout(() => siteMap.invalidateSize(), 150);
    }
    if (typeof fleetTrendChart !== 'undefined' && fleetTrendChart && typeof fleetTrendChart.resize === 'function') {
        setTimeout(() => fleetTrendChart.resize(), 150);
    }
    if (typeof predictiveForecastChart !== 'undefined' && predictiveForecastChart && typeof predictiveForecastChart.resize === 'function') {
        setTimeout(() => predictiveForecastChart.resize(), 150);
    }
}



let currentOverviewSite = "CBE-001";
let lastLoadedOverviewSiteId = "CBE-001";
let lastOverviewClimateTime = 0;
let overviewClimateReqCounter = 0;

function navigateToPredictiveForPriority() {
    const prioritySiteId = lastLoadedOverviewSiteId || "CBE-001";
    showView('recommendations');
    handleSiteSelection(prioritySiteId);
}

async function loadOverviewClimate(siteId) {
    if (!siteId) return;

    let querySiteId = siteId;
    if (siteId === "ALL") {
        querySiteId = currentSelectedSiteId || "CBE-001";
    }

    const reqId = ++overviewClimateReqCounter;
    console.log(`[Overview Climate] Fetching weather for site: ${querySiteId} (Request #${reqId})`);

    const tempElem = document.getElementById('ovTempDisplay');
    const humElem = document.getElementById('ovHumidityDisplay');
    const rainElem = document.getElementById('ovRainDisplay');
    const windElem = document.getElementById('ovWindDisplay');
    const csBadge = document.getElementById('ovClimateStressBadge');

    if (tempElem) tempElem.textContent = "Loading...";
    if (humElem) humElem.textContent = "Loading...";
    if (rainElem) rainElem.textContent = "Loading...";
    if (windElem) windElem.textContent = "Loading...";
    if (csBadge) {
        csBadge.textContent = "Updating...";
        csBadge.className = "prov-badge badge-info";
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/climate-intelligence?site_id=${encodeURIComponent(querySiteId)}`);
        const data = await response.json();

        // Prevent stale responses from overwriting the UI
        if (reqId !== overviewClimateReqCounter) {
            console.log(`[Overview Climate] Ignoring stale weather response for request #${reqId} (current: #${overviewClimateReqCounter})`);
            return;
        }

        if (data.success && data.climate_intelligence) {
            const ci = data.climate_intelligence;
            const current = ci.current || {};

            if (tempElem) tempElem.textContent = `${current.temperature !== undefined ? current.temperature : '--'}°C`;
            if (humElem) humElem.textContent = `${current.humidity !== undefined ? current.humidity : '--'}%`;
            if (rainElem) rainElem.textContent = `${current.rain !== undefined ? current.rain : '--'} mm`;
            if (windElem) windElem.textContent = `${current.wind !== undefined ? current.wind : '--'} km/h`;

            if (csBadge) {
                const stressLevel = ci.overall_climate_stress > 50 ? "WATCH" : "NORMAL";
                csBadge.textContent = stressLevel;
                csBadge.className = `prov-badge ${stressLevel === 'WATCH' ? 'badge-warning' : 'badge-normal'}`;
            }

            // Keep hidden compatibility DOM elements updated
            const narElem = document.getElementById('ovClimateNarrative');
            if (narElem) {
                narElem.textContent = ci.explanation ? ci.explanation.join(' ') : "Current environmental conditions monitored.";
            }

            const wBadge = document.getElementById('ovWeatherProvBadge');
            if (wBadge) {
                wBadge.textContent = `WEATHER:  ${ci.source_status || 'LIVE'}`;
            }
        } else {
            throw new Error(data.error || "Response success = false");
        }
    } catch (err) {
        if (reqId === overviewClimateReqCounter) {
            if (tempElem) tempElem.textContent = "Unavailable";
            if (humElem) humElem.textContent = "Unavailable";
            if (rainElem) rainElem.textContent = "Unavailable";
            if (windElem) windElem.textContent = "Unavailable";
            if (csBadge) {
                csBadge.textContent = "ERROR";
                csBadge.className = "prov-badge badge-critical";
            }
            console.error("Error loading climate intelligence:", err);
        }
    }
}

async function loadOverviewData(siteId = null) {
    if (!siteId || siteId === "ALL") return;

    // Synchronize all facility selectors across other pages
    const dropdownIds = [
        "siteSelector",
        "predictiveFacilitySelector",
        "decisionFacilitySelector",
        "incP19FacilitySelector",
        "scenFacilitySelector",
        "climateFacilitySelector"
    ];
    dropdownIds.forEach(id => {
        const sel = document.getElementById(id);
        if (sel && sel.value !== siteId) {
            sel.value = siteId;
        }
    });
}

function onOverviewFacilityChange(siteId) {
    // Deprecated for passive observation on Overview
}

/* ============================================================
   FLEET MONITORING & ANALYSIS
   ============================================================ */

async function analyzeNextFleetSample() {
    const loadingElem = document.getElementById("loading");
    if (loadingElem && !fleetTimer) {
        loadingElem.classList.remove("hidden");
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/fleet-analyze`);
        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || "Fleet analysis failed");
        }

        fleetDataCache = result.transformers || [];
        fleetSummaryCache = result.summary || {};

        updateFleetDashboard();
        fetchFleetHistory();
        updateMultiAssetIntelligence();
        updateRealtimeAdapterStatus();

    } catch (error) {
        console.error("CascadeGuard Fleet API Error:", error);
        if (!fleetTimer) {
            alert("Unable to connect to CascadeGuard Fleet API.\n\n" + error.message);
        }
        stopFleetMonitoring();
    } finally {
        if (loadingElem) {
            loadingElem.classList.add("hidden");
        }
    }
}

async function updateMultiAssetIntelligence() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/multi-asset-analyze`);
        const result = await response.json();

        if (!result.success) return;

        const assets = result.assets || {};
        const system = result.system || {};
        const cascade = result.cascade || {};

        // Transformer
        const tx = assets.transformer || {};
        const elTxRisk = document.getElementById("maTxRisk");
        const elTxStatus = document.getElementById("maTxStatus");
        if (elTxRisk) elTxRisk.textContent = `${tx.risk || 0} / 100`;
        if (elTxStatus) {
            elTxStatus.textContent = tx.status || "NORMAL";
            elTxStatus.className = `ma-status-badge lvl-${tx.status || 'NORMAL'}`;
        }

        // Chiller
        const ch = assets.chiller || {};
        const elChRisk = document.getElementById("maChRisk");
        const elChStatus = document.getElementById("maChStatus");
        const elChFault = document.getElementById("maChFault");
        if (elChRisk) elChRisk.textContent = `${ch.risk || 0} / 100`;
        if (elChStatus) {
            elChStatus.textContent = ch.status || "NORMAL";
            elChStatus.className = `ma-status-badge lvl-${ch.status || 'NORMAL'}`;
        }
        if (elChFault) elChFault.textContent = `Fault Mode: ${ch.fault_description || 'Normal'}`;

        // Water Pump
        const wp = assets.water_pump || {};
        const elWpRisk = document.getElementById("maWpRisk");
        const elWpStatus = document.getElementById("maWpStatus");
        if (elWpRisk) elWpRisk.textContent = `${wp.risk || 0} / 100`;
        if (elWpStatus) {
            elWpStatus.textContent = "DECISION SUPPORT ONLY";
        }

        // System Cascade Risk
        const elSysRisk = document.getElementById("maSysRisk");
        const elSysLevel = document.getElementById("maSysLevel");
        if (elSysRisk) elSysRisk.textContent = `${system.system_cascade_risk || 0} / 100`;
        if (elSysLevel) elSysLevel.textContent = `SYSTEM LEVEL: ${system.level || 'NORMAL'}`;

        // Vulnerable Asset & Narrative
        const vuln = cascade.most_vulnerable_asset || {};
        const elVulnerAsset = document.getElementById("maVulnerAsset");
        const elNarrative = document.getElementById("maCascadeNarrative");
        if (elVulnerAsset) elVulnerAsset.textContent = `${vuln.asset || 'CHILLER'} (${vuln.name || ''})`;
        if (elNarrative) elNarrative.textContent = cascade.narrative || result.recommendation || "";

    } catch (err) {
        console.error("Multi-Asset Intelligence UI error:", err);
    }
}

function startFleetMonitoring() {
    if (fleetTimer) {
        clearInterval(fleetTimer);
        fleetTimer = null;
    }

    analyzeNextFleetSample();

    fleetTimer = setInterval(analyzeNextFleetSample, 5000);

    const btnStart = document.getElementById("btnStartFleet");
    const btnStop = document.getElementById("btnStopFleet");
    if (btnStart) btnStart.disabled = true;
    if (btnStop) btnStop.disabled = false;

    const statusElem = document.getElementById("metaStatus");
    if (statusElem) {
        statusElem.textContent = "STREAMING FLEET";
        statusElem.className = "status-streaming";
    }
}

function stopFleetMonitoring() {
    if (fleetTimer) {
        clearInterval(fleetTimer);
        fleetTimer = null;
    }

    const btnStart = document.getElementById("btnStartFleet");
    const btnStop = document.getElementById("btnStopFleet");
    if (btnStart) btnStart.disabled = false;
    if (btnStop) btnStop.disabled = true;

    const statusElem = document.getElementById("metaStatus");
    if (statusElem) {
        statusElem.textContent = "PAUSED";
        statusElem.className = "status-paused";
    }
}

async function resetFleetReplay() {
    stopFleetMonitoring();

    try {
        const response = await fetch(`${API_BASE_URL}/api/fleet/reset`, {
            method: "POST"
        });

        const result = await response.json();

        if (result.success) {
            analyzeNextFleetSample();
        } else {
            alert("Failed to reset fleet: " + (result.error || result.message));
        }
    } catch (error) {
        console.error("Reset Fleet Error:", error);
        alert("Error connecting to fleet reset API.");
    }
}

function exportFleetReport() {
    window.open(`${API_BASE_URL}/api/export-report?tx_id=${selectedDetailTxId || "TX-001"}&download=true`, "_blank");
}

async function fetchFleetHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/fleet-history`);
        const data = await response.json();
        if (data.success && data.history) {
            renderFleetTrendChart(data.history);
        }
    } catch (error) {
        console.error("Fetch Fleet History Error:", error);
    }
}

function updateFleetDashboard() {
    renderFleetSummary(fleetSummaryCache);
    renderTopPriorityPanel(fleetDataCache);
    renderFleetTable(fleetDataCache);
    renderFleetHeatmap(fleetDataCache);
    renderClimateOverview(fleetDataCache);

    if (selectedDetailTxId) {
        const tx = fleetDataCache.find(t => t.transformer_id === selectedDetailTxId);
        if (tx) renderTransformerDetailModal(tx);
    }
}

function renderFleetSummary(summary) {
    if (!summary) return;

    const totalMon = document.getElementById("fltTotalMonitored");
    if (totalMon) totalMon.textContent = summary.total_monitored || 5;

    const normCnt = document.getElementById("fltNormalCount");
    if (normCnt) normCnt.textContent = summary.normal_count || 0;

    const wtchCnt = document.getElementById("fltWatchCount");
    if (wtchCnt) wtchCnt.textContent = summary.watch_count || 0;

    const warnCnt = document.getElementById("fltWarningCount");
    if (warnCnt) warnCnt.textContent = summary.warning_count || 0;

    const critCnt = document.getElementById("fltCriticalCount");
    if (critCnt) critCnt.textContent = summary.critical_count || 0;

    const avgRisk = summary.fleet_risk !== undefined ? summary.fleet_risk.toFixed(1) : "--";
    const avgRiskEl = document.getElementById("fltAvgRisk");
    if (avgRiskEl) avgRiskEl.textContent = `${avgRisk} / 100`;

    const avgLvlEl = document.getElementById("fltAvgRiskLevel");
    if (avgLvlEl) avgLvlEl.textContent = summary.fleet_status || "LOW";

    const h = summary.highest_risk_transformer;
    if (h) {
        const hTxElem = document.getElementById("fltHighestRisk");
        const hScoreElem = document.getElementById("fltHighestRiskScore");
        if (hTxElem) hTxElem.textContent = h.transformer_id;
        if (hScoreElem) hScoreElem.textContent = `Score: ${h.score.toFixed(1)} (${h.level})`;
    }

    const stateBadge = document.getElementById("fleetStateBadge");
    if (stateBadge) {
        stateBadge.textContent = `SITES: ${siteRegistryCache.length || summary.total_monitored || 5} MONITORED`;
        stateBadge.className = `badge-ew ew-${(summary.fleet_status || "NORMAL").toLowerCase()}`;
    }
}

function renderTopPriorityPanel(fleetList) {
    if (!fleetList || fleetList.length === 0) return;

    const topTx = fleetList[0];

    const nameEl = document.getElementById("prioTxName");
    const locEl = document.getElementById("prioTxLoc");
    const curScEl = document.getElementById("prioCurrentScore");
    const fc60El = document.getElementById("prioForecastScore");
    const ewEl = document.getElementById("prioEarlyWarning");

    if (nameEl) nameEl.textContent = `${topTx.transformer_id} — ${topTx.display_name}`;
    if (locEl) locEl.textContent = `Location: ${topTx.location} | Priority Rank #1`;
    if (curScEl) curScEl.textContent = `${topTx.cascade.score.toFixed(1)} / 100`;
    
    const fc60 = topTx.predictive_forecast?.forecast?.["60m"]?.cascade_score;
    if (fc60El) fc60El.textContent = fc60 !== undefined ? `${fc60.toFixed(1)} / 100` : "--";

    const ew = topTx.explainability?.early_warning_state || "NORMAL";
    if (ewEl) {
        ewEl.textContent = ew;
        ewEl.className = `hz-level ew-${ew.toLowerCase()}`;
    }

    const topFactors = topTx.explainability?.top_factors || [];
    const factorEl = document.getElementById("prioRiskFactor");
    if (factorEl) {
        if (topFactors.length > 0) {
            factorEl.textContent = `${topFactors[0].description} (SHAP ${topFactors[0].shap_value > 0 ? '+' : ''}${topFactors[0].shap_value})`;
        } else {
            factorEl.textContent = "Operational telemetry stable.";
        }
    }

    const actEl = document.getElementById("prioActionText");
    if (actEl) actEl.textContent = topTx.decision_support?.detailed_guidance || topTx.recommendation || "Continue normal monitoring.";

    renderAnalyticsShapFactors(topFactors);
}

function renderAnalyticsShapFactors(topFactors) {
    const container = document.getElementById("prioShapFactorsList");
    if (!container) return;

    if (!topFactors || topFactors.length === 0) {
        container.innerHTML = `<p style="color:var(--text-muted); font-size:13px;">No elevated risk factors detected in current operational window.</p>`;
        return;
    }

    const maxAbs = Math.max(...topFactors.map(f => f.abs_shap), 0.01);
    let html = "";

    topFactors.forEach(f => {
        const pct = Math.min(Math.round((f.abs_shap / maxAbs) * 100), 100);
        const isInc = f.direction === "increases_risk";
        const barColor = isInc ? "#F59E0B" : "#2563EB";
        const dirLabel = isInc ? "Increasing Risk" : "Decreasing Risk";

        html += `
            <div class="shap-factor-row">
                <div class="shap-factor-header">
                    <strong>${f.description} (<code>${f.feature}</code> = ${f.value})</strong>
                    <span style="color: ${barColor}; font-weight: 600;">${dirLabel} (${f.shap_value > 0 ? '+' : ''}${f.shap_value})</span>
                </div>
                <div class="shap-bar-bg">
                    <div class="shap-bar-fill" style="width: ${pct}%; background-color: ${barColor};"></div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderFleetTable(fleetList) {
    const tbody = document.getElementById("fleetTableBody");
    if (!tbody) return;

    if (!fleetList || fleetList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="12" style="text-align: center; color: var(--text-muted);">No active fleet data.</td></tr>`;
        return;
    }

    let html = "";
    fleetList.forEach(tx => {
        const score = tx.cascade.score;
        const level = tx.cascade.level;
        const trend = tx.explainability?.trend || "STABLE";
        const fc60 = tx.predictive_forecast?.forecast?.["60m"]?.cascade_score?.toFixed(1) || "--";
        const statusClass = `badge-ew ew-${level.toLowerCase()}`;
        const trendClass = `badge-trend trend-${trend.toLowerCase()}`;

        html += `
            <tr onclick="openTransformerDetail('${tx.transformer_id}')" style="cursor:pointer;">
                <td><strong>#${tx.priority_rank}</strong></td>
                <td><code>${tx.transformer_id}</code></td>
                <td><strong>${tx.display_name}</strong></td>
                <td>${tx.location}</td>
                <td>${tx.health.risk.toFixed(1)}</td>
                <td>${tx.operational.risk.toFixed(1)}%</td>
                <td>${tx.climate.climate_stress.toFixed(1)}</td>
                <td><strong>${score.toFixed(1)}</strong></td>
                <td><strong>${fc60}</strong></td>
                <td><span class="${trendClass}">${trend}</span></td>
                <td><span class="${statusClass}">${level}</span></td>
                <td><button onclick="event.stopPropagation(); openTransformerDetail('${tx.transformer_id}')" class="btn-primary" style="padding:4px 8px; font-size:10px;">INSPECT</button></td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

function renderFleetHeatmap(fleetList) {
    const container = document.getElementById("fleetHeatmapGrid");
    if (!container) return;

    if (!fleetList || fleetList.length === 0) {
        container.innerHTML = `<p style="color:var(--text-muted);">Waiting for fleet telemetry...</p>`;
        return;
    }

    let html = "";
    fleetList.forEach(tx => {
        const score = tx.cascade.score;
        const level = tx.cascade.level;
        const ew = tx.explainability?.early_warning_state || "NORMAL";
        const fc60 = tx.predictive_forecast?.forecast?.["60m"]?.cascade_score?.toFixed(1) || "--";

        html += `
            <div class="hm-card" onclick="openTransformerDetail('${tx.transformer_id}')" style="background:var(--bg-secondary); border:1px solid var(--border-color); padding:12px; border-radius:6px; cursor:pointer;">
                <div style="display:flex; justify-content:space-between;">
                    <code>${tx.transformer_id}</code>
                    <span style="font-size:11px; color:var(--text-muted);">Rank #${tx.priority_rank}</span>
                </div>
                <h4 style="margin:4px 0 2px;">${tx.display_name}</h4>
                <small style="color:var(--text-muted);">${tx.location}</small>
                
                <div style="font-size:22px; font-weight:800; margin:8px 0;">${score.toFixed(1)} <span style="font-size:12px;">/ 100</span></div>

                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span class="badge-ew ew-${ew.toLowerCase()}">${ew}</span>
                    <small style="color:var(--text-muted);">+60m: ${fc60}</small>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderClimateOverview(fleetList) {
    const container = document.getElementById("climateFleetGrid");
    if (!container) return;

    if (!fleetList || fleetList.length === 0) return;

    let html = "";
    fleetList.forEach(tx => {
        const c = tx.climate;
        html += `
            <div class="climate-card" style="background:var(--bg-secondary); border:1px solid var(--border-color); padding:12px; border-radius:6px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                    <strong>${tx.location}</strong>
                    <small style="color:var(--text-muted);">TX: ${tx.transformer_id}</small>
                </div>
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:6px; text-align:center;">
                    <div><small style="color:var(--text-muted);">STRESS</small><strong style="display:block;">${c.climate_stress}</strong></div>
                    <div><small style="color:var(--text-muted);">TEMP</small><strong style="display:block;">${c.temperature}°C</strong></div>
                    <div><small style="color:var(--text-muted);">RAIN</small><strong style="display:block;">${c.rain}mm</strong></div>
                    <div><small style="color:var(--text-muted);">WIND</small><strong style="display:block;">${c.wind}km/h</strong></div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderFleetTrendChart(historyMap) {
    const canvas = document.getElementById("fleetTrendChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    const width = canvas.clientWidth || 650;
    const height = canvas.clientHeight || 180;

    canvas.width = width;
    canvas.height = height;

    ctx.clearRect(0, 0, width, height);

    ctx.strokeStyle = "#1E293B";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#94A3B8";
    ctx.font = "10px sans-serif";

    const padding = 35;
    const chartW = width - padding * 2;
    const chartH = height - padding * 2;

    [0, 25, 50, 75, 100].forEach(val => {
        const y = height - padding - (val / 100) * chartH;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
        ctx.fillText(val.toString(), 5, y + 3);
    });

    Object.keys(historyMap).forEach(txId => {
        if (!visibleTxMap[txId]) return;

        const history = historyMap[txId];
        if (!history || history.length < 2) return;

        const step = chartW / (history.length - 1);
        ctx.beginPath();
        ctx.strokeStyle = TX_COLORS[txId] || "#2563EB";
        ctx.lineWidth = 2;

        history.forEach((pt, i) => {
            const x = padding + i * step;
            const y = height - padding - (pt.cascade_score / 100) * chartH;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        const lastPt = history[history.length - 1];
        const lastX = padding + (history.length - 1) * step;
        const lastY = height - padding - (lastPt.cascade_score / 100) * chartH;

        ctx.beginPath();
        ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
        ctx.fillStyle = TX_COLORS[txId] || "#2563EB";
        ctx.fill();
    });
}

function openTransformerDetail(txId) {
    selectedDetailTxId = txId;
    const tx = fleetDataCache.find(t => t.transformer_id === txId);
    
    if (tx) {
        renderTransformerDetailModal(tx);
        document.getElementById("detailModal").classList.remove("hidden");
    } else {
        fetch(`${API_BASE_URL}/api/transformer/${txId}`)
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    renderTransformerDetailModal(data);
                    document.getElementById("detailModal").classList.remove("hidden");
                }
            });
    }
}

function closeTransformerDetail() {
    selectedDetailTxId = null;
    document.getElementById("detailModal").classList.add("hidden");
}

function renderTransformerDetailModal(tx) {
    const txIdElem = document.getElementById("dtlTxId");
    const txNameElem = document.getElementById("dtlTxName");
    const txLocElem = document.getElementById("dtlTxLoc");

    if (txIdElem) txIdElem.textContent = tx.transformer_id;
    if (txNameElem) txNameElem.textContent = tx.display_name;
    if (txLocElem) txLocElem.textContent = `Location: ${tx.location} | Timestamp: ${tx.timestamp}`;

    const scBadge = document.getElementById("dtlScenarioBadge");
    if (scBadge) {
        scBadge.textContent = `SCENARIO: ${tx.scenario?.name || "NORMAL"}`;
    }

    const casSc = document.getElementById("dtlCascadeScore");
    if (casSc) casSc.textContent = `${tx.cascade.score.toFixed(1)} / 100`;

    const hRisk = document.getElementById("dtlHealthRisk");
    if (hRisk) hRisk.textContent = tx.health.risk.toFixed(1);

    const opRisk = document.getElementById("dtlOpRisk");
    if (opRisk) opRisk.textContent = `${tx.operational.risk.toFixed(1)} %`;

    const clStress = document.getElementById("dtlClimateStress");
    if (clStress) clStress.textContent = tx.climate.climate_stress.toFixed(1);

    const topFactors = tx.explainability?.top_factors || [];
    renderDetailTopFactors(topFactors);

    const recElem = document.getElementById("dtlRecommendation");
    if (recElem) recElem.textContent = tx.decision_support?.detailed_guidance || tx.recommendation || "Continue normal monitoring.";
}

function renderDetailTopFactors(factors) {
    const container = document.getElementById("dtlShapContainer");
    if (!container) return;

    if (!factors || factors.length === 0) {
        container.innerHTML = `<p style="color:var(--text-muted); font-size:12px;">No active risk factors reported.</p>`;
        return;
    }

    const maxShap = Math.max(...factors.map(f => f.abs_shap), 0.01);

    let html = "";
    factors.forEach((f, idx) => {
        const barPct = Math.min(Math.round((f.abs_shap / maxShap) * 100), 100);
        const isInc = f.direction === "increases_risk";
        const dirText = isInc ? "Increasing Risk" : "Decreasing Risk";
        const barColor = isInc ? "#F59E0B" : "#2563EB";

        html += `
            <div style="margin-bottom: 8px;">
                <div style="display:flex; justify-content:space-between; font-size:12px;">
                    <span>${idx + 1}. ${f.description}</span>
                    <span style="color:${barColor}; font-weight:600;">${dirText} (${f.shap_value > 0 ? '+' : ''}${f.shap_value})</span>
                </div>
                <div class="shap-bar-bg" style="margin-top:2px;">
                    <div class="shap-bar-fill" style="width: ${barPct}%; background-color: ${barColor};"></div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

async function updateRealtimeAdapterStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/realtime-status`);
        const result = await response.json();
        if (!result.success) return;

        const txSt = document.getElementById("txAdapterStatus");
        const chSt = document.getElementById("chAdapterStatus");
        const wpSt = document.getElementById("wpAdapterStatus");
        const tsSt = document.getElementById("freshnessTimestamp");

        if (txSt) txSt.innerText = result.transformer ? result.transformer.status : "Historical Replay";
        if (chSt) chSt.innerText = result.chiller ? result.chiller.status : "Historical Dataset";
        if (wpSt) wpSt.innerText = result.water_pump ? result.water_pump.status + " (Decision Support)" : "Dataset (Decision Support)";
        if (tsSt) tsSt.innerText = `Updated: ${result.timestamp || "Just Now"}`;

    } catch (e) {
        console.error("Realtime Adapter Status Fetch Note:", e);
    }
}

let currentScenarioName = "NORMAL";

async function runClimateScenario(scenarioName, btnElem) {
    currentScenarioName = scenarioName;
    if (btnElem) {
        document.querySelectorAll(".btn-scenario").forEach(b => b.classList.remove("active"));
        btnElem.classList.add("active");
    }

    try {
        const response = await fetch(`${API_BASE_URL}/api/scenario-analyze`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario: scenarioName, site_id: currentSelectedSiteId })
        });

        const result = await response.json();
        if (!result.success) return;

        const cascade = result.cascade || {};
        const weather = result.weather || {};
        const assets = result.assets || {};

        const bRiskElem = document.getElementById("scenBaseRisk");
        const sRiskElem = document.getElementById("scenSimRisk");
        const deltaElem = document.getElementById("scenDelta");
        const tagElem = document.getElementById("scenLevelTag");
        const recElem = document.getElementById("scenRecommendationText");

        if (bRiskElem) bRiskElem.innerText = `${cascade.baseline_risk} / 100`;
        if (sRiskElem) sRiskElem.innerText = `${cascade.scenario_risk} / 100`;
        if (deltaElem) {
            const chg = cascade.change;
            deltaElem.innerText = chg > 0 ? `+${chg}` : `${chg}`;
        }

        if (tagElem) {
            tagElem.innerText = cascade.level || "NORMAL";
        }

        if (recElem) recElem.innerText = result.recommendation || "";

        const fnClim = document.getElementById("fnClimate");
        const fnPump = document.getElementById("fnPump");
        const fnCh = document.getElementById("fnChiller");
        const fnTx = document.getElementById("fnTx");
        const fnSys = document.getElementById("fnSystem");

        if (fnClim) fnClim.innerText = `${weather.scenario ? weather.scenario.climate_stress : '--'} / 100`;
        if (fnPump) fnPump.innerText = `${assets.water_pump ? assets.water_pump.risk : '--'} / 100 (DS)`;
        if (fnCh) fnCh.innerText = `${assets.chiller ? assets.chiller.risk : '--'} / 100`;
        if (fnTx) fnTx.innerText = `${assets.transformer ? assets.transformer.risk : '--'} / 100`;
        if (fnSys) fnSys.innerText = `${cascade.scenario_risk || '--'} / 100`;

    } catch (e) {
        console.error("Climate Scenario Execution Error:", e);
    }
}

/* SITE LOCATION CONFIGURATION & MAP LOGIC */
let siteMap = null;
let siteMarker = null;

function initSiteMap(lat, lon) {
    if (typeof L === "undefined") return;

    const mapContainer = document.getElementById("siteMapContainer");
    if (!mapContainer) return;

    if (!siteMap) {
        siteMap = L.map('siteMapContainer', { attributionControl: false }).setView([lat, lon], 12);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18
        }).addTo(siteMap);

        siteMarker = L.marker([lat, lon], { draggable: true }).addTo(siteMap);

        siteMarker.on('dragend', function (e) {
            const pos = e.target.getLatLng();
            const latInp = document.getElementById("siteInputLat");
            const lonInp = document.getElementById("siteInputLon");
            if (latInp) latInp.value = pos.lat.toFixed(5);
            if (lonInp) lonInp.value = pos.lng.toFixed(5);
        });
    } else {
        siteMap.setView([lat, lon], 12);
        siteMarker.setLatLng([lat, lon]);
    }
}

function onCoordsInputChange() {
    const latInp = parseFloat(document.getElementById("siteInputLat").value);
    const lonInp = parseFloat(document.getElementById("siteInputLon").value);
    if (!isNaN(latInp) && !isNaN(lonInp)) {
        if (siteMap && siteMarker) {
            siteMap.setView([latInp, lonInp], 12);
            siteMarker.setLatLng([latInp, lonInp]);
        }
    }
}

async function locateSite() {
    const searchVal = document.getElementById("siteInputSearch").value.trim();
    if (!searchVal) return;

    try {
        const geoUrl = `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(searchVal)}&count=1&language=en&format=json`;
        const res = await fetch(geoUrl);
        const geo = await res.json();

        if (geo.results && geo.results.length > 0) {
            const place = geo.results[0];
            const lat = parseFloat(place.latitude);
            const lon = parseFloat(place.longitude);

            document.getElementById("siteInputLat").value = lat.toFixed(5);
            document.getElementById("siteInputLon").value = lon.toFixed(5);

            const nameInp = document.getElementById("siteInputName");
            if (nameInp && (!nameInp.value || nameInp.value.includes("Facility"))) {
                nameInp.value = `${place.name} Industrial Facility`;
            }

            initSiteMap(lat, lon);
        } else {
            alert(`Location '${searchVal}' not found. Please enter exact latitude and longitude manually.`);
        }
    } catch (e) {
        console.error("Geocoding lookup exception:", e);
    }
}

let isAddFacilityMode = false;
let siteRegistryCache = [];

function showFormNotification(msg, isError = false) {
    const el = document.getElementById("siteFormNotification");
    if (!el) return;
    if (!msg) {
        el.style.display = "none";
        el.innerText = "";
        return;
    }
    el.style.display = "block";
    el.style.background = isError ? "rgba(239, 68, 68, 0.15)" : "rgba(34, 197, 94, 0.15)";
    el.style.border = isError ? "1px solid #EF4444" : "1px solid #22C55E";
    el.style.color = isError ? "#FCA5A5" : "#86EFAC";
    el.innerText = msg;
}

// Reusable Facility Data-Access Layer (Requirement 9)
function getFacilities() {
    return siteRegistryCache;
}

function getFacilityById(siteId) {
    return siteRegistryCache.find(s => s.site_id === siteId) || null;
}

function getMonitoredFacilities() {
    return siteRegistryCache.filter(s => s.status === "ACTIVE" || s.status === "MONITORED");
}

function getAssetForFacility(siteId, assetType) {
    const site = getFacilityById(siteId);
    if (!site) return null;
    if (assetType === "transformer") return site.transformer_id || (site.asset_ids ? site.asset_ids.transformer : null);
    if (assetType === "chiller") return site.chiller_id || (site.asset_ids ? site.asset_ids.chiller : null);
    if (assetType === "water_pump") return site.water_pump_id || (site.asset_ids ? site.asset_ids.water_pump : null);
    return null;
}

async function fetchSiteRegistry() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/sites`);
        const data = await res.json();
        if (data.success && Array.isArray(data.sites)) {
            siteRegistryCache = data.sites;
            populateFacilityDropdowns(siteRegistryCache);
            
            // Dynamically update site count in the top header (Requirement 1, 3)
            const stateBadge = document.getElementById("fleetStateBadge");
            if (stateBadge) {
                stateBadge.textContent = `SITES: ${siteRegistryCache.length} MONITORED`;
            }
            
            const exists = siteRegistryCache.some(s => s.site_id === currentSelectedSiteId);
            if (!exists && siteRegistryCache.length > 0) {
                currentSelectedSiteId = siteRegistryCache[0].site_id;
            }
            
            updateFacilityDetailsPanel();
        }
    } catch (err) {
        console.error("fetchSiteRegistry error:", err);
    }
}

function populateFacilityDropdowns(sites) {
    const dropdownIds = [
        "ovFacilitySelect",
        "siteSelector",
        "predictiveFacilitySelector",
        "decisionFacilitySelector",
        "incP19FacilitySelector",
        "scenFacilitySelector",
        "climateFacilitySelector",
        "cascadeFacilitySelector"
    ];


    dropdownIds.forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;

        const currentVal = select.value || currentSelectedSiteId;
        select.innerHTML = "";

        sites.forEach(site => {
            const opt = document.createElement("option");
            opt.value = site.site_id;
            opt.textContent = `${site.site_name} (${site.site_id}) - ${site.city}`;
            select.appendChild(opt);
        });

        if (sites.some(s => s.site_id === currentVal)) {
            select.value = currentVal;
        } else if (sites.length > 0) {
            select.value = sites[0].site_id;
        }
    });
}

function updateFacilityDetailsPanel(siteObj = null) {
    const site = siteObj || siteRegistryCache.find(s => s.site_id === currentSelectedSiteId);
    if (!site) return;

    const sName = document.getElementById("hdrSiteName");
    const sId = document.getElementById("hdrSiteId");
    const sCity = document.getElementById("hdrSiteCity");
    const sCoords = document.getElementById("hdrCoordinates");
    const sAssets = document.getElementById("hdrConnectedAssets");

    if (sName) sName.innerText = site.site_name || "--";
    if (sId) sId.innerText = site.site_id || "--";
    if (sCity) sCity.innerText = site.city || "--";
    if (sCoords && site.latitude !== undefined && site.longitude !== undefined) {
        sCoords.innerText = `${site.latitude}, ${site.longitude}`;
    }
    if (sAssets) {
        const tx = site.transformer_id || (site.asset_ids ? site.asset_ids.transformer : "TR-001");
        const ch = site.chiller_id || (site.asset_ids ? site.asset_ids.chiller : "CH-001");
        const wp = site.water_pump_id || (site.asset_ids ? site.asset_ids.water_pump : "WP-001");
        sAssets.innerText = `TX: ${tx} | CH: ${ch} | WP: ${wp}`;
    }

    // Refresh IoT device registry list
    loadIotRegistryData(site.site_id);
}

function openAddFacilityForm() {
    isAddFacilityMode = true;
    showFormNotification(null);

    const titleEl = document.getElementById("siteFormTitle");
    const badgeEl = document.getElementById("siteFormModeBadge");
    const saveBtn = document.getElementById("btnSaveFacility");
    const delBtn = document.getElementById("btnDeleteFacility");

    // Toggle header button classes
    const headerAddBtn = document.getElementById("headerAddFacilityBtn");
    const headerEditBtn = document.getElementById("headerEditFacilityBtn");
    if (headerAddBtn) {
        headerAddBtn.classList.remove("btn-secondary");
        headerAddBtn.classList.add("btn-primary");
    }
    if (headerEditBtn) {
        headerEditBtn.classList.remove("btn-primary");
        headerEditBtn.classList.add("btn-secondary");
    }

    if (titleEl) titleEl.innerText = "FACILITY REGISTRY — ADD NEW FACILITY";
    if (badgeEl) {
        badgeEl.innerText = "ADD NEW FACILITY MODE";
        badgeEl.className = "prov-badge pred-sim";
    }
    if (saveBtn) saveBtn.innerText = "SAVE NEW FACILITY";
    if (delBtn) delBtn.style.display = "none";

    const inputId = document.getElementById("siteInputId");
    const inputName = document.getElementById("siteInputName");
    const inputCity = document.getElementById("siteInputCity");
    const inputLat = document.getElementById("siteInputLat");
    const inputLon = document.getElementById("siteInputLon");
    const inputTx = document.getElementById("siteInputTx");
    const inputCh = document.getElementById("siteInputCh");
    const inputWp = document.getElementById("siteInputWp");

    if (inputId) { inputId.value = ""; inputId.disabled = false; inputId.focus(); }
    if (inputName) inputName.value = "";
    if (inputCity) inputCity.value = "";
    if (inputLat) inputLat.value = "11.00555";
    if (inputLon) inputLon.value = "76.96612";
    if (inputTx) inputTx.value = "";
    if (inputCh) inputCh.value = "";
    if (inputWp) inputWp.value = "";
}

function setEditFacilityMode(site, keepNotification = false) {
    isAddFacilityMode = false;
    if (!keepNotification) {
        showFormNotification(null);
    }

    const titleEl = document.getElementById("siteFormTitle");
    const badgeEl = document.getElementById("siteFormModeBadge");
    const saveBtn = document.getElementById("btnSaveFacility");
    const delBtn = document.getElementById("btnDeleteFacility");

    // Toggle header button classes
    const headerAddBtn = document.getElementById("headerAddFacilityBtn");
    const headerEditBtn = document.getElementById("headerEditFacilityBtn");
    if (headerAddBtn) {
        headerAddBtn.classList.remove("btn-primary");
        headerAddBtn.classList.add("btn-secondary");
    }
    if (headerEditBtn) {
        headerEditBtn.classList.remove("btn-secondary");
        headerEditBtn.classList.add("btn-primary");
    }

    if (titleEl) titleEl.innerText = "FACILITY REGISTRY EDIT";
    if (badgeEl) {
        badgeEl.innerText = "EDIT MODE";
        badgeEl.className = "prov-badge live-weather";
    }
    if (saveBtn) saveBtn.innerText = "SAVE FACILITY CONFIGURATION";
    if (delBtn) delBtn.style.display = "inline-block";

    const inputId = document.getElementById("siteInputId");
    const inputName = document.getElementById("siteInputName");
    const inputCity = document.getElementById("siteInputCity");
    const inputLat = document.getElementById("siteInputLat");
    const inputLon = document.getElementById("siteInputLon");
    const inputTx = document.getElementById("siteInputTx");
    const inputCh = document.getElementById("siteInputCh");
    const inputWp = document.getElementById("siteInputWp");

    if (site) {
        if (inputId) { inputId.value = site.site_id; inputId.disabled = true; }
        if (inputName) inputName.value = site.site_name;
        if (inputCity) inputCity.value = site.city;
        if (inputLat) inputLat.value = site.latitude;
        if (inputLon) inputLon.value = site.longitude;
        if (inputTx) inputTx.value = site.transformer_id || (site.asset_ids ? site.asset_ids.transformer : "");
        if (inputCh) inputCh.value = site.chiller_id || (site.asset_ids ? site.asset_ids.chiller : "");
        if (inputWp) inputWp.value = site.water_pump_id || (site.asset_ids ? site.asset_ids.water_pump : "");
    }
}

function enterEditModeForCurrent() {
    if (siteRegistryCache && siteRegistryCache.length > 0) {
        const currentSite = siteRegistryCache.find(s => s.site_id === currentSelectedSiteId) || siteRegistryCache[0];
        setEditFacilityMode(currentSite);
    }
}

async function saveFacilityForm() {
    showFormNotification(null);

    const siteId = document.getElementById("siteInputId") ? document.getElementById("siteInputId").value.trim() : "";
    const siteName = document.getElementById("siteInputName") ? document.getElementById("siteInputName").value.trim() : "";
    const city = document.getElementById("siteInputCity") ? document.getElementById("siteInputCity").value.trim() : "";
    const latRaw = document.getElementById("siteInputLat") ? document.getElementById("siteInputLat").value : "";
    const lonRaw = document.getElementById("siteInputLon") ? document.getElementById("siteInputLon").value : "";
    const txId = document.getElementById("siteInputTx") ? document.getElementById("siteInputTx").value.trim() : "";
    const chId = document.getElementById("siteInputCh") ? document.getElementById("siteInputCh").value.trim() : "";
    const wpId = document.getElementById("siteInputWp") ? document.getElementById("siteInputWp").value.trim() : "";

    // Validation checks
    if (!siteId) {
        showFormNotification("Site ID is required.", true);
        return;
    }
    if (!siteName) {
        showFormNotification("Site Name is required.", true);
        return;
    }
    if (!city) {
        showFormNotification("City is required.", true);
        return;
    }

    if (latRaw === "" || isNaN(parseFloat(latRaw))) {
        showFormNotification("Latitude must be numeric.", true);
        return;
    }
    const lat = parseFloat(latRaw);
    if (lat < -90 || lat > 90) {
        showFormNotification("Latitude must be between -90 and 90.", true);
        return;
    }

    if (lonRaw === "" || isNaN(parseFloat(lonRaw))) {
        showFormNotification("Longitude must be numeric.", true);
        return;
    }
    const lon = parseFloat(lonRaw);
    if (lon < -180 || lon > 180) {
        showFormNotification("Longitude must be between -180 and 180.", true);
        return;
    }

    if (!txId) {
        showFormNotification("Transformer ID is required.", true);
        return;
    }
    if (!chId) {
        showFormNotification("Chiller ID is required.", true);
        return;
    }
    if (!wpId) {
        showFormNotification("Water Pump ID is required.", true);
        return;
    }

    if (isAddFacilityMode) {
        const existing = siteRegistryCache.find(s => s.site_id.toLowerCase() === siteId.toLowerCase());
        if (existing) {
            showFormNotification("A facility with this Site ID already exists.", true);
            return;
        }
    }

    const saveBtn = document.getElementById("btnSaveFacility");
    const origBtnText = saveBtn ? saveBtn.innerText : "";
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerText = "Saving...";
    }

    const payload = {
        site_id: siteId,
        site_name: siteName,
        city: city,
        latitude: lat,
        longitude: lon,
        transformer_id: txId,
        chiller_id: chId,
        water_pump_id: wpId
    };

    try {
        const url = isAddFacilityMode ? `${API_BASE_URL}/api/sites` : `${API_BASE_URL}/api/sites/${siteId}`;
        const method = isAddFacilityMode ? "POST" : "PUT";

        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const result = await res.json();
        if (!res.ok || !result.success) {
            const errDetail = result.error || result.detail || "Failed to save facility configuration.";
            showFormNotification(errDetail, true);
            return;
        }

        showFormNotification(`Facility '${siteId}' saved successfully.`, false);
        currentSelectedSiteId = siteId;
        isAddFacilityMode = false;

        await fetchSiteRegistry();
        handleSiteSelection(siteId, true);

    } catch (err) {
        console.error("Save facility error:", err);
        showFormNotification("Network error while saving facility.", true);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerText = origBtnText;
        }
    }
}

async function confirmSite() {
    await saveFacilityForm();
}

async function deleteSelectedFacility() {
    if (!currentSelectedSiteId) return;
    if (!confirm(`Are you sure you want to delete facility '${currentSelectedSiteId}'?`)) return;

    try {
        const res = await fetch(`${API_BASE_URL}/api/sites/${currentSelectedSiteId}`, { method: "DELETE" });
        const result = await res.json();

        if (!result.success) {
            showFormNotification(result.error || "Failed to delete facility.", true);
            return;
        }

        showFormNotification(`Facility '${currentSelectedSiteId}' deleted.`, false);
        await fetchSiteRegistry();
        if (siteRegistryCache.length > 0) {
            handleSiteSelection(siteRegistryCache[0].site_id);
        }
    } catch (err) {
        console.error("Delete facility error:", err);
        showFormNotification("Network error while deleting facility.", true);
    }
}

function updateHeaderSiteBanner(site) {
    updateFacilityDetailsPanel(site);
}

async function fetchSiteConfig() {
    await fetchSiteRegistry();
}

let currentSelectedSiteId = "CBE-001";

let climateTelemetryTimer = null;
let climateTelemetryData = {
    transformer: { oil_temperature: 78.4, winding_temperature: 82.1, load_pct: 74, status: "NORMAL" },
    chiller: { supply_temperature: 7.2, return_temperature: 12.8, load_pct: 68, cop: 4.5 },
    water_pump: { motor_temperature: 54.2, flow_rate: 82, load_pct: 61, status: "NORMAL" }
};

function initClimateTelemetryData() {
    climateTelemetryData = {
        transformer: { oil_temperature: 78.4, winding_temperature: 82.1, load_pct: 74, status: "NORMAL" },
        chiller: { supply_temperature: 7.2, return_temperature: 12.8, load_pct: 68, cop: 4.5 },
        water_pump: { motor_temperature: 54.2, flow_rate: 82, load_pct: 61, status: "NORMAL" }
    };
}

async function simulateClimateTelemetry(siteId) {
    if (!siteId) return;
    try {
        const res = await fetch(`${API_BASE_URL}/api/facilities/${siteId}/telemetry`);
        const result = await res.json();
        if (result.success && result.telemetry && result.telemetry.assets) {
            climateTelemetryData = result.telemetry.assets;
            updateClimateTelemetryDOM(siteId);
        }
    } catch (err) {
        console.error("Fetch simulated telemetry error:", err);
    }
}

function updateClimateTelemetryDOM(siteId) {
    const site = siteRegistryCache.find(s => s.site_id === siteId) || {};
    const txId = site.transformer_id || (site.asset_ids ? site.asset_ids.transformer : "TX-001");
    const chId = site.chiller_id || (site.asset_ids ? site.asset_ids.chiller : "CH-001");
    const wpId = site.water_pump_id || (site.asset_ids ? site.asset_ids.water_pump : "WP-001");

    const txIdEl = document.getElementById("ciAssetTxId");
    const chIdEl = document.getElementById("ciAssetChId");
    const wpIdEl = document.getElementById("ciAssetWpId");

    if (txIdEl) txIdEl.textContent = txId;
    if (chIdEl) chIdEl.textContent = chId;
    if (wpIdEl) wpIdEl.textContent = wpId;

    const txOil = document.getElementById("ciAssetTxOilTemp");
    const txWind = document.getElementById("ciAssetTxWindingTemp");
    const txLoad = document.getElementById("ciAssetTxLoad");
    const txCooling = document.getElementById("ciAssetTxCooling");

    if (climateTelemetryData.transformer) {
        const tx = climateTelemetryData.transformer;
        if (txOil) txOil.textContent = `${(tx.oil_temperature || 0).toFixed(1)} °C`;
        if (txWind) txWind.textContent = `${(tx.winding_temperature || 0).toFixed(1)} °C`;
        if (txLoad) txLoad.textContent = `${(tx.load_pct || 0)}%`;
        if (txCooling) txCooling.textContent = "SIMULATED";
    }

    const chSupply = document.getElementById("ciAssetChSupplyTemp");
    const chReturn = document.getElementById("ciAssetChReturnTemp");
    const chComp = document.getElementById("ciAssetChCompressorLoad");
    const chEff = document.getElementById("ciAssetChEfficiency");

    if (climateTelemetryData.chiller) {
        const ch = climateTelemetryData.chiller;
        if (chSupply) chSupply.textContent = `${(ch.supply_temperature || 0).toFixed(1)} °C`;
        if (chReturn) chReturn.textContent = `${(ch.return_temperature || 0).toFixed(1)} °C`;
        if (chComp) chComp.textContent = `${(ch.load_pct || 0)}%`;
        if (chEff) chEff.textContent = `${((ch.cop || 4.0) * 20).toFixed(0)}%`;
    }

    const wpMotor = document.getElementById("ciAssetWpMotorTemp");
    const wpFlow = document.getElementById("ciAssetWpFlowRate");
    const wpLoad = document.getElementById("ciAssetWpMotorLoad");
    const wpStatus = document.getElementById("ciAssetWpStatus");

    if (climateTelemetryData.water_pump) {
        const wp = climateTelemetryData.water_pump;
        if (wpMotor) wpMotor.textContent = `${(wp.motor_temperature || 0).toFixed(1)} °C`;
        if (wpFlow) wpFlow.textContent = `${(wp.flow_rate || 0).toFixed(0)}%`;
        if (wpLoad) wpLoad.textContent = `${(wp.load_pct || 0)}%`;
        if (wpStatus) wpStatus.textContent = "SIMULATED";
    }
}

async function fetchClimateIntelligence(siteId = null) {
    const targetSite = siteId || currentSelectedSiteId || "CBE-001";
    console.log(`[Climate View] Fetching climate intelligence for site: ${targetSite}`);

    const tempElem = document.getElementById("ciCurrTemp");
    const humElem = document.getElementById("ciCurrHum");
    const windElem = document.getElementById("ciCurrWind");
    const rainElem = document.getElementById("ciCurrRain");
    const ciId = document.getElementById("ciHdrSiteId");
    const ciName = document.getElementById("ciHdrSiteName");
    const ciCity = document.getElementById("ciHdrCity");
    const ciCoords = document.getElementById("ciHdrCoords");
    const ciStress = document.getElementById("ciCurrStress");
    const ciTrend = document.getElementById("ciTrendBadge");
    const ciStressDesc = document.getElementById("ciStressDescription");

    // Compatibility variables
    const oSNow = document.getElementById("outlookStressNow");
    const oTNow = document.getElementById("outlookTempNow");
    const oS24 = document.getElementById("outlookStress24");
    const oT24 = document.getElementById("outlookTemp24");
    const oS48 = document.getElementById("outlookStress48");
    const oT48 = document.getElementById("outlookTemp48");
    const oS72 = document.getElementById("outlookStress72");
    const oT72 = document.getElementById("outlookTemp72");

    if (tempElem) tempElem.textContent = "Loading...";
    if (humElem) humElem.textContent = "Loading...";
    if (windElem) windElem.textContent = "Loading...";
    if (rainElem) rainElem.textContent = "Loading...";
    if (ciId) ciId.textContent = "UPDATING...";

    try {
        const res = await fetch(`${API_BASE_URL}/api/climate-intelligence?site_id=${encodeURIComponent(targetSite)}`);
        const result = await res.json();
        
        if (!result.success || !result.climate_intelligence) {
            throw new Error(result.error || "Failed to retrieve climate intelligence.");
        }

        const intel = result.climate_intelligence;
        const curr = intel.current || {};
        const impacts = intel.asset_impacts || {};

        if (ciName) ciName.textContent = intel.site_name || `${targetSite} Facility`;
        if (ciId) ciId.textContent = intel.site_id || targetSite;
        if (ciCity) ciCity.textContent = intel.city || intel.location || "Coimbatore";
        if (ciCoords && intel.latitude !== undefined && intel.longitude !== undefined) {
            const latStr = intel.latitude >= 0 ? `${intel.latitude.toFixed(4)}° N` : `${Math.abs(intel.latitude).toFixed(4)}° S`;
            const lonStr = intel.longitude >= 0 ? `${intel.longitude.toFixed(4)}° E` : `${Math.abs(intel.longitude).toFixed(4)}° W`;
            ciCoords.textContent = `${latStr}, ${lonStr}`;
        }

        const badge = document.getElementById("ciStatusBadge");
        if (badge) {
            const isLive = intel.source_status === "LIVE";
            badge.textContent = isLive ? "LIVE • OPEN-METEO" : "OFFLINE FALLBACK";
            badge.style.background = isLive ? "#10B981" : "#EF4444";
            badge.style.color = "#FFFFFF";
        }

        if (tempElem) tempElem.textContent = `${curr.temperature !== undefined ? curr.temperature : '--'}°C`;
        if (humElem) humElem.textContent = `${curr.humidity !== undefined ? curr.humidity : '--'}%`;
        if (rainElem) rainElem.textContent = `${curr.rain !== undefined ? curr.rain : '--'} mm`;
        if (windElem) windElem.textContent = `${curr.wind !== undefined ? curr.wind : '--'} km/h`;

        const stressVal = intel.overall_climate_stress !== undefined ? intel.overall_climate_stress : 0;
        const stressLvl = stressVal > 75 ? "CRITICAL" : (stressVal > 50 ? "HIGH" : (stressVal > 35 ? "ELEVATED" : (stressVal > 20 ? "WATCH" : "NORMAL")));
        
        if (ciStress) ciStress.textContent = stressVal.toFixed(1);
        if (ciTrend) {
            ciTrend.textContent = stressLvl;
            ciTrend.className = `prov-badge lvl-${stressLvl === 'CRITICAL' || stressLvl === 'HIGH' ? 'CRITICAL' : 'NORMAL'}`;
            ciTrend.style.background = stressLvl === 'CRITICAL' || stressLvl === 'HIGH' ? '#EF4444' : (stressLvl === 'WATCH' || stressLvl === 'ELEVATED' ? '#F59E0B' : '#2563EB');
            ciTrend.style.color = stressLvl === 'CRITICAL' || stressLvl === 'HIGH' || stressLvl === 'WATCH' || stressLvl === 'ELEVATED' ? '#0B1120' : '#FFFFFF';
        }

        let interpretationText = "";
        if (stressLvl === "CRITICAL") {
            interpretationText = "Critical climate exposure detected. Immediate review of facility cooling systems required.";
        } else if (stressLvl === "HIGH") {
            interpretationText = "High climate stress. Monitor equipment parameters closely for potential thermal drift.";
        } else if (stressLvl === "ELEVATED") {
            interpretationText = "Elevated environmental conditions. Increased thermal loading on sensitive cooling assets.";
        } else if (stressLvl === "WATCH") {
            interpretationText = "Watch status. Environmental stress slightly elevated, check diagnostic logs.";
        } else {
            interpretationText = "Current climate conditions are within normal operating limits for the selected facility.";
        }
        if (ciStressDesc) ciStressDesc.textContent = interpretationText;

        // Asset Climate Exposure Cards
        const txImpact = impacts.transformer || {};
        const chImpact = impacts.chiller || {};
        const wpImpact = impacts.water_pump || {};

        const txScore = txImpact.climate_stress !== undefined ? txImpact.climate_stress : 0;
        const chScore = chImpact.climate_stress !== undefined ? chImpact.climate_stress : 0;
        const wpScore = wpImpact.climate_stress !== undefined ? wpImpact.climate_stress : 0;

        const txEl = document.getElementById("ciAssetTxExposure");
        const chEl = document.getElementById("ciAssetChExposure");
        const wpEl = document.getElementById("ciAssetWpExposure");

        if (txEl) txEl.textContent = txScore.toFixed(0);
        if (chEl) chEl.textContent = chScore.toFixed(0);
        if (wpEl) wpEl.textContent = wpScore.toFixed(0);

        const getAssetStatus = (score) => {
            if (score > 75) return "CRITICAL";
            if (score > 50) return "HIGH";
            if (score > 30) return "WATCH";
            return "NORMAL";
        };

        const txStatus = getAssetStatus(txScore);
        const chStatus = getAssetStatus(chScore);
        const wpStatus = getAssetStatus(wpScore);

        const txBadge = document.getElementById("ciAssetTxStatusBadge");
        const chBadge = document.getElementById("ciAssetChStatusBadge");
        const wpBadge = document.getElementById("ciAssetWpStatusBadge");

        const updateBadgeStyle = (badge, status) => {
            if (!badge) return;
            badge.textContent = status;
            if (status === "CRITICAL" || status === "HIGH") {
                badge.className = "prov-badge badge-critical";
                badge.style.background = "#EF4444";
                badge.style.color = "#0B1120";
            } else if (status === "WATCH") {
                badge.className = "prov-badge badge-warning";
                badge.style.background = "#F59E0B";
                badge.style.color = "#0B1120";
            } else {
                badge.className = "prov-badge badge-normal";
                badge.style.background = "#2563EB";
                badge.style.color = "#FFFFFF";
            }
        };

        updateBadgeStyle(txBadge, txStatus);
        updateBadgeStyle(chBadge, chStatus);
        updateBadgeStyle(wpBadge, wpStatus);

        let normalCount = 0, watchCount = 0, criticalCount = 0;
        [txStatus, chStatus, wpStatus].forEach(st => {
            if (st === "NORMAL") normalCount++;
            else if (st === "WATCH") watchCount++;
            else criticalCount++;
        });

        const countEl = document.getElementById("ciAssetStatusCountText");
        const normalEl = document.getElementById("ciAssetStatusNormalText");
        const watchEl = document.getElementById("ciAssetStatusWatchText");
        const criticalEl = document.getElementById("ciAssetStatusCriticalText");

        if (countEl) countEl.textContent = "3 ASSETS MONITORED";
        if (normalEl) normalEl.textContent = `${normalCount} NORMAL`;
        if (watchEl) watchEl.textContent = `${watchCount} WATCH`;
        if (criticalEl) criticalEl.textContent = `${criticalCount} CRITICAL`;

        const txFactorEl = document.getElementById("ciAssetTxFactor");
        const chFactorEl = document.getElementById("ciAssetChFactor");
        const wpFactorEl = document.getElementById("ciAssetWpFactor");

        const tempVal = curr.temperature !== undefined ? curr.temperature : 25;
        const humVal = curr.humidity !== undefined ? curr.humidity : 50;
        const rainVal = curr.rain !== undefined ? curr.rain : 0;

        if (txFactorEl) {
            if (tempVal > 35) {
                txFactorEl.textContent = "Critical ambient heat: high transformer winding thermal stress and cooling load.";
            } else if (tempVal > 30) {
                txFactorEl.textContent = "Elevated ambient temperature: increased cooling and oil heat accumulation.";
            } else {
                txFactorEl.textContent = "Thermal conditions stable: transformer operating within normal baseline temperature.";
            }
        }

        if (chFactorEl) {
            if (tempVal > 32 && humVal > 70) {
                chFactorEl.textContent = "High ambient heat and humidity: reduced heat rejection and elevated compressor power demand.";
            } else if (tempVal > 30) {
                chFactorEl.textContent = "Elevated ambient heat: increased chiller thermal load and baseline duty cycle.";
            } else {
                chFactorEl.textContent = "Mild climate: chiller heat rejection operates at optimal baseline efficiency.";
            }
        }

        if (wpFactorEl) {
            if (rainVal > 5) {
                wpFactorEl.textContent = "Precipitation detected: increased moisture ingress risk on external pump electronics.";
            } else if (humVal > 80) {
                wpFactorEl.textContent = "High relative humidity: risk of moisture build-up and surface condensation.";
            } else {
                wpFactorEl.textContent = "Dry conditions: moisture exposure minimal across water pump seals.";
            }
        }

        // Initialize and trigger simulated live IoT telemetry stream
        initClimateTelemetryData();
        simulateClimateTelemetry(targetSite);

        if (climateTelemetryTimer) clearInterval(climateTelemetryTimer);
        climateTelemetryTimer = setInterval(() => {
            simulateClimateTelemetry(targetSite);
        }, 30000);

        // Update footer last updated timestamp
        const lastUpdatedEl = document.getElementById("ciLastUpdatedText");
        if (lastUpdatedEl) {
            const ts = intel.current.timestamp || "";
            const timePart = ts.includes(" ") ? ts.split(" ")[1] : ts;
            const displayTime = timePart ? timePart.substring(0, 5) : new Date().toLocaleTimeString().substring(0, 5);
            lastUpdatedEl.textContent = `Updated ${displayTime}`;
        }

        // Compatibility updates
        if (oSNow) oSNow.textContent = "--";
        if (oTNow) oTNow.textContent = "--";
        if (oS24) oS24.textContent = "--";
        if (oT24) oT24.textContent = "--";
        if (oS48) oS48.textContent = "--";
        if (oT48) oT48.textContent = "--";
        if (oS72) oS72.textContent = "--";
        if (oT72) oT72.textContent = "--";

    } catch (e) {
        console.error("Fetch Climate Intelligence Error:", e);
        if (tempElem) tempElem.textContent = "Unavailable";
        if (humElem) humElem.textContent = "Unavailable";
        if (rainElem) rainElem.textContent = "Unavailable";
        if (windElem) windElem.textContent = "Unavailable";
        if (ciId) ciId.textContent = "CLIMATE DATA UNAVAILABLE";
        if (ciStress) ciStress.textContent = "ERROR";
        if (ciStressDesc) ciStressDesc.textContent = "Unable to retrieve current weather for this facility.";
        
        if (climateTelemetryTimer) clearInterval(climateTelemetryTimer);
        const normalEl = document.getElementById("ciAssetStatusNormalText");
        const watchEl = document.getElementById("ciAssetStatusWatchText");
        const criticalEl = document.getElementById("ciAssetStatusCriticalText");
        if (normalEl) normalEl.textContent = "--";
        if (watchEl) watchEl.textContent = "--";
        if (criticalEl) criticalEl.textContent = "--";
    }
}

/* REAL-TIME OT TELEMETRY LOGIC */
let liveOTStreamInterval = null;
let currentOTMode = "MOCK";

async function fetchOTStatus() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/telemetry/status`);
        const result = await res.json();
        if (!result.success) return;

        currentOTMode = result.telemetry_mode || "MOCK";

        const modeElem = document.getElementById("otModeDisplay");
        if (modeElem) {
            if (currentOTMode === "REAL_OT") {
                modeElem.innerText = "DATA CONNECTIVITY: REAL OT";
                modeElem.className = "prov-badge live-weather";
            } else {
                modeElem.innerText = "DATA CONNECTIVITY: OPERATIONAL";
                modeElem.className = "prov-badge badge-connectivity";
            }
        }
    } catch (e) {
        console.error("Fetch OT Status Exception:", e);
    }
}

async function fetchLiveOTTelemetry() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/telemetry/live`);
        const result = await res.json();
        if (!result.success || !result.telemetry) return;

        const tel = result.telemetry;
        const tx = tel.transformer || {};
        const ch = tel.chiller || {};
        const wp = tel.water_pump || {};

        const txT = tx.telemetry || {};
        const otiElem = document.getElementById("otTxOTI");
        const wtiElem = document.getElementById("otTxWTI");
        const atiElem = document.getElementById("otTxATI");
        const oliElem = document.getElementById("otTxOLI");
        const kwElem = document.getElementById("otTxKW");
        const vl1Elem = document.getElementById("otTxVL1");

        if (otiElem) otiElem.innerText = `${txT.OTI !== undefined ? txT.OTI : '--'} °C`;
        if (wtiElem) wtiElem.innerText = `${txT.WTI !== undefined ? txT.WTI : '--'} °C`;
        if (atiElem) atiElem.innerText = `${txT.ATI !== undefined ? txT.ATI : '--'} °C`;
        if (oliElem) oliElem.innerText = `${txT.OLI !== undefined ? txT.OLI : '--'} %`;
        if (kwElem) kwElem.innerText = `${txT.KW !== undefined ? txT.KW : '--'} kW`;
        if (vl1Elem) vl1Elem.innerText = `${txT.VL1 !== undefined ? txT.VL1 : '--'} kV`;

        const chT = ch.telemetry || {};
        const teiElem = document.getElementById("otChTEI");
        const teoElem = document.getElementById("otChTEO");
        const tciElem = document.getElementById("otChTCI");
        const tcoElem = document.getElementById("otChTCO");
        const chKwElem = document.getElementById("otChKW");

        if (teiElem) teiElem.innerText = `${chT.TEI !== undefined ? chT.TEI : '--'} °C`;
        if (teoElem) teoElem.innerText = `${chT.TEO !== undefined ? chT.TEO : '--'} °C`;
        if (tciElem) tciElem.innerText = `${chT.TCI !== undefined ? chT.TCI : '--'} °C`;
        if (tcoElem) tcoElem.innerText = `${chT.TCO !== undefined ? chT.TCO : '--'} °C`;
        if (chKwElem) chKwElem.innerText = `${chT.kW !== undefined ? chT.kW : '--'} kW`;

        const wpT = wp.telemetry || {};
        const flowElem = document.getElementById("otWpFlow");
        const pressElem = document.getElementById("otWpPress");
        const motorTElem = document.getElementById("otWpMotorT");
        const vibElem = document.getElementById("otWpVib");

        if (flowElem) flowElem.innerText = `${wpT.flow !== undefined ? wpT.flow : '--'} L/m`;
        if (pressElem) pressElem.innerText = `${wpT.pressure !== undefined ? wpT.pressure : '--'} bar`;
        if (motorTElem) motorTElem.innerText = `${wpT.motor_temperature !== undefined ? wpT.motor_temperature : '--'} °C`;
        if (vibElem) vibElem.innerText = `${wpT.vibration !== undefined ? wpT.vibration : '--'} mm/s`;

    } catch (e) {
        console.error("Fetch Live OT Telemetry Error:", e);
    }
}

async function setTelemetryScenario(scenarioName, btnElem) {
    if (btnElem) {
        document.querySelectorAll(".btn-ot-scen").forEach(b => b.classList.remove("active"));
        btnElem.classList.add("active");
    }

    try {
        const res = await fetch(`${API_BASE_URL}/api/telemetry/scenario`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ scenario: scenarioName })
        });
        const result = await res.json();
        if (result.success) {
            fetchLiveOTTelemetry();
            analyzeNextFleetSample();
        }
    } catch (e) {
        console.error("Set Telemetry Scenario Error:", e);
    }
}

function startLiveOTStream() {
    if (liveOTStreamInterval) clearInterval(liveOTStreamInterval);
    fetchLiveOTTelemetry();
    liveOTStreamInterval = setInterval(() => {
        fetchLiveOTTelemetry();
    }, 2500);
}

/* INCIDENT COMMAND CENTER FRONTEND LOGIC */

async function fetchIncidents() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/incidents`);
        const result = await res.json();
        if (!result.success || !result.data) return;

        const data = result.data;
        const activeList = data.active_incidents || [];
        const historyList = data.history || [];

        const activeCount = activeList.length;
        const critCount = activeList.filter(i => i.severity === "CRITICAL").length;

        const activeElem = document.getElementById("incKpiActive");
        const critElem = document.getElementById("incKpiCritical");
        if (activeElem) activeElem.innerText = activeCount;
        if (critElem) critElem.innerText = critCount;

        if (activeList.length > 0) {
            const topInc = activeList[0];
            const sysElem = document.getElementById("incKpiSysRisk");
            const vulnElem = document.getElementById("incKpiVulnAsset");
            if (sysElem) sysElem.innerText = `${topInc.system_risk ? topInc.system_risk.toFixed(1) : '--'} / 100`;
            if (vulnElem) vulnElem.innerText = topInc.most_vulnerable_asset || '--';
        }

        const banner = document.getElementById("incWarningBanner");
        const bTitle = document.getElementById("incBannerTitle");
        const bSub = document.getElementById("incBannerSubtext");

        if (critCount > 0) {
            if (banner) banner.className = "inc-warning-banner inc-banner-critical";
            if (bTitle) bTitle.innerText = "CRITICAL CASCADE RISK: Immediate engineering assessment recommended.";
            if (bSub) bSub.innerText = "Potential elevated multi-asset failure risk detected under climate stress conditions.";
        } else if (activeCount > 0) {
            if (banner) banner.className = "inc-warning-banner inc-banner-warning";
            if (bTitle) bTitle.innerText = "WARNING: Infrastructure risk requires attention.";
            if (bSub) bSub.innerText = "Potential elevated risk detected across transformer, cooling, or climate conditions.";
        } else {
            if (banner) banner.className = "inc-warning-banner inc-banner-hidden";
        }

        const tbody = document.getElementById("incTableBody");
        if (!tbody) return;

        if (historyList.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted);">No active incidents. Systems operating within normal baseline limits.</td></tr>`;
            return;
        }

        let html = "";
        historyList.slice(0, 10).forEach(inc => {
            const sevClass = inc.severity === "CRITICAL" ? "lvl-CRITICAL" : (inc.severity === "WARNING" ? "lvl-WARNING" : "lvl-NORMAL");
            
            html += `
                <tr>
                    <td><code>${inc.incident_id}</code></td>
                    <td><span class="status-badge ${sevClass}">${inc.severity}</span></td>
                    <td>${inc.timestamp}</td>
                    <td><strong>${inc.system_risk !== undefined ? inc.system_risk.toFixed(1) : '--'} / 100</strong></td>
                    <td><span class="prov-badge live-weather">${inc.most_vulnerable_asset || '--'}</span></td>
                    <td style="max-width: 200px; font-size: 11px; color: var(--text-muted);">${inc.trigger || '--'}</td>
                    <td><strong>${inc.status}</strong></td>
                    <td>
                        ${inc.status === "OPEN" ? `<button class="btn-secondary" style="padding:2px 6px; font-size:10px;" onclick="acknowledgeIncident('${inc.incident_id}')">ACK</button>` : ''}
                        ${inc.status !== "RESOLVED" ? `<button class="btn-success" style="padding:2px 6px; font-size:10px; margin-left:4px;" onclick="resolveIncident('${inc.incident_id}')">RESOLVE</button>` : ''}
                        <button class="btn-primary" style="padding:2px 6px; font-size:10px; margin-left:4px;" onclick="triggerPDFReportDownload('${inc.incident_id}')">PDF</button>
                    </td>
                </tr>
            `;
        });
        tbody.innerHTML = html;

    } catch (e) {
        console.error("Fetch Incidents Error:", e);
    }
}

async function acknowledgeIncident(incId) {
    try {
        const res = await fetch(`${API_BASE_URL}/api/incidents/${incId}/acknowledge`, { method: "POST" });
        const result = await res.json();
        if (result.success) {
            fetchIncidents();
        }
    } catch (e) {
        console.error("Acknowledge Incident Error:", e);
    }
}

async function resolveIncident(incId) {
    try {
        const res = await fetch(`${API_BASE_URL}/api/incidents/${incId}/resolve`, { method: "POST" });
        const result = await res.json();
        if (result.success) {
            fetchIncidents();
        }
    } catch (e) {
        console.error("Resolve Incident Error:", e);
    }
}

async function triggerPDFReportDownload(incId = null) {
    try {
        const payload = incId ? { incident_id: incId } : {};
        const res = await fetch(`${API_BASE_URL}/api/incidents/generate-report`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            console.error(`PDF generation HTTP error ${res.status}`);
            alert("Failed to generate PDF incident report.");
            return;
        }

        const blob = await res.blob();
        if (blob.type !== "application/pdf") {
            console.error("Unexpected PDF MIME type:", blob.type);
            alert("Server did not return a valid PDF document.");
            return;
        }

        let filename = incId ? `CascadeGuard_Incident_${incId}.pdf` : "CascadeGuard_Executive_Report.pdf";
        const disposition = res.headers.get("Content-Disposition");
        if (disposition && disposition.includes("filename=")) {
            const filenameMatch = disposition.match(/filename=["']?([^"';]+)["']?/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1].trim();
            }
        }
        if (!filename.toLowerCase().endsWith(".pdf")) {
            filename += ".pdf";
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        console.error("Trigger PDF Download Error:", e);
        alert("Error initiating PDF report download.");
    }
}

/* REGIONAL COMMAND CENTER FRONTEND LOGIC */

let regionalMapInstance = null;
let regionalMarkers = {};

function initRegionalMap() {
    const mapElem = document.getElementById("regionalMap");
    if (!mapElem || regionalMapInstance) return;

    try {
        regionalMapInstance = L.map("regionalMap").setView([11.5, 78.5], 7);

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 18,
            attribution: "OpenStreetMap | CascadeGuard Regional Command"
        }).addTo(regionalMapInstance);
    } catch (e) {
        console.error("Init Regional Map Error:", e);
    }
}

async function fetchRegionalStatus() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/regional-status`);
        const result = await res.json();
        if (!result.success || !result.regional) return;

        const reg = result.regional;
        const sites = reg.sites || [];

        const monElem = document.getElementById("regKpiMonitored");
        const critElem = document.getElementById("regKpiCritical");
        const warnElem = document.getElementById("regKpiWarning");
        const riskElem = document.getElementById("regKpiRisk");
        const vulnElem = document.getElementById("regKpiVulnSite");

        if (monElem) monElem.innerText = reg.sites_monitored;
        if (critElem) critElem.innerText = reg.critical_sites;
        if (warnElem) warnElem.innerText = reg.warning_sites;
        if (riskElem) riskElem.innerText = `${reg.regional_risk.toFixed(1)} / 100`;

        // Simplified overview KPI calculations
        const watchElem = document.getElementById("regKpiWatch");
        if (watchElem) watchElem.innerText = reg.watch_sites || 0;

        const warnCritElem = document.getElementById("regKpiWarningCritical");
        if (warnCritElem) warnCritElem.innerText = (reg.warning_sites || 0) + (reg.critical_sites || 0);

        const priorityKpiElem = document.getElementById("regKpiPriority");
        if (priorityKpiElem) priorityKpiElem.innerText = "1";

        const mv = reg.most_vulnerable_site || {};
        if (vulnElem) vulnElem.innerText = mv.site_name || '--';

        const alertBanner = document.getElementById("regAlertBanner");
        if (alertBanner) {
            if (reg.critical_sites > 0 || reg.regional_level === "CRITICAL") {
                alertBanner.className = "inc-warning-banner inc-banner-critical";
            } else if (reg.warning_sites > 0 || reg.regional_level === "WARNING") {
                alertBanner.className = "inc-warning-banner inc-banner-warning";
            } else {
                alertBanner.className = "inc-warning-banner inc-banner-hidden";
            }
        }

        const prioritySiteId = mv.site_id;
        
        const pSiteText = document.getElementById("ovPrioritySiteText");
        if (pSiteText) {
            if (prioritySiteId) {
                pSiteText.innerHTML = `${mv.site_name || "Coimbatore Industrial Facility"} <strong id="ovPrioritySiteId" style="color: var(--brand-accent, #06B6D4); font-weight: 700; margin-left: 6px;">(${prioritySiteId})</strong>`;
            } else {
                pSiteText.innerHTML = `Unable to determine current priority <strong id="ovPrioritySiteId" style="color: var(--danger, #EF4444); font-weight: 700; margin-left: 6px;">(--)</strong>`;
            }
        }

        const mvName = document.getElementById("mvSiteName");
        const mvId = document.getElementById("mvSiteId");
        const mvRisk = document.getElementById("mvRiskNum");
        const mvDesc = document.getElementById("mvVulnDesc");

        if (mvName) mvName.innerText = mv.site_name || "Unable to determine current priority";
        if (mvId) mvId.innerText = mv.site_id || "--";
        if (mvRisk) mvRisk.innerText = mv.system_cascade_risk ? mv.system_cascade_risk.toFixed(1) : "--";
        if (mvDesc) mvDesc.innerHTML = `Primary Vulnerability: <strong style="color:var(--text-primary); font-weight:700;">${mv.vulnerable_asset || 'NONE'}</strong><br/>Risk Status: <strong style="color:${mv.level === 'CRITICAL' ? '#EF4444' : (mv.level === 'WARNING' || mv.level === 'WATCH' ? '#F59E0B' : '#22C55E')}; font-weight:700;">${mv.level || 'NORMAL'}</strong>`;

        // Keep local variables and elements in sync
        if (prioritySiteId) {
            const nowTime = Date.now();
            if (prioritySiteId !== lastLoadedOverviewSiteId || !lastOverviewClimateTime || (nowTime - lastOverviewClimateTime > 5 * 60 * 1000)) {
                lastLoadedOverviewSiteId = prioritySiteId;
                lastOverviewClimateTime = nowTime;
                currentOverviewSite = prioritySiteId;
                loadOverviewClimate(prioritySiteId);
            }
        } else {
            // Clear climate UI to represent unavailable data state
            const tempElem = document.getElementById('ovTempDisplay');
            const humElem = document.getElementById('ovHumidityDisplay');
            const rainElem = document.getElementById('ovRainDisplay');
            const windElem = document.getElementById('ovWindDisplay');
            const csBadge = document.getElementById('ovClimateStressBadge');
            if (tempElem) tempElem.textContent = "WEATHER DATA UNAVAILABLE";
            if (humElem) humElem.textContent = "--";
            if (rainElem) rainElem.textContent = "--";
            if (windElem) windElem.textContent = "--";
            if (csBadge) {
                csBadge.textContent = "UNKNOWN";
                csBadge.className = "prov-badge badge-info";
            }
        }

        // Dynamic Alert Banner Update
        const alertContainer = document.getElementById("ovAlertContainer");
        if (alertContainer) {
            if (reg.critical_sites > 0 || reg.warning_sites > 0) {
                const alertTitle = reg.critical_sites > 0 ? "CRITICAL INFRASTRUCTURE RISK DETECTED" : " ELEVATED INFRASTRUCTURE RISK DETECTED";
                const activeAssetName = mv.vulnerable_asset || "TRANSFORMER";
                alertContainer.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                        <div>
                            <small style="font-size: 11.5px; font-weight: 600; color: #EF4444; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">CURRENT ALERT</small>
                            <h4 style="font-size: 16px; font-weight: 750; color: var(--text-primary); margin: 0 0 6px; text-transform: uppercase; line-height: 1.2;">${alertTitle}</h4>
                            <p style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.5; margin: 0;">
                                Forecast conditions indicate increased ${activeAssetName.toLowerCase()} thermal exposure at the priority facility <strong>(${mv.site_name || 'UNKNOWN'})</strong>.
                            </p>
                        </div>
                        <button type="button" class="btn-primary" style="border: none; background: #EF4444; color: #0B1120; font-size: 13.5px; font-weight: 650; padding: 8px 16px;" onclick="navigateToPredictiveForPriority()">
                            REVIEW 72-HOUR RISK
                        </button>
                    </div>
                `;
            } else {
                alertContainer.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                        <div>
                            <small style="font-size: 11.5px; font-weight: 600; color: #22C55E; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 6px;">CURRENT STATUS</small>
                            <h4 style="font-size: 16px; font-weight: 750; color: var(--text-primary); margin: 0 0 6px; line-height: 1.2;">✓ ALL MONITORED FACILITIES OPERATIONAL</h4>
                            <p style="font-size: 13.5px; color: var(--text-secondary); line-height: 1.5; margin: 0;">
                                All monitored regional facilities are currently operating within expected predictive stress baseline parameters.
                            </p>
                        </div>
                        <button type="button" class="btn-secondary" style="border: 1px solid var(--border-strong); background: transparent; color: var(--text-primary); font-size: 13.5px; font-weight: 650; padding: 8px 16px;" onclick="navigateToPredictiveForPriority()">
                            REVIEW 72-HOUR RISK
                        </button>
                    </div>
                `;
            }
        }

        if (regionalMapInstance) {
            sites.forEach(s => {
                const color = s.level === "CRITICAL" ? "#EF4444" : (s.level === "WARNING" ? "#F59E0B" : "#2563EB");
                const popupContent = `
                    <div style="font-family: sans-serif; font-size: 12px; color: #0F172A;">
                        <strong>${s.site_name} (${s.site_id})</strong><br/>
                        <b>Cascade Risk:</b> ${s.system_cascade_risk.toFixed(1)} / 100<br/>
                        <b>Status:</b> <span style="color: ${color}; font-weight:800;">${s.level}</span><br/>
                        <b>Vulnerability:</b> ${s.most_vulnerable_asset}<br/>
                        <b>Climate Stress:</b> ${s.climate_stress.toFixed(1)}
                    </div>
                `;

                // Highlight priority facility marker (larger size + cyan border accent)
                const isPriority = (s.site_id === prioritySiteId);
                const markerRadius = isPriority ? 14 : 9;
                const markerWeight = isPriority ? 4 : 2;
                const markerColor = isPriority ? "#06B6D4" : color;

                if (regionalMarkers[s.site_id]) {
                    regionalMarkers[s.site_id].setPopupContent(popupContent);
                    regionalMarkers[s.site_id].setRadius(markerRadius);
                    regionalMarkers[s.site_id].setStyle({
                        color: markerColor,
                        fillColor: color,
                        weight: markerWeight,
                        fillOpacity: 0.8
                    });
                } else {
                    const marker = L.circleMarker([s.latitude, s.longitude], {
                        color: markerColor,
                        fillColor: color,
                        fillOpacity: 0.8,
                        radius: markerRadius,
                        weight: markerWeight
                    }).addTo(regionalMapInstance);
                    marker.bindPopup(popupContent);
                    regionalMarkers[s.site_id] = marker;
                }
            });
        }

        const gridElem = document.getElementById("siteCardsGrid");
        if (gridElem) {
            let gridHtml = "";
            sites.forEach(s => {
                const sClass = s.level === "CRITICAL" ? "lvl-CRITICAL" : (s.level === "WARNING" ? "lvl-WARNING" : "lvl-NORMAL");
                gridHtml += `
                    <div class="site-card" onclick="handleSiteSelection('${s.site_id}')">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <strong>${s.city}</strong>
                            <span class="prov-badge live-weather" style="font-size:10px;">${s.site_id}</span>
                        </div>
                        <div class="site-card-risk">${s.system_cascade_risk.toFixed(1)}</div>
                        <div style="font-size:11px;">STATUS: <span class="status-badge ${sClass}">${s.level}</span></div>
                        <div style="margin-top:6px; font-size:11px; color:var(--text-muted);">
                            Tx: ${s.transformer_risk.toFixed(1)} | Ch: ${s.chiller_risk.toFixed(1)} | P: ${s.water_pump_risk.toFixed(1)}
                        </div>
                    </div>
                `;
            });
            gridElem.innerHTML = gridHtml;
        }

        const compBody = document.getElementById("siteComparisonTableBody");
        if (compBody) {
            let compHtml = "";
            sites.forEach(s => {
                const cClass = s.level === "CRITICAL" ? "lvl-CRITICAL" : (s.level === "WARNING" ? "lvl-WARNING" : "lvl-NORMAL");
                compHtml += `
                    <tr>
                        <td style="font-size: 13.5px;"><strong>#${s.priority_rank}</strong></td>
                        <td style="font-size: 14.5px; font-weight: 600;">${s.site_name} <span style="font-size: 11.5px; color: var(--text-muted); font-weight: 500; margin-left: 4px;">(${s.site_id})</span></td>
                        <td style="font-size: 13.5px; color: var(--text-secondary);">${s.city}</td>
                        <td style="font-size: 14.5px; font-weight: 700;">${s.system_cascade_risk.toFixed(1)} / 100</td>
                        <td style="font-size: 11.5px;"><span class="status-badge ${cClass}">${s.level}</span></td>
                        <td style="font-size: 13.5px; color: var(--text-secondary);">${s.transformer_risk.toFixed(1)}</td>
                        <td style="font-size: 13.5px; color: var(--text-secondary);">${s.chiller_risk.toFixed(1)}</td>
                        <td style="font-size: 13.5px; color: var(--text-secondary);">${s.water_pump_risk.toFixed(1)}</td>
                        <td style="font-size: 13.5px; color: var(--text-secondary);">${s.climate_stress.toFixed(1)}</td>
                        <td style="font-size: 11.5px;"><span class="prov-badge live-weather">${s.most_vulnerable_asset}</span></td>
                        <td style="font-size: 11.5px;"><span class="prov-badge pred-sim">${s.data_quality}</span></td>
                        <td><button class="btn-secondary" style="padding: 6px 12px; font-size: 12.5px; font-weight: 650;" onclick="handleSiteSelection('${s.site_id}')">VIEW SITE</button></td>
                    </tr>
                `;
            });
            compBody.innerHTML = compHtml;
        }

    } catch (e) {
        console.error("Fetch Regional Status Error:", e);
    }
}

function handleSiteSelection(siteId, keepNotification = false) {
    if (!siteId) return;
    if (siteId === "ALL") {
        currentSelectedSiteId = "ALL";
        showView("overview");
        fetchRegionalStatus();
        loadOverviewClimate("ALL");
        return;
    }

    currentSelectedSiteId = siteId;
    fetch(`${API_BASE_URL}/api/sites/${siteId}`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.site) {
                const site = data.site;
                updateFacilityDetailsPanel(site);
                setEditFacilityMode(site, keepNotification);

                // Synchronize all facility selectors across views
                const dropdownIds = [
                    "ovFacilitySelect",
                    "siteSelector",
                    "predictiveFacilitySelector",
                    "decisionFacilitySelector",
                    "incP19FacilitySelector",
                    "scenFacilitySelector",
                    "climateFacilitySelector",
                    "cascadeFacilitySelector"
                ];

                dropdownIds.forEach(id => {
                    const sel = document.getElementById(id);
                    if (sel && sel.value !== siteId) {
                        sel.value = siteId;
                    }
                });

                selectedPredictiveSiteId = siteId;
                selectedDecisionSiteId = siteId;

                initSiteMap(site.latitude, site.longitude);
                fetchClimateIntelligence(site.site_id);
                fetchRegionalStatus();
                loadOverviewClimate(siteId);
            }
        })
        .catch(err => console.error("Site selection error:", err));
}

/* DEMO MODE & GUIDED DEMO FLOW */
function toggleDemoGuide() {
    const panel = document.getElementById("demoGuidePanel");
    if (panel) {
        panel.classList.toggle("demo-guide-hidden");
    }
}

function highlightDemoStep(stepNumber) {
    for (let i = 1; i <= 8; i++) {
        const el = document.getElementById(`demoStep${i}`);
        if (el) {
            if (i === stepNumber) {
                el.classList.add("active");
            } else {
                el.classList.remove("active");
            }
        }
    }
}

let isDemoRunning = false;

function updateHeaderClock() {
    const el = document.getElementById("hdrLastUpdated");
    if (el) {
        const now = new Date();
        const hrs = String(now.getHours()).padStart(2, '0');
        const mins = String(now.getMinutes()).padStart(2, '0');
        el.innerText = `LAST UPDATED: ${hrs}:${mins}`;
    }
}

async function runOneClickDemoFlow() {
    if (isDemoRunning) return;
    isDemoRunning = true;
    
    const guidePanel = document.getElementById("demoGuidePanel");
    if (guidePanel) guidePanel.classList.remove("demo-guide-hidden");
    
    const btn = document.getElementById("btnOneClickDemo");
    if (btn) {
        btn.innerText = "SIMULATION IN PROGRESS...";
        btn.disabled = true;
    }

    try {
        // Step 1: Baseline Overview
        highlightDemoStep(1);
        showView("overview");
        await setTelemetryScenario("NORMAL");
        await new Promise(r => setTimeout(r, 2500));

        // Step 2: Climate & Heat Stress
        highlightDemoStep(2);
        showView("climate");
        await setTelemetryScenario("HEAT_STRESS");
        await new Promise(r => setTimeout(r, 3000));

        // Step 3: Assets & Chiller Surge
        highlightDemoStep(3);
        showView("assets");
        await setTelemetryScenario("CHILLER_OVERLOAD");
        await new Promise(r => setTimeout(r, 3000));

        // Step 4: Water Pump Degradation
        highlightDemoStep(4);
        showView("cascade");
        await setTelemetryScenario("PUMP_DEGRADATION");
        await new Promise(r => setTimeout(r, 3000));

        // Step 5: Scenarios & Combined Cascade
        highlightDemoStep(5);
        showView("scenarios");
        await setTelemetryScenario("COMBINED_CASCADE");
        await runClimateScenario("COMBINED_CASCADE", null);
        await new Promise(r => setTimeout(r, 3000));

        // Step 6: Analytics & SHAP
        highlightDemoStep(6);
        showView("analytics");
        await fetchIncidents();
        await new Promise(r => setTimeout(r, 2500));

        // Step 7: Incidents
        highlightDemoStep(7);
        showView("incidents");
        await new Promise(r => setTimeout(r, 2500));

        // Step 8: Reports
        highlightDemoStep(8);
        showView("reports");
        alert("SYSTEM SIMULATION COMPLETE! System Cascade Risk reached critical levels, generating dynamic SHAP XAI factors, automated incident alert webhook, and downloadable PDF report.");

    } catch (err) {
        console.error("Simulation Flow Error:", err);
    } finally {
        isDemoRunning = false;
        if (btn) {
            btn.innerText = "RUN AUTOMATED SIMULATION";
            btn.disabled = false;
        }
    }
}

window.addEventListener("DOMContentLoaded", async () => {
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
    updateHeaderClock();
    setInterval(updateHeaderClock, 30000);
    loadOverviewData(currentSelectedSiteId);
    await fetchSiteRegistry();
    handleSiteSelection(currentSelectedSiteId);
    analyzeNextFleetSample();
    runClimateScenario("NORMAL", null);
    fetchOTStatus();
    startLiveOTStream();
    fetchIncidents();
    setInterval(fetchIncidents, 4000);
    initRegionalMap();
    fetchRegionalStatus();
    setInterval(fetchRegionalStatus, 5000);
});


/* ============================================================
   PHASE 5: DEPENDENCY-AWARE CASCADE RISK CONTROLLER
   ============================================================ */

let cascadeForecastChart = null;
let selectedCascadeSiteId = "CBE-001";
let currentCascadeScenario = "NORMAL";
let selectedCascadeNodeName = "transformer";
let cascadeDataCache = null;

function handleCascadeFacilitySelection(siteId) {
    selectedCascadeSiteId = siteId;
    currentSelectedSiteId = siteId;
    selectedPredictiveSiteId = siteId;
    selectedDecisionSiteId = siteId;

    const dropdownIds = [
        "ovFacilitySelect",
        "siteSelector",
        "predictiveFacilitySelector",
        "decisionFacilitySelector",
        "incP19FacilitySelector",
        "scenFacilitySelector",
        "cascadeFacilitySelector",
        "climateFacilitySelector"
    ];
    dropdownIds.forEach(id => {
        const sel = document.getElementById(id);
        if (sel && sel.value !== siteId) {
            sel.value = siteId;
        }
    });

    loadCascadeViewData();
}

function handleCascadeScenarioSelection(scenarioName) {
    currentCascadeScenario = scenarioName;
    loadCascadeViewData();
}

function selectCascadeNode(nodeType) {
    selectedCascadeNodeName = nodeType;
    updateCascadeNodeUI();
    populateCascadeNodeDetails(nodeType);
}

function updateCascadeNodeUI() {
    const nodes = ["transformer", "chiller", "water_pump", "facility"];
    nodes.forEach(node => {
        const el = document.getElementById(`node-${node}`);
        if (el) {
            if (node === selectedCascadeNodeName) {
                el.style.borderColor = "var(--brand-accent, #06B6D4)";
                el.style.boxShadow = "0 0 12px rgba(6, 182, 212, 0.4)";
                el.style.transform = "scale(1.03)";
            } else {
                el.style.borderColor = (node === "transformer" ? "var(--border-strong)" : "var(--border-subtle)");
                el.style.boxShadow = "0 4px 6px rgba(0,0,0,0.1)";
                el.style.transform = "scale(1)";
            }
        }
    });
}

function populateCascadeNodeDetails(nodeType) {
    if (!cascadeDataCache) return;
    
    const nodes = cascadeDataCache.dependency_graph.nodes || [];
    const siteName = cascadeDataCache.site_name || "Facility";
    
    let nodeId = "--";
    let typeName = "";
    let baseRisk = "--";
    let propRisk = "--";
    let finalRisk = "--";
    let description = "";

    const txNode = nodes.find(n => n.type === "transformer") || {};
    const chNode = nodes.find(n => n.type === "chiller") || {};
    const wpNode = nodes.find(n => n.type === "water_pump") || {};

    const scenData = cascadeDataCache.scenarios.find(s => s.scenario.toLowerCase() === currentCascadeScenario.toLowerCase()) || {};
    const nodeRisks = scenData.node_risks || {};

    if (nodeType === "transformer") {
        nodeId = txNode.id || "TX-001";
        typeName = "Power Transformer";
        const rInfo = nodeRisks.transformer || {};
        baseRisk = `${(rInfo.base_risk || 0).toFixed(1)} / 100`;
        propRisk = `${(rInfo.propagated_risk || 0).toFixed(1)} / 100`;
        finalRisk = `${(rInfo.cascade_risk || 0).toFixed(1)} / 100`;
        description = `Transformer ${nodeId} provides the primary power distribution to downstream chiller and pump. Stress propagates downstream to all connected circuits.`;
    } else if (nodeType === "chiller") {
        nodeId = chNode.id || "CH-001";
        typeName = "HVAC Chiller";
        const rInfo = nodeRisks.chiller || {};
        baseRisk = `${(rInfo.base_risk || 0).toFixed(1)} / 100`;
        propRisk = `${(rInfo.propagated_risk || 0).toFixed(1)} / 100`;
        finalRisk = `${(rInfo.cascade_risk || 0).toFixed(1)} / 100`;
        description = `HVAC Chiller ${nodeId} depends on Transformer ${txNode.id || 'TX-001'} for electrical power (POWER dependency strength = 1.0). Provides chilled water cooling service to the facility (COOLING dependency strength = 0.8).`;
    } else if (nodeType === "water_pump") {
        nodeId = wpNode.id || "WP-001";
        typeName = "Water Pump";
        const rInfo = nodeRisks.water_pump || {};
        baseRisk = `${(rInfo.base_risk || 0).toFixed(1)} / 100`;
        propRisk = `${(rInfo.propagated_risk || 0).toFixed(1)} / 100`;
        finalRisk = `${(rInfo.cascade_risk || 0).toFixed(1)} / 100`;
        description = `Water Pump ${nodeId} depends on Transformer ${txNode.id || 'TX-001'} for electrical power (POWER dependency strength = 1.0). Provides drainage service to protect site against flooding (DRAINAGE dependency strength = 0.6).`;
    } else if (nodeType === "facility") {
        nodeId = "FACILITY";
        typeName = siteName;
        baseRisk = "N/A";
        propRisk = "N/A";
        finalRisk = `${(scenData.cascade_risk || 0).toFixed(1)} / 100`;
        description = `The facility core service relies on cooling (${chNode.id || 'CH-001'}, strength: 0.8) and drainage water management (${wpNode.id || 'WP-001'}, strength: 0.6) to remain operational.`;
    }

    const titleEl = document.getElementById("nodeSidebarTitle");
    const idEl = document.getElementById("nodeSidebarId");
    const baseEl = document.getElementById("nodeSidebarBase");
    const propEl = document.getElementById("nodeSidebarProp");
    const finalEl = document.getElementById("nodeSidebarFinal");
    const descEl = document.getElementById("nodeSidebarDesc");

    if (titleEl) titleEl.textContent = typeName;
    if (idEl) idEl.textContent = nodeId;
    if (baseEl) baseEl.textContent = baseRisk;
    if (propEl) propEl.textContent = propRisk;
    if (finalEl) finalEl.textContent = finalRisk;
    if (descEl) descEl.textContent = description;
}

async function loadCascadeViewData() {
    try {
        const selElem = document.getElementById("cascadeFacilitySelector");
        if (selElem && selElem.value !== selectedCascadeSiteId) {
            selElem.value = selectedCascadeSiteId;
        }

        const url = `${API_BASE_URL}/api/facilities/${selectedCascadeSiteId}/cascade?scenario=${currentCascadeScenario}`;
        const res = await fetch(url);
        const data = await res.json();

        if (!data.success) return;
        cascadeDataCache = data;

        // Populate Key metrics
        const fc = data.facility_cascade || {};
        const normalScen = data.scenarios.find(s => s.scenario.toLowerCase() === "normal") || {};
        const activeScen = data.scenarios.find(s => s.scenario.toLowerCase() === currentCascadeScenario.toLowerCase()) || {};

        document.getElementById("casRiskScore").textContent = `${fc.current_risk.toFixed(1)} / 100`;
        const lvl = fc.level || "LOW";
        const levelEl = document.getElementById("casRiskLevel");
        if (levelEl) {
            levelEl.textContent = lvl;
            levelEl.className = `prov-badge lvl-${lvl}`;
            levelEl.style.backgroundColor = lvl === "CRITICAL" || lvl === "HIGH" ? "#EF4444" : (lvl === "ELEVATED" || lvl === "MODERATE" ? "#F59E0B" : "#10B981");
            levelEl.style.color = "#ffffff";
        }

        document.getElementById("casPeakRisk").textContent = `${fc.peak_risk.toFixed(1)} / 100`;
        document.getElementById("casWarningTime").textContent = fc.cascade_warning_time;
        if (fc.cascade_warning_time !== "No immediate cascade hazard predicted") {
            document.getElementById("casWarningTime").style.color = "#EF4444";
        } else {
            document.getElementById("casWarningTime").style.color = "#10B981";
        }

        const spof = fc.critical_spof || {};
        document.getElementById("casSpofName").textContent = spof.name || "Power Transformer";
        document.getElementById("casSpofDetail").textContent = `Risk consequence: ${spof.risk_consequence.toFixed(1)} / 100`;

        // Update Simulated Scenario Impact Stats
        document.getElementById("simBaselineRisk").textContent = `${normalScen.cascade_risk.toFixed(1)} / 100`;
        document.getElementById("simScenarioRisk").textContent = `${activeScen.cascade_risk.toFixed(1)} / 100`;
        if (activeScen.cascade_risk > normalScen.cascade_risk) {
            document.getElementById("simScenarioRisk").style.color = "#EF4444";
        } else {
            document.getElementById("simScenarioRisk").style.color = "var(--text-primary)";
        }

        const affectedAssetsStr = activeScen.affected_assets && activeScen.affected_assets.length > 0
            ? activeScen.affected_assets.join(", ")
            : "None";
        document.getElementById("simAffectedAssets").textContent = affectedAssetsStr;

        const affectedServicesStr = activeScen.affected_services && activeScen.affected_services.length > 0
            ? activeScen.affected_services.join(", ")
            : "None";
        document.getElementById("simAffectedServices").textContent = affectedServicesStr;

        // Update Nodes on visual flow chart (Graph)
        const nodes = data.dependency_graph.nodes || [];
        const txNode = nodes.find(n => n.type === "transformer") || {};
        const chNode = nodes.find(n => n.type === "chiller") || {};
        const wpNode = nodes.find(n => n.type === "water_pump") || {};

        const activeRisks = activeScen.node_risks || {};

        document.getElementById("graphTxId").textContent = txNode.id || "TX-001";
        document.getElementById("graphTxRisk").textContent = `${(activeRisks.transformer?.cascade_risk ?? 0).toFixed(1)} / 100`;

        document.getElementById("graphChId").textContent = chNode.id || "CH-001";
        document.getElementById("graphChRisk").textContent = `${(activeRisks.chiller?.cascade_risk ?? 0).toFixed(1)} / 100`;

        document.getElementById("graphWpId").textContent = wpNode.id || "WP-001";
        document.getElementById("graphWpRisk").textContent = `${(activeRisks.water_pump?.cascade_risk ?? 0).toFixed(1)} / 100`;

        document.getElementById("graphFacId").textContent = "FACILITY SYSTEM";
        document.getElementById("graphFacRisk").textContent = `${activeScen.cascade_risk.toFixed(1)} / 100`;

        // Update Node selection view
        updateCascadeNodeUI();
        populateCascadeNodeDetails(selectedCascadeNodeName);

        // Update Chart
        updateCascadeForecastChart(data.forecast || []);

    } catch (err) {
        console.error("Error loading cascade view data:", err);
    }
}

function updateCascadeForecastChart(hourlyPoints) {
    const canvas = document.getElementById("cascadeForecastChart");
    if (!canvas) return;
    if (!hourlyPoints || hourlyPoints.length === 0) return;

    const labels = hourlyPoints.map((p) => {
        const offset = p.hour_offset;
        if (offset === 0) return 'NOW';
        if (offset === 6) return '+6H';
        if (offset === 12) return '+12H';
        if (offset === 24) return '+24H';
        if (offset === 48) return '+48H';
        if (offset === 71 || offset === 72) return '+72H';
        return '';
    });

    const txScores = hourlyPoints.map(p => p.transformer_risk);
    const chScores = hourlyPoints.map(p => p.chiller_risk);
    const wpScores = hourlyPoints.map(p => p.water_pump_risk);
    const cascadeScores = hourlyPoints.map(p => p.cascade_risk);

    if (cascadeForecastChart) {
        cascadeForecastChart.destroy();
    }

    cascadeForecastChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Cascade Consequence',
                    data: cascadeScores,
                    borderColor: '#A855F7',
                    backgroundColor: 'rgba(168, 85, 247, 0.05)',
                    borderWidth: 3.5,
                    fill: true,
                    tension: 0.2,
                    pointRadius: 1
                },
                {
                    label: 'Transformer Risk',
                    data: txScores,
                    borderColor: '#EF4444',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.2,
                    pointRadius: 1
                },
                {
                    label: 'Chiller Risk',
                    data: chScores,
                    borderColor: '#F59E0B',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.2,
                    pointRadius: 1
                },
                {
                    label: 'Water Pump Risk',
                    data: wpScores,
                    borderColor: '#3B82F6',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.2,
                    pointRadius: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'var(--border-subtle)' },
                    ticks: { color: 'var(--text-secondary)' }
                },
                x: {
                    grid: { color: 'transparent' },
                    ticks: { color: 'var(--text-secondary)' }
                }
            },
            plugins: {
                legend: {
                    labels: { color: 'var(--text-primary)', font: { family: 'JetBrains Mono' } }
                }
            }
        }
    });
}


/* ============================================================
   PHASE 17: PREDICTIVE CLIMATE RISK & FACILITY FAILURE FORECASTING
   ============================================================ */

let predictiveForecastChart = null;
let selectedPredictiveSiteId = "CBE-001";
let predictiveDecisionContext = null;

function handlePredictiveFacilitySelection(siteId) {
    selectedPredictiveSiteId = siteId;
    currentSelectedSiteId = siteId;
    selectedDecisionSiteId = siteId;

    const dropdownIds = [
        "ovFacilitySelect",
        "siteSelector",
        "predictiveFacilitySelector",
        "decisionFacilitySelector",
        "incP19FacilitySelector",
        "scenFacilitySelector",
        "cascadeFacilitySelector"
    ];
    dropdownIds.forEach(id => {
        const sel = document.getElementById(id);
        if (sel && sel.value !== siteId) {
            sel.value = siteId;
        }
    });

    loadPredictiveRiskData();
}

function getRiskBadgeHTML(level) {
    const lvl = (level || "LOW").toUpperCase();
    if (lvl === "CRITICAL") return `<span class="ma-status-badge badge-crit" style="background:#EF4444; color:#fff; padding:2px 8px; border-radius:4px; font-weight:700;"> CRITICAL</span>`;
    if (lvl === "HIGH") return `<span class="ma-status-badge badge-warning" style="background:#F97316; color:#fff; padding:2px 8px; border-radius:4px; font-weight:700;">️ HIGH</span>`;
    if (lvl === "ELEVATED" || lvl === "MODERATE" || lvl === "WATCH" || lvl === "WARNING") return `<span class="ma-status-badge badge-warning" style="background:#F59E0B; color:#000; padding:2px 8px; border-radius:4px; font-weight:700;"> ${lvl}</span>`;
    return `<span class="ma-status-badge badge-low" style="background:#10B981; color:#fff; padding:2px 8px; border-radius:4px; font-weight:700;"> LOW</span>`;
}

function getHumanReadableFeatureName(feat) {
    if (!feat || feat === 'undefined') return "Operational Parameter";
    const mappings = {
        "MPD_roll60m_mean": "Max Power Demand",
        "KW_roll30m_mean": "Active Power Load",
        "THDVL1_roll60m_mean": "Voltage harmonic distortion",
        "THDVL1_roll30m_mean": "Voltage harmonic distortion",
        "OTI": "Oil temperature trend",
        "OTI_roll60m_mean": "Oil temperature trend",
        "WTI": "Transformer thermal condition",
        "WTI_roll60m_mean": "Transformer thermal condition",
        "OLI": "Cooling performance",
        "OLI_roll30m_mean": "Cooling performance",
        "VL1": "Phase L1 Voltage",
        "VL23": "Phase L23 Voltage",
        "VL31": "Phase L31 Voltage",
        "IL1": "Phase L1 Load Current",
        "KW": "Active Power Demand",
        "KVA": "Apparent Power Load",
        "Avg_PF": "Power factor variation",
        "Avg_PF_roll60m_mean": "Power factor variation",
        "FRQ": "Grid Frequency Stability"
    };
    const clean = mappings[feat] || feat;
    if (clean === "undefined" || !clean) return "Operational Parameter";
    return clean;
}

let currentPredictiveScenario = null;

async function togglePredictiveScenario(isActive) {
    currentPredictiveScenario = isActive ? "HEATWAVE" : null;
    const badge = document.getElementById("predDataSourceBadge");
    if (badge) {
        if (isActive) {
            badge.textContent = " CONTROLLED SCENARIO";
            badge.style.background = "#D97706";
        } else {
            badge.textContent = " LIVE CLIMATE — Open-Meteo";
            badge.style.background = "var(--status-success)";
        }
    }
    await loadPredictiveRiskData();
}

function refocusToDecisionCenter() {
    navigateToDecisionCenter(selectedPredictiveSiteId, null);
}

function takePreventiveActionFromPredictive() {
    navigateToDecisionCenter(selectedPredictiveSiteId, predictiveDecisionContext);
}

async function loadPredictiveRiskData() {
    try {
        const selElem = document.getElementById("predictiveFacilitySelector");
        if (selElem && selElem.value !== selectedPredictiveSiteId) {
            selElem.value = selectedPredictiveSiteId;
        }

        const url = currentPredictiveScenario
            ? `${API_BASE_URL}/api/facilities/${selectedPredictiveSiteId}/prediction?scenario=${currentPredictiveScenario}`
            : `${API_BASE_URL}/api/facilities/${selectedPredictiveSiteId}/prediction`;

        const res = await fetch(url);
        const data = await res.json();

        if (!data.success || !data.prediction) return;
        const pred = data.prediction;

        // Facility Coordinates & Names
        const nameElem = document.getElementById("predFacName");
        if (nameElem) nameElem.textContent = pred.site_name;
        const cityElem = document.getElementById("predFacCityCoords");
        if (cityElem) cityElem.textContent = `${pred.city} | ${pred.latitude}° N, ${pred.longitude}° E`;

        // Update Scenario / Weather Provenance Badge (Requirement 6)
        const badge = document.getElementById("predDataSourceBadge");
        if (badge) {
            if (pred.controlled_scenario) {
                badge.textContent = "CONTROLLED SCENARIO";
                badge.style.background = "#D97706";
            } else {
                const weatherStatus = (pred.data_source || {}).weather_source_status || 'UNKNOWN';
                if (weatherStatus === 'LIVE') {
                    badge.textContent = "LIVE WEATHER • OPEN-METEO";
                    badge.className = "prov-badge live-weather";
                    badge.style.background = ""; // Reset inline color to let CSS take over
                } else if (weatherStatus === 'UNAVAILABLE') {
                    badge.textContent = "LIVE WEATHER UNAVAILABLE";
                    badge.className = "prov-badge badge-ds";
                    badge.style.background = "#EF4444";
                } else {
                    badge.textContent = `WEATHER ${weatherStatus}`;
                    badge.className = "prov-badge badge-ds";
                    badge.style.background = "#F59E0B";
                }
            }
        }

        const m = pred.milestones || {};
        const nowPt = m.NOW || {};
        const pt6 = m["6h"] || {};
        const pt24 = m["24h"] || {};
        const pt48 = m["48h"] || {};
        const pt72 = m["72h"] || {};

        // SECTION 1: CLIMATE OUTLOOK
        document.getElementById("outTempNow").textContent = `${nowPt.temperature !== undefined ? nowPt.temperature.toFixed(1) : '--'} °C`;
        document.getElementById("outTemp24").textContent = `${pt24.temperature !== undefined ? pt24.temperature.toFixed(1) : '--'} °C`;
        document.getElementById("outTemp48").textContent = `${pt48.temperature !== undefined ? pt48.temperature.toFixed(1) : '--'} °C`;
        document.getElementById("outTemp72").textContent = `${pt72.temperature !== undefined ? pt72.temperature.toFixed(1) : '--'} °C`;

        document.getElementById("outHumNow").textContent = `${nowPt.humidity !== undefined ? nowPt.humidity.toFixed(1) : '--'} %`;
        document.getElementById("outHum24").textContent = `${pt24.humidity !== undefined ? pt24.humidity.toFixed(1) : '--'} %`;
        document.getElementById("outHum48").textContent = `${pt48.humidity !== undefined ? pt48.humidity.toFixed(1) : '--'} %`;
        document.getElementById("outHum72").textContent = `${pt72.humidity !== undefined ? pt72.humidity.toFixed(1) : '--'} %`;

        document.getElementById("outRainNow").textContent = `${nowPt.rain !== undefined ? nowPt.rain.toFixed(1) : '--'} mm`;
        document.getElementById("outRain24").textContent = `${pt24.rain !== undefined ? pt24.rain.toFixed(1) : '--'} mm`;
        document.getElementById("outRain48").textContent = `${pt48.rain !== undefined ? pt48.rain.toFixed(1) : '--'} mm`;
        document.getElementById("outRain72").textContent = `${pt72.rain !== undefined ? pt72.rain.toFixed(1) : '--'} mm`;

        document.getElementById("outWindNow").textContent = `${nowPt.wind_speed !== undefined ? nowPt.wind_speed.toFixed(1) : '--'} km/h`;
        document.getElementById("outWind24").textContent = `${pt24.wind_speed !== undefined ? pt24.wind_speed.toFixed(1) : '--'} km/h`;
        document.getElementById("outWind48").textContent = `${pt48.wind_speed !== undefined ? pt48.wind_speed.toFixed(1) : '--'} km/h`;
        document.getElementById("outWind72").textContent = `${pt72.wind_speed !== undefined ? pt72.wind_speed.toFixed(1) : '--'} km/h`;

        // Populate Climate Stress row inside the Climate Outlook Table
        const outStressNowEl = document.getElementById("outStressNow");
        if (outStressNowEl) outStressNowEl.textContent = nowPt.climate_stress !== undefined ? nowPt.climate_stress.toFixed(1) : '--';
        const outStress24El = document.getElementById("outStress24");
        if (outStress24El) outStress24El.textContent = pt24.climate_stress !== undefined ? pt24.climate_stress.toFixed(1) : '--';
        const outStress48El = document.getElementById("outStress48");
        if (outStress48El) outStress48El.textContent = pt48.climate_stress !== undefined ? pt48.climate_stress.toFixed(1) : '--';
        const outStress72El = document.getElementById("outStress72");
        if (outStress72El) outStress72El.textContent = pt72.climate_stress !== undefined ? pt72.climate_stress.toFixed(1) : '--';

        const tr = (pred.trend_analysis || {}).trend || "STABLE";

        // SECTION 2: INFRASTRUCTURE RISK STATUS
        const eq = pred.equipment || {};
        const tx = eq.transformer || {};
        const ch = eq.chiller || {};
        const wp = eq.water_pump || {};

        document.getElementById("txAssetId").textContent = tx.equipment_id || "TR-001";
        document.getElementById("txAssetRiskNow").textContent = `${nowPt.transformer_risk !== undefined ? nowPt.transformer_risk.toFixed(1) : '--'} / 100`;
        document.getElementById("txAssetRisk72").textContent = `${pt72.transformer_risk !== undefined ? pt72.transformer_risk.toFixed(1) : '--'} / 100`;

        document.getElementById("chAssetId").textContent = ch.equipment_id || "CH-001";
        document.getElementById("chAssetRiskNow").textContent = `${nowPt.chiller_risk !== undefined ? nowPt.chiller_risk.toFixed(1) : '--'} / 100`;
        document.getElementById("chAssetRisk72").textContent = `${pt72.chiller_risk !== undefined ? pt72.chiller_risk.toFixed(1) : '--'} / 100`;

        document.getElementById("wpAssetId").textContent = wp.equipment_id || "WP-001";
        document.getElementById("wpAssetRiskNow").textContent = `${nowPt.water_pump_risk !== undefined ? nowPt.water_pump_risk.toFixed(1) : '--'} / 100`;
        document.getElementById("wpAssetRisk72").textContent = `${pt72.water_pump_risk !== undefined ? pt72.water_pump_risk.toFixed(1) : '--'} / 100`;

        // SECTION 5: OVERALL CASCADE RISK
        document.getElementById("overallCascadeRiskNow").textContent = `${nowPt.cascade_risk !== undefined ? nowPt.cascade_risk.toFixed(1) : '--'} / 100`;
        document.getElementById("overallCascadeRisk72").textContent = `${pt72.cascade_risk !== undefined ? pt72.cascade_risk.toFixed(1) : '--'} / 100`;

        // Populate Current Risk KPI (Requirement 3, 4)
        const cascadeRiskNow = nowPt.cascade_risk !== undefined ? nowPt.cascade_risk : 0.0;
        const cascadeRiskLvl = cascadeRiskNow > 75 ? "CRITICAL" : (cascadeRiskNow > 50 ? "HIGH" : (cascadeRiskNow > 35 ? "ELEVATED" : (cascadeRiskNow > 20 ? "WATCH" : "LOW")));
        
        const currentRiskNumEl = document.getElementById("predCurrentRiskNum");
        const currentRiskLvlEl = document.getElementById("predCurrentRiskLvl");
        if (currentRiskNumEl) currentRiskNumEl.textContent = cascadeRiskNow.toFixed(1);
        if (currentRiskLvlEl) {
            currentRiskLvlEl.textContent = cascadeRiskLvl;
            currentRiskLvlEl.className = `prov-badge lvl-${cascadeRiskLvl}`;
            currentRiskLvlEl.style.backgroundColor = cascadeRiskLvl === "CRITICAL" || cascadeRiskLvl === "HIGH" ? "#EF4444" : (cascadeRiskLvl === "ELEVATED" || cascadeRiskLvl === "WATCH" ? "#F59E0B" : "#10B981");
            currentRiskLvlEl.style.color = "#ffffff";
        }

        // Show Trend (Requirement 4)
        const trendLabelEl = document.getElementById("predRiskTrendLabel");
        if (trendLabelEl) {
            const trendText = tr === "RISING" ? "↑ RISING NEXT 72 HOURS" : (tr === "FALLING" ? "↓ FALLING NEXT 72 HOURS" : "→ STABLE NEXT 72 HOURS");
            trendLabelEl.textContent = trendText;
            trendLabelEl.style.color = tr === "RISING" ? "#EF4444" : (tr === "FALLING" ? "#10B981" : "var(--text-secondary)");
        }

        // Populate Asset Risk summary cards
        const txNow = nowPt.transformer_risk !== undefined ? nowPt.transformer_risk : 0;
        const txLvl = txNow > 75 ? "CRITICAL" : (txNow > 50 ? "HIGH" : (txNow > 35 ? "ELEVATED" : (txNow > 20 ? "WATCH" : "LOW")));
        
        const txValEl = document.getElementById("predTxRiskNow");
        const tx72El = document.getElementById("predTxRisk72");
        const txBadgeEl = document.getElementById("predTxRiskBadge");
        const txTrendEl = document.getElementById("predTxRiskTrend");

        if (txValEl) txValEl.textContent = `${txNow.toFixed(1)} / 100`;
        if (tx72El) tx72El.textContent = `${(pt72.transformer_risk || 0).toFixed(1)} / 100`;
        if (txBadgeEl) {
            txBadgeEl.textContent = txLvl;
            txBadgeEl.className = `prov-badge lvl-${txLvl}`;
            txBadgeEl.style.backgroundColor = txLvl === "CRITICAL" || txLvl === "HIGH" ? "#EF4444" : (txLvl === "ELEVATED" || txLvl === "WATCH" ? "#F59E0B" : "#2563EB");
            txBadgeEl.style.color = "#ffffff";
        }
        
        const txDelta = (pt72.transformer_risk || 0) - txNow;
        const txTrend = txDelta > 2.0 ? "Increasing" : (txDelta < -2.0 ? "Decreasing" : "Stable");
        if (txTrendEl) {
            txTrendEl.textContent = txTrend.toUpperCase();
            txTrendEl.style.color = txTrend === "Increasing" ? "#EF4444" : (txTrend === "Decreasing" ? "#10B981" : "#F59E0B");
        }

        const chNow = nowPt.chiller_risk !== undefined ? nowPt.chiller_risk : 0;
        const chLvl = chNow > 75 ? "CRITICAL" : (chNow > 50 ? "HIGH" : (chNow > 35 ? "ELEVATED" : (chNow > 20 ? "WATCH" : "LOW")));
        
        const chValEl = document.getElementById("predChRiskNow");
        const ch72El = document.getElementById("predChRisk72");
        const chBadgeEl = document.getElementById("predChRiskBadge");
        const chTrendEl = document.getElementById("predChRiskTrend");

        if (chValEl) chValEl.textContent = `${chNow.toFixed(1)} / 100`;
        if (ch72El) ch72El.textContent = `${(pt72.chiller_risk || 0).toFixed(1)} / 100`;
        if (chBadgeEl) {
            chBadgeEl.textContent = chLvl;
            chBadgeEl.className = `prov-badge lvl-${chLvl}`;
            chBadgeEl.style.backgroundColor = chLvl === "CRITICAL" || chLvl === "HIGH" ? "#EF4444" : (chLvl === "ELEVATED" || chLvl === "WATCH" ? "#F59E0B" : "#2563EB");
            chBadgeEl.style.color = "#ffffff";
        }
        
        const chDelta = (pt72.chiller_risk || 0) - chNow;
        const chTrend = chDelta > 2.0 ? "Increasing" : (chDelta < -2.0 ? "Decreasing" : "Stable");
        if (chTrendEl) {
            chTrendEl.textContent = chTrend.toUpperCase();
            chTrendEl.style.color = chTrend === "Increasing" ? "#EF4444" : (chTrend === "Decreasing" ? "#10B981" : "#F59E0B");
        }

        const wpNow = nowPt.water_pump_risk !== undefined ? nowPt.water_pump_risk : 0;
        const wpLvl = wpNow > 75 ? "CRITICAL" : (wpNow > 50 ? "HIGH" : (wpNow > 35 ? "ELEVATED" : (wpNow > 20 ? "WATCH" : "LOW")));
        
        const wpValEl = document.getElementById("predWpRiskNow");
        const wp72El = document.getElementById("predWpRisk72");
        const wpBadgeEl = document.getElementById("predWpRiskBadge");
        const wpTrendEl = document.getElementById("predWpRiskTrend");

        if (wpValEl) wpValEl.textContent = `${wpNow.toFixed(1)} / 100`;
        if (wp72El) wp72El.textContent = `${(pt72.water_pump_risk || 0).toFixed(1)} / 100`;
        if (wpBadgeEl) {
            wpBadgeEl.textContent = wpLvl;
            wpBadgeEl.className = `prov-badge lvl-${wpLvl}`;
            wpBadgeEl.style.backgroundColor = wpLvl === "CRITICAL" || wpLvl === "HIGH" ? "#EF4444" : (wpLvl === "ELEVATED" || wpLvl === "WATCH" ? "#F59E0B" : "#2563EB");
            wpBadgeEl.style.color = "#ffffff";
        }
        
        const wpDelta = (pt72.water_pump_risk || 0) - wpNow;
        const wpTrend = wpDelta > 2.0 ? "Increasing" : (wpDelta < -2.0 ? "Decreasing" : "Stable");
        if (wpTrendEl) {
            wpTrendEl.textContent = wpTrend.toUpperCase();
            wpTrendEl.style.color = wpTrend === "Increasing" ? "#EF4444" : (wpTrend === "Decreasing" ? "#10B981" : "#F59E0B");
        }

        // Highlight highest risk asset card
        const assetRisks = [
            { name: "transformer", key: "Tx", cardId: "predTxSummaryCard", titleText: "Power Transformer", score72: pt72.transformer_risk || 0 },
            { name: "chiller", key: "Ch", cardId: "predChSummaryCard", titleText: "HVAC Chiller", score72: pt72.chiller_risk || 0 },
            { name: "water_pump", key: "Wp", cardId: "predWpSummaryCard", titleText: "Water Pump", score72: pt72.water_pump_risk || 0 }
        ];
        const highest = assetRisks.reduce((prev, curr) => (prev.score72 > curr.score72) ? prev : curr);

        assetRisks.forEach(item => {
            const card = document.getElementById(item.cardId);
            if (card) {
                const strong = card.querySelector("strong");
                if (strong) {
                    if (item.name === highest.name) {
                        strong.innerHTML = `${item.titleText} <span class="prov-badge" style="background: #EF4444; color: #0B1120; font-size: 9.5px; font-weight: 700; border-radius: 3px; padding: 1px 4px; margin-left: 6px; text-transform: uppercase;">HIGHEST EXPOSURE</span>`;
                        card.style.borderColor = "#EF4444";
                    } else {
                        strong.textContent = item.titleText;
                        card.style.borderColor = "var(--border-subtle)";
                    }
                }
            }
        });

        // SECTION 6: WHY IS RISK CHANGING? (SHAP XAI) (Requirement 9, 10)
        const shapSumElem = document.getElementById("predShapSummary");
        const shapListElem = document.getElementById("predShapFactorsList");
        const shapData = pred.shap_explanation || {};
        if (shapSumElem) shapSumElem.textContent = shapData.summary || "XAI evaluation complete.";
        
        if (shapListElem && shapData.factors && shapData.factors.length > 0) {
            // Take top 3 factors only (Requirement 9)
            const top3Factors = shapData.factors.slice(0, 3);
            const maxShap = Math.max(...top3Factors.map(x => Math.abs(x.shap_value || 0)), 1);
            
            shapListElem.innerHTML = top3Factors.map(f => {
                const isPos = f.direction === "increases_risk";
                const icon = isPos ? "↑" : "↓";
                const color = isPos ? "#EF4444" : "#10B981";
                const shapVal = f.shap_value >= 0 ? `+${f.shap_value.toFixed(2)}` : `${f.shap_value.toFixed(2)}`;
                const barWidth = Math.min(100, Math.max(10, Math.round((Math.abs(f.shap_value) / maxShap) * 100)));
                
                // Human-readable feature name translation (Requirement 10)
                let displayName = f.description && !f.description.includes('_') ? f.description : getHumanReadableFeatureName(f.feature || '');
                if (!displayName || displayName === 'undefined') displayName = "Operational Parameter";
                const valStr = f.value !== undefined && f.value !== null ? f.value.toFixed(1) : '--';

                return `
                    <div style="margin-bottom:12px; width: 100%;">
                        <div style="display:flex; justify-content:space-between; font-size:14.5px; margin-bottom:4px; font-weight: 500;">
                            <span style="color:var(--text-secondary);">${displayName} (${valStr})</span>
                            <strong style="color:${color}; font-weight:700; font-size:13.5px;">${icon} ${shapVal} SHAP</strong>
                        </div>
                        <div style="background:var(--bg-app); height:6px; border-radius:3px; overflow:hidden; border:1px solid var(--border-subtle);">
                            <div style="background:${color}; width:${barWidth}%; height:100%;"></div>
                        </div>
                    </div>
                `;
            }).join("");
        } else if (shapListElem) {
            shapListElem.innerHTML = '<p style="font-size:12px; color:var(--text-muted);">Explanation unavailable</p>';
        }

        // SECTION 6: CLIMATE EVENT ALERT STATUS (Requirement 11)
        let activeEventName = "None Detected";
        let activeEventSeverity = "NORMAL";
        let isControlled = pred.controlled_scenario;

        const hw = (pred.natural_events && pred.natural_events.heatwave) || {};
        const rain = (pred.natural_events && pred.natural_events.heavy_rainfall) || {};
        const wind = (pred.natural_events && pred.natural_events.high_wind) || {};

        if (hw.detected) {
            activeEventName = "Heatwave";
            activeEventSeverity = hw.severity || "WATCH";
        } else if (rain.detected) {
            activeEventName = "Heavy Rainfall";
            activeEventSeverity = "WARNING";
        } else if (wind.detected) {
            activeEventName = "High Wind / Storm";
            activeEventSeverity = "WARNING";
        }

        // Populate dynamic Climate Event secondary status indicator
        const indicator = document.getElementById("predClimateEventIndicator");
        if (indicator) {
            if (isControlled) {
                indicator.innerHTML = `<span class="prov-badge" style="background:#D97706; color:#0B1120; font-weight:800; font-size:11px; padding:2px 6px; border-radius:4px; margin-right:8px;">SIMULATION</span> Controlled scenario active: environmental stress simulated.`;
            } else if (activeEventName !== "None Detected") {
                let badgeCol = "#EF4444";
                if (activeEventSeverity === "WATCH") badgeCol = "#F59E0B";
                if (activeEventSeverity === "NORMAL") badgeCol = "#10B981";
                indicator.innerHTML = `<span class="prov-badge" style="background:${badgeCol}; color:#0B1120; font-weight:800; font-size:11px; padding:2px 6px; border-radius:4px; margin-right:8px;">${activeEventName.toUpperCase()} ${activeEventSeverity}</span> Climate alert active: monitoring ambient stress closely.`;
            } else {
                indicator.innerHTML = `<span class="prov-badge" style="background:#10B981; color:#ffffff; font-weight:800; font-size:11px; padding:2px 6px; border-radius:4px; margin-right:8px;">NOMINAL</span> Regional environmental conditions are stable.`;
            }
        }

        // SECTION 7: RECOMMENDED PREVENTIVE ACTION (Requirement 12)
        const eqNowRisks = {
            "transformer": nowPt.transformer_risk || 0,
            "chiller": nowPt.chiller_risk || 0,
            "water_pump": nowPt.water_pump_risk || 0
        };

        const eq72Risks = [
            { name: "Power Transformer", id: tx.equipment_id || "TR-001", riskNow: eqNowRisks.transformer, risk72: pt72.transformer_risk || 0, action: tx.recommended_action || "Routine monitoring." },
            { name: "HVAC Chiller", id: ch.equipment_id || "CH-001", riskNow: eqNowRisks.chiller, risk72: pt72.chiller_risk || 0, action: ch.recommended_action || "Routine monitoring." },
            { name: "Water Pump", id: wp.equipment_id || "WP-001", riskNow: eqNowRisks.water_pump, risk72: pt72.water_pump_risk || 0, action: wp.recommended_action || "Routine monitoring." }
        ];

        const highestAsset = eq72Risks.reduce((prev, curr) => (prev.risk72 > curr.risk72) ? prev : curr);

        const typeMap = {
            "Power Transformer": "transformer",
            "HVAC Chiller": "chiller",
            "Water Pump": "water_pump"
        };
        predictiveDecisionContext = {
            type: typeMap[highestAsset.name] || "transformer",
            name: highestAsset.name,
            id: highestAsset.id,
            riskNow: highestAsset.riskNow,
            risk72: highestAsset.risk72
        };

        let assetTrend = "Stable";
        const delta = highestAsset.risk72 - highestAsset.riskNow;
        if (delta > 2.0) {
            assetTrend = "Increasing";
        } else if (delta < -2.0) {
            assetTrend = "Decreasing";
        }

        // Keep compatibility hidden fields updated
        const txValCompat = document.getElementById("predTxRiskVal");
        if (txValCompat) txValCompat.textContent = `${txNow.toFixed(1)} / 100`;
        const txLvlCompat = document.getElementById("predTxRiskLvl");
        if (txLvlCompat) txLvlCompat.textContent = txLvl;

        const chValCompat = document.getElementById("predChRiskVal");
        if (chValCompat) chValCompat.textContent = `${chNow.toFixed(1)} / 100`;
        const chLvlCompat = document.getElementById("predChRiskLvl");
        if (chLvlCompat) chLvlCompat.textContent = chLvl;

        const wpValCompat = document.getElementById("predWpRiskVal");
        if (wpValCompat) wpValCompat.textContent = `${wpNow.toFixed(1)} / 100`;
        const wpLvlCompat = document.getElementById("predWpRiskLvl");
        if (wpLvlCompat) wpLvlCompat.textContent = wpLvl;

        const tpAssetCompat = document.getElementById("tpActiveAsset");
        if (tpAssetCompat) tpAssetCompat.textContent = `${highestAsset.name.toUpperCase()} (${highestAsset.id})`;
        const tpAssetRiskCompat = document.getElementById("tpActiveAssetRisk");
        if (tpAssetRiskCompat) tpAssetRiskCompat.textContent = `${highestAsset.riskNow.toFixed(1)}  ${highestAsset.risk72.toFixed(1)} / 100 (72H)`;
        const tpAssetTrendCompat = document.getElementById("tpActiveAssetTrend");
        if (tpAssetTrendCompat) tpAssetTrendCompat.textContent = assetTrend.toUpperCase();

        document.getElementById("tpActiveAssetAction").textContent = highestAsset.action;

        // SECTION 4: Update Trajectory Chart
        updatePredictiveRiskChart(pred.hourly_forecast || []);
    } catch (err) {
        console.error("Error loading predictive risk data:", err);
    }
}

function formatForecastTimestamp(ts) {
    if (!ts) return "";
    try {
        const parts = ts.split("T");
        if (parts.length === 2) {
            const dateParts = parts[0].split("-");
            const timeStr = parts[1];
            if (dateParts.length === 3) {
                const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                const y = dateParts[0];
                const m = months[parseInt(dateParts[1], 10) - 1] || dateParts[1];
                const d = parseInt(dateParts[2], 10);
                return `${d} ${m} ${y} · ${timeStr}`;
            }
        }
        return ts;
    } catch (e) {
        return ts;
    }
}

function updatePredictiveRiskChart(hourlyPoints) {
    const canvas = document.getElementById("predictiveForecastChart");
    if (!canvas) return;

    if (!hourlyPoints || hourlyPoints.length === 0) return;

    const labels = hourlyPoints.map((p, idx) => {
        const offset = p.hour_offset;
        if (offset === 0) return 'NOW';
        if (offset === 6) return '+6H';
        if (offset === 12) return '+12H';
        if (offset === 24) return '+24H';
        if (offset === 48) return '+48H';
        if (offset === 71 || offset === 72) return '+72H';
        return '';
    });

    const cascadeScores = hourlyPoints.map(p => p.cascade_risk);
    const transformerScores = hourlyPoints.map(p => p.transformer_risk);
    const chillerScores = hourlyPoints.map(p => p.chiller_risk);
    const pumpScores = hourlyPoints.map(p => p.water_pump_risk);

    if (predictiveForecastChart) {
        predictiveForecastChart.destroy();
    }

    predictiveForecastChart = new Chart(canvas, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Overall Cascade Stress',
                    data: cascadeScores,
                    borderColor: '#06B6D4',
                    backgroundColor: 'rgba(6, 182, 212, 0.03)',
                    borderWidth: 3.5,
                    fill: true,
                    tension: 0.2,
                    pointRadius: 1
                },
                {
                    label: 'Transformer',
                    data: transformerScores,
                    borderColor: '#EF4444',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.2,
                    pointRadius: 1
                },
                {
                    label: 'HVAC Chiller',
                    data: chillerScores,
                    borderColor: '#F59E0B',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.2,
                    pointRadius: 1
                },
                {
                    label: 'Water Pump',
                    data: pumpScores,
                    borderColor: '#3B82F6',
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.2,
                    pointRadius: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.08)' },
                    ticks: { color: '#94A3B8' }
                },
                x: {
                    grid: { color: 'rgba(255, 255, 255, 0.08)' },
                    ticks: { color: '#94A3B8' }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        color: '#94A3B8',
                        boxWidth: 12,
                        font: {
                            size: 11,
                            weight: 'bold'
                        }
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        title: function(context) {
                            const index = context[0].dataIndex;
                            const pt = hourlyPoints[index];
                            const dateStr = pt.timestamp ? formatForecastTimestamp(pt.timestamp) : '';
                            const offsetStr = pt.hour_offset === 0 ? 'NOW' : `+${pt.hour_offset} hours`;
                            return `${dateStr} (${offsetStr})`;
                        }
                    }
                }
            }
        }
    });
}

async function loadPredictiveAlerts() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/predictive-alerts`);
        const data = await res.json();
        const container = document.getElementById("predictiveAlertsContainer");
        if (!container) return;

        if (!data.success || !data.alerts || data.alerts.length === 0) {
            container.innerHTML = `<div style="background:var(--bg-secondary); padding:12px; border-radius:6px; color:var(--text-muted); font-size:13px;"> All facilities operating within normal predictive parameters. No critical early warnings.</div>`;
            return;
        }

        container.innerHTML = data.alerts.map(a => {
            const isCrit = a.severity === "CRITICAL" || a.severity === "HIGH";
            const borderCol = isCrit ? "#EF4444" : "#F59E0B";
            const bgCol = isCrit ? "rgba(239, 68, 68, 0.08)" : "rgba(245, 158, 11, 0.08)";
            return `
                <div style="background:${bgCol}; border-left:4px solid ${borderCol}; padding:14px; border-radius:6px; border-top:1px solid var(--border-color); border-right:1px solid var(--border-color); border-bottom:1px solid var(--border-color);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <strong style="font-size:14px; color:var(--text-primary);">${a.title}</strong>
                        ${getRiskBadgeHTML(a.severity)}
                    </div>
                    <p style="font-size:12.5px; color:var(--text-secondary); margin-bottom:8px;">${a.message}</p>
                    <small style="color:var(--text-muted); font-weight:700;">RECOMMENDED OPERATOR ACTION: </small>
                    <span style="font-size:12px; color:var(--accent-cyan); font-weight:600;">${a.recommended_action}</span>
                </div>
            `;
        }).join("");

    } catch (err) {
        console.error("Error loading predictive alerts:", err);
    }
}

async function loadFacilityRiskRankings() {

    try {
        const res = await fetch(`${API_BASE_URL}/api/facility-risk-ranking`);
        const data = await res.json();
        const tbody = document.getElementById("predRankingTableBody");
        if (!tbody) return;

        if (!data.success || !data.rankings || data.rankings.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" style="text-align:center; color:var(--text-muted);">No facility rankings available.</td></tr>`;
            return;
        }

        tbody.innerHTML = data.rankings.map(r => `
            <tr style="${r.site_id === selectedPredictiveSiteId ? 'background:rgba(6,182,212,0.1);' : ''}">
                <td style="font-weight:700; color:var(--accent-cyan);">#${r.rank}</td>
                <td><strong>${r.site_name}</strong> <small style="color:var(--text-muted);">(${r.site_id})</small></td>
                <td>${r.city}</td>
                <td style="font-weight:800; font-size:14px;">${r.overall_facility_risk} / 100</td>
                <td>${getRiskBadgeHTML(r.risk_level)}</td>
                <td>${r.transformer_risk} / 100</td>
                <td>${r.chiller_risk} / 100</td>
                <td>${r.water_pump_risk} / 100 (DS)</td>
                <td><small style="color:var(--text-secondary);">Prioritize <strong>${r.highest_risk_equipment}</strong> inspection & mitigation.</small></td>
            </tr>
        `).join("");

    } catch (err) {
        console.error("Error loading facility rankings:", err);
    }
}


/* ============================================================
   PHASE 3B: DECISION CENTER — CLIMATE RISK RESPONSE
   ============================================================ */

let selectedDecisionSiteId = "CBE-001";
let decisionViewMode = "OPERATOR";
let rawDecisionActionsCache = [];
let currentTopActionId = null;
let decisionContextAsset = null;     // { type, name, id, riskNow, risk72 }
let decisionCachedPrediction = null; // full prediction object for current facility
let decisionCachedDecisions = null;  // full decisions API response
let decisionActiveAction = null;
let decisionMitigationRequestKey = null;
let decisionLoadRequestId = 0;
let isMitigationSimulated = false;

function updateDecisionActionButtons() {
    const btnsGroup = document.getElementById("tpActionButtonsGroup");
    if (!btnsGroup) return;

    const simulateBtn = document.getElementById("dcSimulateMitigationBtn");
    const topAction = decisionActiveAction;
    if (!topAction) {
        btnsGroup.innerHTML = "";
        return;
    }

    const st = (topAction.status || "PENDING").toUpperCase();

    if (st === "COMPLETED") {
        btnsGroup.innerHTML = `<span class="prov-badge live-weather" style="background:#10B981; color:#ffffff; font-weight:700; padding:4px 8px; border-radius:4px;">COMPLETED</span>`;
        if (simulateBtn) simulateBtn.style.display = "none";
    } else if (st === "IN_PROGRESS") {
        btnsGroup.innerHTML = `
            <button type="button" class="btn-primary" style="background: var(--brand-accent, #06B6D4); color: #0B1120; border: none; font-weight:700; padding:6px 12px; border-radius:4px; cursor:pointer;" onclick="updateActionStatus('${currentTopActionId}', 'COMPLETED')">MARK COMPLETED</button>
        `;
        if (simulateBtn) simulateBtn.style.display = "none";
    } else {
        if (!isMitigationSimulated) {
            if (simulateBtn) {
                simulateBtn.style.display = "inline-block";
                simulateBtn.disabled = false;
                simulateBtn.textContent = "SIMULATE MITIGATION";
            }
            btnsGroup.innerHTML = "";
        } else {
            if (simulateBtn) {
                simulateBtn.style.display = "inline-block";
                simulateBtn.disabled = false;
                simulateBtn.textContent = "RUN AGAIN";
            }
            btnsGroup.innerHTML = `
                <span class="prov-badge" style="background: #10B981; color: #ffffff; font-weight: 700; padding: 6px 12px; border-radius: 4px; font-size: 12.5px; height: 38px; display: inline-flex; align-items: center; box-sizing: border-box; vertical-align: middle;">SIMULATION COMPLETE</span>
                <button type="button" class="btn-primary" style="background: var(--brand-accent, #06B6D4); color: #0B1120; border: none; font-weight:700; padding:6px 16px; border-radius:4px; cursor:pointer; height: 38px; box-sizing: border-box; vertical-align: middle; margin-left: 8px;" onclick="handleTopActionStart()">START ACTION</button>
                <button type="button" class="btn-secondary" style="background: transparent; color: var(--text-muted); border: 1px solid var(--border-subtle); padding:6px 12px; border-radius:4px; cursor:pointer; margin-left:8px; height: 38px; box-sizing: border-box; vertical-align: middle;" onclick="handleTopActionDismiss()">DISMISS</button>
            `;
        }
    }
}

// Navigate here from Predictive Risk — carries facility + asset context
function navigateToDecisionCenter(siteId, assetContext) {
    selectedDecisionSiteId = siteId || selectedDecisionSiteId;
    selectedPredictiveSiteId = selectedDecisionSiteId;
    currentSelectedSiteId = selectedDecisionSiteId;
    decisionContextAsset = assetContext || null;

    // Sync all dropdowns
    ['decisionFacilitySelector', 'predictiveFacilitySelector', 'ovFacilitySelect', 'siteSelector',
     'incP19FacilitySelector', 'scenFacilitySelector'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = selectedDecisionSiteId;
    });

    showView("decision");
}

function handleDecisionFacilitySelection(siteId) {
    selectedDecisionSiteId = siteId;
    selectedPredictiveSiteId = siteId;
    currentSelectedSiteId = siteId;
    decisionContextAsset = null; // clear passed context on manual switch
    clearMitigationProjection();

    ['predictiveFacilitySelector', 'ovFacilitySelect', 'siteSelector',
     'incP19FacilitySelector', 'scenFacilitySelector', 'cascadeFacilitySelector'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = siteId;
    });

    loadDecisionCenterData();
}

function toggleDecisionViewMode(mode) {
    decisionViewMode = mode;
}

function selectDecisionAsset(assetType) {
    if (!decisionCachedDecisions || !decisionCachedPrediction) return;

    const fd = decisionCachedDecisions;
    const pred = decisionCachedPrediction;
    const m = pred.milestones;
    const nowPt = m.NOW || {};
    const pt72 = m['72h'] || {};

    // Find matching decision for selected asset
    const matchedDec = (fd.decisions || []).find(d =>
        d.equipment_type && d.equipment_type.toUpperCase().replace(/[^A-Z_]/g, '') ===
        assetType.toUpperCase().replace(/[^A-Z_]/g, '')
    ) || fd.top_action;

    if (!matchedDec) return;

    // Update asset context
    const riskNow = assetType === 'transformer' ? (nowPt.transformer_risk || 0)
                  : assetType === 'chiller' ? (nowPt.chiller_risk || 0)
                  : (nowPt.water_pump_risk || 0);
    const risk72 = assetType === 'transformer' ? (pt72.transformer_risk || 0)
                 : assetType === 'chiller' ? (pt72.chiller_risk || 0)
                 : (pt72.water_pump_risk || 0);

    const assetNameMap = { transformer: 'POWER TRANSFORMER', chiller: 'HVAC CHILLER', water_pump: 'WATER PUMP (DS)' };

    decisionContextAsset = {
        type: assetType,
        name: assetNameMap[assetType] || assetType.toUpperCase(),
        id: matchedDec.equipment_id,
        riskNow,
        risk72
    };

    // Update Risk Summary
    const setEl = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };
    setEl('dcRiskAssetName', `${decisionContextAsset.name} (${decisionContextAsset.id})`);
    setEl('dcRiskCurrentVal', `${riskNow.toFixed(1)} / 100`);
    setEl('dcRisk72hVal', `${risk72.toFixed(1)} / 100`);

    // Highlight selected card
    ['transformer', 'chiller', 'water_pump'].forEach(t => {
        const cardId = t === 'transformer' ? 'dcAssetCardTx' : t === 'chiller' ? 'dcAssetCardCh' : 'dcAssetCardWp';
        const card = document.getElementById(cardId);
        if (card) {
            card.style.borderColor = (t === assetType) ? 'var(--accent-cyan)' : 'var(--border-color)';
        }
    });

    // Update recommendation card for selected asset
    renderTopPriorityActionCard(matchedDec);
    clearMitigationProjection();
}

function clearMitigationProjection(message = 'Choose an asset and run the modelled projection.') {
    decisionMitigationRequestKey = null;
    isMitigationSimulated = false;
    updateDecisionActionButtons();

    const set = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
    ['dcMitigationBaselineRisk', 'dcMitigationStrategyName', 'dcMitigationStrategyDesc',
     'dcMitigationProjectedRisk', 'dcMitigationReductionPts', 'dcMitigationResponseTime',
     'dcMitigationObjScore', 'dcMitigationBeforeLabel', 'dcMitigationAfterLabel',
     'dcResCurrentRisk', 'dcResProjectedRisk', 'dcResChange', 'dcResAction'].forEach(id => set(id, '--'));
    const before = document.getElementById('dcMitigationBeforeBar');
    const after = document.getElementById('dcMitigationAfterBar');
    if (before) before.style.width = '0%';
    if (after) after.style.width = '0%';
    const state = document.getElementById('dcMitigationState');
    if (state) { state.textContent = message; state.style.color = 'var(--text-muted)'; }
    const button = document.getElementById('dcSimulateMitigationBtn');
    if (button) { button.disabled = false; button.textContent = 'SIMULATE MITIGATION'; }
    const status = document.getElementById('dcResStatus');
    if (status) { status.textContent = 'AWAITING SIMULATION'; status.style.background = '#64748B'; }
    // Reset projected-impact panel to empty state
    const emptyPanel = document.getElementById('dcProjectedImpactEmpty');
    const filledPanel = document.getElementById('dcProjectedImpactFilled');
    if (emptyPanel) emptyPanel.style.display = 'block';
    if (filledPanel) filledPanel.style.display = 'none';
}

async function simulateDecisionMitigation() {
    const asset = decisionContextAsset;
    const action = decisionActiveAction;
    const state = document.getElementById('dcMitigationState');
    const button = document.getElementById('dcSimulateMitigationBtn');
    if (!asset || !action) {
        clearMitigationProjection('NO PREVENTIVE ACTION AVAILABLE');
        return;
    }
    const requestKey = selectedDecisionSiteId + ':' + asset.type + ':' + asset.id;
    decisionMitigationRequestKey = requestKey;
    if (button) { button.disabled = true; button.textContent = 'SIMULATING...'; }
    if (state) { state.textContent = 'Running modelled mitigation projection...'; state.style.color = 'var(--accent-cyan)'; }
    try {
        const response = await fetch(API_BASE_URL + '/api/mitigation/projection', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ site_id: selectedDecisionSiteId, asset_type: asset.type, asset_id: asset.id, action: action.action })
        });
        const result = await response.json();
        if (!response.ok) {
            throw new Error(`Simulation request failed: HTTP ${response.status} | ${result.error || 'Server error'}`);
        }
        if (!result.success || !result.projection) {
            throw new Error(result.error || 'Mitigation projection unavailable.');
        }
        if (decisionMitigationRequestKey !== requestKey) return;
        isMitigationSimulated = true;
        updateDecisionActionButtons();
        renderMitigationProjection(result);
    } catch (error) {
        if (decisionMitigationRequestKey === requestKey) {
            isMitigationSimulated = false;
            updateDecisionActionButtons();
            
            const state = document.getElementById('dcMitigationState');
            if (state) {
                state.innerHTML = `
                    <div style="color: #EF4444; font-weight: 750;">
                        MITIGATION SIMULATION FAILED<br>
                        <small style="color: var(--text-muted); font-weight: 600;">Unable to calculate the projected impact.<br>Reason: ${error.message}</small>
                    </div>
                `;
            }
            if (button) {
                button.textContent = 'RETRY';
            }
        }
    } finally {
        if (decisionMitigationRequestKey === requestKey && !isMitigationSimulated && button && button.textContent !== 'RETRY') {
            button.disabled = false;
            button.textContent = 'SIMULATE MITIGATION';
        }
    }
}

function renderMitigationProjection(result) {
    const projection = result.projection;
    const recommendation = result.recommendation || {};
    const baseline = Number(projection.baseline_risk);
    const projected = Number(projection.projected_risk);
    const change = Number(projection.risk_change);
    if (![baseline, projected, change].every(Number.isFinite)) {
        clearMitigationProjection('MITIGATION PROJECTION UNAVAILABLE: Backend returned invalid model values.');
        return;
    }
    const set = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
    set('dcMitigationBaselineRisk', baseline.toFixed(1));
    set('dcMitigationStrategyName', recommendation.action || projection.strategy_name || '--');
    set('dcMitigationStrategyDesc', projection.strategy_description || recommendation.why || '--');
    set('dcMitigationProjectedRisk', projected.toFixed(1));
    const pctChange = baseline > 0 ? ((projected - baseline) / baseline * 100) : 0;
    const pointsText = `${change >= 0 ? '+' : ''}${change.toFixed(1)} pts`;
    const pctText = `(${pctChange >= 0 ? '+' : ''}${pctChange.toFixed(0)}%)`;
    set('dcMitigationReductionPts', `${pointsText} ${pctText}`);
    set('dcMitigationResponseTime', Number.isFinite(Number(projection.response_time_minutes)) ? projection.response_time_minutes + ' min' : '--');
    set('dcMitigationObjScore', Number.isFinite(Number(projection.objective_score)) ? projection.objective_score + '/100' : '--');
    set('dcMitigationBeforeLabel', baseline.toFixed(1) + ' / 100');
    set('dcMitigationAfterLabel', projected.toFixed(1) + ' / 100 (PROJECTED)');
    const before = document.getElementById('dcMitigationBeforeBar');
    const after = document.getElementById('dcMitigationAfterBar');
    if (before) before.style.width = Math.max(0, Math.min(100, baseline)) + '%';
    if (after) after.style.width = Math.max(0, Math.min(100, projected)) + '%';
    set('dcResCurrentRisk', baseline.toFixed(1) + ' / 100');
    set('dcResProjectedRisk', projected.toFixed(1) + ' / 100');
    set('dcResChange', `${pointsText} ${pctText}`);
    set('dcResAction', recommendation.action || projection.strategy_name || '--');
    const status = document.getElementById('dcResStatus');
    if (status) {
        status.textContent = projection.status || 'NO SIGNIFICANT PROJECTED CHANGE';
        status.style.background = change <= -10 ? '#10B981' : (change < 0 ? '#F59E0B' : '#64748B');
    }
    const state = document.getElementById('dcMitigationState');
    if (state) { state.textContent = 'Modelled projection complete - not a guaranteed outcome.'; state.style.color = '#10B981'; }
    // Show filled projected-impact panel
    const emptyPanel = document.getElementById('dcProjectedImpactEmpty');
    const filledPanel = document.getElementById('dcProjectedImpactFilled');
    if (emptyPanel) emptyPanel.style.display = 'none';
    if (filledPanel) filledPanel.style.display = 'block';
}

function getFeatureExplanation(feat, isIncrease) {
    const mappings = {
        "MPD_roll60m_mean": isIncrease ? "High power demand is stressing thermal thresholds." : "Power demand is within stable operational limits.",
        "KW_roll30m_mean": isIncrease ? "Active power load is elevated, driving component heating." : "Active power load is running nominal.",
        "THDVL1_roll60m_mean": isIncrease ? "Electrical voltage distortion is causing minor core losses." : "Voltage harmonic levels are clean and nominal.",
        "THDVL1_roll30m_mean": isIncrease ? "Electrical voltage distortion is causing minor core losses." : "Voltage harmonic levels are clean and nominal.",
        "OTI": isIncrease ? "Elevated oil temperatures exceed seasonal cooling benchmarks." : "Oil temperatures are within standard ranges.",
        "WTI": isIncrease ? "Winding temperatures are elevated under current load profiles." : "Winding temperatures are stable.",
        "ATI": isIncrease ? "Ambient summer heat is reducing cooling efficacy." : "Ambient environmental temperatures are nominal.",
        "OLI": isIncrease ? "Oil level indicators indicate slight variance from baseline." : "Oil level index is normal.",
        "VL1": isIncrease ? "Phase L1 voltage variance detected." : "Phase L1 voltage is stable.",
        "VL23": isIncrease ? "Phase L23 voltage variance detected." : "Phase L23 voltage is stable.",
        "VL31": isIncrease ? "Phase L31 voltage variance detected." : "Phase L31 voltage is stable.",
        "IL1": isIncrease ? "High line current is drawing maximum capacity." : "Line current load is nominal.",
        "KW": isIncrease ? "Active power demand is driving transformer load." : "Power demand load is stable.",
        "KVA": isIncrease ? "Apparent power load is elevated." : "Apparent power load is normal.",
        "Avg_PF": isIncrease ? "Lower power factor increases current draw." : "Power factor is highly optimized.",
        "FRQ": isIncrease ? "Grid frequency fluctuations detected." : "Grid frequency is highly stable."
    };
    return mappings[feat] || (isIncrease ? "Operational variance is influencing equipment stress." : "Operating parameter is stable.");
}

async function loadDecisionCenterData() {
    const requestId = ++decisionLoadRequestId;
    try {
        clearMitigationProjection();
        // Sync dropdown
        const selElem = document.getElementById('decisionFacilitySelector');
        if (selElem && selElem.value !== selectedDecisionSiteId) {
            selElem.value = selectedDecisionSiteId;
        }

        //  FETCH 1: Decisions API 
        const [decRes, predRes] = await Promise.all([
            fetch(`${API_BASE_URL}/api/facilities/${selectedDecisionSiteId}/decisions`),
            fetch(`${API_BASE_URL}/api/facilities/${selectedDecisionSiteId}/prediction`)
        ]);

        const decData = await decRes.json();
        const predData = await predRes.json();
        if (requestId !== decisionLoadRequestId) return;

        if (!decData.success || !decData.facility_decisions) {
            console.error('Decision API failed:', decData);
            return;
        }
        if (!predData.success || !predData.prediction) {
            console.error('Prediction API failed:', predData);
            return;
        }

        const fd = decData.facility_decisions;
        const pred = predData.prediction;

        // Cache for asset switching
        decisionCachedDecisions = fd;
        decisionCachedPrediction = pred;

        const m = pred.milestones;
        const nowPt = m.NOW || {};
        const pt72 = m['72h'] || {};
        const eq = pred.equipment || {};

        //  SECTION 1: RISK SUMMARY 
        const setEl = (id, val) => { const e = document.getElementById(id); if (e) e.textContent = val; };

        setEl('dcRiskFacilityName', `${fd.site_name || pred.site_name} (${selectedDecisionSiteId})`);

        // Determine active/highest-risk asset
        const assets = [
            { type: 'transformer', name: 'POWER TRANSFORMER', id: (eq.transformer || {}).equipment_id || 'TX-001',
              riskNow: nowPt.transformer_risk || 0, risk72: pt72.transformer_risk || 0 },
            { type: 'chiller', name: 'HVAC CHILLER', id: (eq.chiller || {}).equipment_id || 'CH-001',
              riskNow: nowPt.chiller_risk || 0, risk72: pt72.chiller_risk || 0 },
            { type: 'water_pump', name: 'WATER PUMP (DS)', id: (eq.water_pump || {}).equipment_id || 'WP-001',
              riskNow: nowPt.water_pump_risk || 0, risk72: pt72.water_pump_risk || 0 }
        ];

        // If context was passed (from Predictive Risk), use it; otherwise pick highest 72H
        let activeAsset = decisionContextAsset
            ? assets.find(a => a.type === decisionContextAsset.type) || assets.reduce((p, c) => p.risk72 > c.risk72 ? p : c)
            : assets.reduce((p, c) => p.risk72 > c.risk72 ? p : c);

        decisionContextAsset = activeAsset;

        setEl('dcRiskAssetName', `${activeAsset.name} (${activeAsset.id})`);
        setEl('dcRiskCurrentVal', `${activeAsset.riskNow.toFixed(1)} / 100`);
        setEl('dcRisk72hVal', `${activeAsset.risk72.toFixed(1)} / 100`);

        const tr = (pred.trend_analysis || {}).trend || 'STABLE';
        const trendEl = document.getElementById('dcRiskTrend');
        if (trendEl) {
            trendEl.textContent = tr === 'RISING' ? '↑ Increasing' : (tr === 'FALLING' ? '↓ Decreasing' : '→ Stable');
            trendEl.style.color = tr === 'RISING' ? '#EF4444' : (tr === 'FALLING' ? '#10B981' : '#F59E0B');
        }

        const natEv = pred.natural_events || {};
        const hw = natEv.heatwave || {};
        const rain = natEv.heavy_rainfall || {};
        const wind = natEv.high_wind || {};
        let eventLabel = 'No active event detected';
        if (pred.controlled_scenario) eventLabel = 'CONTROLLED SCENARIO';
        else if (hw.detected) eventLabel = `HEATWAVE — ${hw.severity || 'WATCH'}`;
        else if (rain.detected) eventLabel = 'HEAVY RAINFALL ALERT';
        else if (wind.detected) eventLabel = 'HIGH WIND ALERT';
        setEl('dcClimateEvent', eventLabel);
        setEl('dcClimateStress', nowPt.climate_stress !== undefined ? nowPt.climate_stress.toFixed(1) : '--');

        //  SECTION 2: ASSET CARDS 
        const priorityColor = p => {
            if (p === 'CRITICAL') return '#EF4444';
            if (p === 'HIGH' || p === 'URGENT') return '#F97316';
            if (p === 'MODERATE') return '#F59E0B';
            return '#64748B';
        };

        const decByType = {};
        (fd.decisions || []).forEach(d => { decByType[d.equipment_type.toLowerCase()] = d; });

        const fillCard = (idSuffix, assetTypeKey, asset) => {
            const dec = decByType[assetTypeKey] || {};
            setEl(`dcAsset${idSuffix}Id`, asset.id);
            setEl(`dcAsset${idSuffix}RiskNow`, `${asset.riskNow.toFixed(1)} / 100`);
            setEl(`dcAsset${idSuffix}Risk72`, `${asset.risk72.toFixed(1)} / 100`);
            const badge = document.getElementById(`dcAsset${idSuffix}PriorityBadge`);
            if (badge) {
                const p = dec.priority || dec.action_priority_level || '--';
                badge.textContent = p;
                badge.style.background = priorityColor(p);
            }
        };

        fillCard('Tx', 'transformer', assets[0]);
        fillCard('Ch', 'chiller', assets[1]);
        fillCard('Wp', 'water_pump', assets[2]);

        // Highlight active asset card
        ['transformer', 'chiller', 'water_pump'].forEach(t => {
            const cardId = t === 'transformer' ? 'dcAssetCardTx' : (t === 'chiller' ? 'dcAssetCardCh' : 'dcAssetCardWp');
            const card = document.getElementById(cardId);
            if (card) {
                if (t === activeAsset.type) {
                    card.style.borderColor = '#06B6D4';
                    card.style.background = 'rgba(6, 182, 212, 0.06)';
                    card.style.boxShadow = '0 0 8px rgba(6, 182, 212, 0.15)';
                    let ind = card.querySelector('.selected-indicator');
                    if (!ind) {
                        ind = document.createElement('span');
                        ind.className = 'selected-indicator';
                        ind.style.cssText = 'position: absolute; right: 8px; bottom: 8px; font-size: 9px; font-weight: 800; color: #06B6D4; letter-spacing: 0.5px;';
                        ind.textContent = 'SELECTED';
                        card.appendChild(ind);
                    } else {
                        ind.style.display = 'block';
                    }
                } else {
                    card.style.borderColor = 'var(--border-subtle)';
                    card.style.background = 'var(--bg-surface)';
                    card.style.boxShadow = 'none';
                    const ind = card.querySelector('.selected-indicator');
                    if (ind) ind.style.display = 'none';
                }
            }
        });

        //  SECTION 3: SHAP XAI WHY 
        const shapData = pred.shap_explanation || {};
        setEl('dcShapSummaryText', shapData.summary || 'XAI evaluation complete.');
        const shapListEl = document.getElementById('dcShapFactorsList');
        const techListEl = document.getElementById('dcShapTechnicalDetails');
        
        if (shapListEl && shapData.factors && shapData.factors.length > 0) {
            const maxShap = Math.max(...shapData.factors.map(x => Math.abs(x.shap_value || 0)), 1);
            
            // Show only top 3 simplified risk drivers
            const topFactors = shapData.factors.slice(0, 3);
            shapListEl.innerHTML = topFactors.map(f => {
                const isPos = f.impact_direction === 'INCREASES_RISK';
                const icon = isPos ? '↑' : '↓';
                const color = isPos ? '#EF4444' : '#10B981';
                let displayName = f.feature_description && f.feature_description !== 'undefined' ? f.feature_description : getHumanReadableFeatureName(f.feature || '');
                if (!displayName || displayName === 'undefined') displayName = "Operational Parameter";
                const explanation = getFeatureExplanation(f.feature || '', isPos);
                return `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; padding: 12px 16px; background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: 4px;">
                        <div>
                            <strong style="font-size: 14px; color: var(--text-primary); display: block;">${displayName}</strong>
                            <small style="font-size: 12px; color: var(--text-muted); display: block; margin-top: 4px;">${explanation}</small>
                        </div>
                        <span style="font-size: 13px; font-weight: 700; color: ${color}; white-space: nowrap; margin-left: 12px;">${icon} ${Math.abs(f.shap_value).toFixed(2)} risk impact</span>
                    </div>
                `;
            }).join('');

            // Full list of technical factors inside expandable explanation
            if (techListEl) {
                techListEl.innerHTML = shapData.factors.map(f => {
                    const isPos = f.impact_direction === 'INCREASES_RISK';
                    const icon = isPos ? '↑' : '↓';
                    const color = isPos ? '#EF4444' : '#10B981';
                    const shapVal = f.shap_value >= 0 ? `+${f.shap_value.toFixed(2)}` : `${f.shap_value.toFixed(2)}`;
                    const barWidth = Math.min(100, Math.max(10, Math.round((Math.abs(f.shap_value) / maxShap) * 100)));
                    return `
                        <div style="margin-bottom: 8px; width: 100%;">
                            <div style="display:flex; justify-content:space-between; font-size:11.5px; margin-bottom:2px;">
                                <span style="color:var(--text-secondary); font-family: monospace;">${f.feature || ''} (${f.feature_value !== undefined ? f.feature_value : '--'})</span>
                                <strong style="color:${color}; font-weight:700;">${icon} ${shapVal} SHAP</strong>
                            </div>
                            <div style="background:var(--bg-app); height:4px; border-radius:2px; overflow:hidden; border:1px solid var(--border-subtle);">
                                <div style="background:${color}; width:${barWidth}%; height:100%;"></div>
                            </div>
                        </div>
                    `;
                }).join('');
            }
        } else {
            if (shapListEl) shapListEl.innerHTML = `<p style="color:var(--text-muted); font-size:12px;">Explanation unavailable for this asset.</p>`;
            if (techListEl) techListEl.innerHTML = `<p style="color:var(--text-muted); font-size:12px;">No technical factors available.</p>`;
        }

        //  CLIMATE CONTEXT 
        const allStressValues = (pred.hourly_forecast || []).map(h => h.climate_stress || 0);
        const peakStress = allStressValues.length ? Math.max(...allStressValues).toFixed(1) : '--';
        setEl('dcCtxEvent', eventLabel);
        setEl('dcCtxTemp', nowPt.temperature !== undefined ? `${nowPt.temperature.toFixed(1)} °C` : '--');
        setEl('dcCtxHumidity', nowPt.humidity !== undefined ? `${nowPt.humidity.toFixed(1)} %` : '--');
        setEl('dcCtxStress', nowPt.climate_stress !== undefined ? nowPt.climate_stress.toFixed(1) : '--');
        setEl('dcCtxPeakStress', peakStress);
        setEl('dcCtxCascade', (fd.cascading_risk || {}).cascading_risk_detected ? 'CASCADE RISK DETECTED' : 'No cascade detected');

        //  SECTION 4: RECOMMENDED ACTION 
        const topAction = (fd.decisions || []).find(d =>
            d.equipment_type && d.equipment_type.toLowerCase() === activeAsset.type
        ) || fd.top_action;

        rawDecisionActionsCache = fd.decisions || [];
        renderTopPriorityActionCard(topAction);
        renderCascadingRiskAlert(fd.cascading_risk);
        renderResponseTimeline((fd.response_plan || {}).timelines);
        // Modelled mitigation is user-triggered, scoped to the selected asset.
        return;

        //  SECTION 5: PROJECTED MITIGATION (Optimization API) 
        try {
            const optPayload = {
                site_id: selectedDecisionSiteId,
                scenario: {
                    temperature: nowPt.temperature || 28.5,
                    humidity: nowPt.humidity || 65,
                    rain: nowPt.rain || 0,
                    wind_speed: nowPt.wind_speed || 12
                }
            };
            const optRes = await fetch(`${API_BASE_URL}/api/optimization/optimize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(optPayload)
            });
            const optData = await optRes.json();
            if (optData.success && optData.optimization) {
                const opt = optData.optimization;
                const rec = opt.recommended_plan || {};
                const baselineRisk = parseFloat(opt.baseline_risk || 0);
                const projectedRisk = parseFloat(rec.simulated_system_risk || baselineRisk);
                const reductionPts = parseFloat(opt.baseline_risk - projectedRisk || rec.risk_reduction_pts || 0);

                setEl('dcMitigationBaselineRisk', baselineRisk.toFixed(1));
                setEl('dcMitigationStrategyName', rec.strategy_name || rec.strategy_id || 'Optimized Strategy');
                const stratDesc = rec.description || 'Prescriptive intervention plan.';
                setEl('dcMitigationStrategyDesc', stratDesc.length > 80 ? stratDesc.substring(0, 80) + '…' : stratDesc);
                setEl('dcMitigationProjectedRisk', projectedRisk.toFixed(1));
                setEl('dcMitigationReductionPts', `${reductionPts >= 0 ? '-' : '+'}${Math.abs(reductionPts).toFixed(1)} pts`);
                setEl('dcMitigationResponseTime', rec.response_time_minutes !== undefined ? rec.response_time_minutes : '--');
                setEl('dcMitigationObjScore', rec.objective_score !== undefined ? `${rec.objective_score}/100` : '--');

                // Before/after bars
                const beforeBar = document.getElementById('dcMitigationBeforeBar');
                const afterBar = document.getElementById('dcMitigationAfterBar');
                const beforeLabel = document.getElementById('dcMitigationBeforeLabel');
                const afterLabel = document.getElementById('dcMitigationAfterLabel');
                if (beforeBar) { setTimeout(() => { beforeBar.style.width = `${Math.min(baselineRisk, 100)}%`; }, 100); }
                if (afterBar) { setTimeout(() => { afterBar.style.width = `${Math.min(projectedRisk, 100)}%`; }, 200); }
                if (beforeLabel) beforeLabel.textContent = `${baselineRisk.toFixed(1)} / 100`;
                if (afterLabel) afterLabel.textContent = `${projectedRisk.toFixed(1)} / 100 (PROJECTED)`;

                //  SECTION 6: RESILIENCE OUTLOOK 
                setEl('dcResCurrentRisk', `${baselineRisk.toFixed(1)} / 100`);
                setEl('dcResProjectedRisk', `${projectedRisk.toFixed(1)} / 100`);
                const changeText = reductionPts > 0 ? `- ${reductionPts.toFixed(1)} pts (Improvement)` : reductionPts < 0 ? `+ ${Math.abs(reductionPts).toFixed(1)} pts (Increase)` : 'No change projected';
                setEl('dcResChange', changeText);
                setEl('dcResAction', rec.strategy_name || (topAction || {}).action || '--');

                const resStatusEl = document.getElementById('dcResStatus');
                if (resStatusEl) {
                    if (reductionPts >= 10) {
                        resStatusEl.textContent = 'EFFECTIVE MITIGATION AVAILABLE';
                        resStatusEl.style.background = '#10B981';
                    } else if (reductionPts > 0) {
                        resStatusEl.textContent = 'PARTIAL MITIGATION PROJECTED';
                        resStatusEl.style.background = '#F59E0B';
                    } else if ((fd.facility_priority_level || '').toUpperCase() === 'LOW') {
                        resStatusEl.textContent = 'LOW RISK — MONITORING RECOMMENDED';
                        resStatusEl.style.background = '#3B82F6';
                    } else {
                        resStatusEl.textContent = 'PREVENTIVE ACTION RECOMMENDED';
                        resStatusEl.style.background = '#EF4444';
                    }
                }
            }
        } catch (optErr) {
            console.warn('Optimization API unavailable:', optErr);
            setEl('dcMitigationStrategyName', 'Mitigation projection unavailable.');
            setEl('dcMitigationStrategyDesc', '');
        }

    } catch (err) {
        console.error('Error loading decision center data:', err);
    }
}

function renderTopPriorityActionCard(topAction) {
    if (!topAction) return;

    decisionActiveAction = topAction;
    currentTopActionId = topAction.action_id;
    document.getElementById("tpSiteBadge").textContent = topAction.site_id || "SITE-001";
    document.getElementById("tpTitle").textContent = `${topAction.site_name || "Facility"} — ${topAction.equipment_type || "Asset"}`;
    document.getElementById("tpEqId").textContent = `Equipment: ${topAction.equipment_id || "TX-001"} | Responsible Team: ${topAction.responsible_team || "Engineering Operations"}`;

    document.getElementById("tpPriorityScore").textContent = `${topAction.action_priority_score || topAction.risk_score || 0} / 100`;
    document.getElementById("tpPriorityLevel").innerHTML = getRiskBadgeHTML(topAction.action_priority_level || topAction.priority);

    document.getElementById("tpActionText").textContent = topAction.action || "Routine preventive inspection.";
    document.getElementById("tpWhyText").textContent = topAction.why || "Operational baseline check.";
    document.getElementById("tpTimeframeText").textContent = topAction.when_timeframe || topAction.timeframe || "Within 6 Hours";
    document.getElementById("tpBenefitText").textContent = topAction.expected_benefit || "Risk mitigation.";

    document.getElementById("tpConfidenceBadge").textContent = `DECISION CONFIDENCE: ${topAction.decision_confidence_pct || 89}% (${topAction.confidence_level || 'HIGH'})`;
    document.getElementById("tpModeBadge").textContent = topAction.decision_mode || "AI-ASSISTED DECISION ENGINE";

    // Update Action Buttons State if Acknowledged/In Progress
    updateDecisionActionButtons();
}

function renderCascadingRiskAlert(cascadingInfo) {
    const container = document.getElementById("cascadingRiskAlertContainer");
    if (!container) return;

    if (!cascadingInfo || !cascadingInfo.cascading_risk_detected) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = `
        <div style="background: rgba(239, 68, 68, 0.1); border-left: 5px solid #EF4444; border-top: 1px solid var(--border-color); border-right: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color); padding: 16px; border-radius: 6px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                <strong style="color:#EF4444; font-size:14px; text-transform:uppercase;">CASCADING CLIMATE RISK DETECTED</strong>
                <span class="prov-badge live-weather" style="background:#EF4444;">HIGH INTERDEPENDENCY</span>
            </div>
            <p style="font-size:13px; color:var(--text-primary); margin-bottom:6px;">${cascadingInfo.chain_description}</p>
            <small style="color:var(--text-muted); font-size:11px;">Primary Vulnerability Node: <strong>${cascadingInfo.primary_vulnerability}</strong>. Simultaneous mitigation required across chiller and transformer assets.</small>
        </div>
    `;
}

function renderResponseTimeline(timelines) {
    if (!timelines) return;

    const renderList = (items) => {
        if (!items || items.length === 0) return `<p style="color:var(--text-muted); font-size:11px;">No pending actions</p>`;
        return items.map(it => `
            <div style="margin-bottom:6px; background:var(--bg-primary); padding:6px 8px; border-radius:4px; border:1px solid var(--border-color);">
                <strong style="font-size:11.5px; color:var(--text-primary);">${it.equipment_id || ''}: ${it.action}</strong>
            </div>
        `).join("");
    };

    document.getElementById("tpTimelineNow").innerHTML = renderList(timelines.now);
    document.getElementById("tpTimeline2h").innerHTML = renderList(timelines.next_2_hours);
    document.getElementById("tpTimeline6h").innerHTML = renderList(timelines.next_6_hours);
    document.getElementById("tpTimeline24h").innerHTML = renderList(timelines.next_24_hours);
    document.getElementById("tpTimeline3d").innerHTML = renderList(timelines.next_3_days);
}

function filterActionTable() {
    const prioFilter = document.getElementById("actionFilterPriority").value.toUpperCase();
    const eqFilter = document.getElementById("actionFilterEquipment").value.toUpperCase();
    const statusFilter = document.getElementById("actionFilterStatus").value.toUpperCase();

    let filtered = rawDecisionActionsCache.filter(a => {
        if (prioFilter !== "ALL" && (a.action_priority_level || a.priority || "").toUpperCase() !== prioFilter) return false;
        if (eqFilter !== "ALL" && !(a.equipment_type || "").toUpperCase().includes(eqFilter)) return false;
        if (statusFilter !== "ALL" && (a.status || "PENDING").toUpperCase() !== statusFilter) return false;
        return true;
    });

    renderActionTable(filtered);
}

function renderActionTable(actions) {
    const tbody = document.getElementById("dcActionTableBody");
    if (!tbody) return;

    if (!actions || actions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:var(--text-muted);">No operational actions match selected filters.</td></tr>`;
        return;
    }

    tbody.innerHTML = actions.map((a, idx) => {
        const isMgmt = decisionViewMode === "MANAGEMENT";
        const st = (a.status || "PENDING").toUpperCase();
        let stBadge = `<span class="ma-status-badge badge-warning" style="background:#64748B;">PENDING</span>`;
        if (st === "ACKNOWLEDGED") stBadge = `<span class="ma-status-badge badge-low" style="background:#10B981;">ACKNOWLEDGED</span>`;
        else if (st === "IN_PROGRESS") stBadge = `<span class="ma-status-badge badge-warning" style="background:#06B6D4;">IN PROGRESS</span>`;
        else if (st === "COMPLETED") stBadge = `<span class="ma-status-badge badge-low" style="background:#10B981;">COMPLETED</span>`;

        return `
            <tr>
                <td style="font-weight:700; color:var(--accent-cyan);">#${idx + 1}</td>
                <td><strong>${a.site_name || a.site_id}</strong></td>
                <td>${a.equipment_id} <small style="color:var(--text-muted);">(${a.equipment_type})</small></td>
                <td>${a.risk_score} / 100</td>
                <td><small style="font-weight:700;">${a.impact_level || 'MODERATE'}</small></td>
                <td><small style="font-weight:700; color:var(--status-danger);">${a.urgency_level || 'HIGH'}</small></td>
                <td style="font-weight:800; font-size:14px;">${a.action_priority_score || a.risk_score} ${getRiskBadgeHTML(a.action_priority_level || a.priority)}</td>
                <td>
                    <strong style="color:var(--text-primary); font-size:12.5px;">${a.action}</strong>
                    ${isMgmt ? `<p style="font-size:11px; color:var(--text-secondary); margin-top:2px;">Timeframe: ${a.when_timeframe || 'Within 6h'} | Expected Benefit: ${a.expected_benefit || 'Risk Reduction'}</p>` : `<p style="font-size:11px; color:var(--text-muted); margin-top:2px;">Why: ${a.why || ''}</p>`}
                </td>
                <td>${stBadge}</td>
                <td>
                    ${st === "PENDING" ? `<button type="button" class="btn-primary" style="padding:4px 8px; font-size:10px;" onclick="updateActionStatus('${a.action_id}', 'ACKNOWLEDGED')">ACKNOWLEDGE</button>` : ''}
                    ${st === "ACKNOWLEDGED" ? `<button type="button" class="btn-success" style="padding:4px 8px; font-size:10px;" onclick="updateActionStatus('${a.action_id}', 'IN_PROGRESS')">START</button>` : ''}
                    ${st === "IN_PROGRESS" ? `<button type="button" class="btn-success" style="padding:4px 8px; font-size:10px;" onclick="updateActionStatus('${a.action_id}', 'COMPLETED')">COMPLETE</button>` : ''}
                    ${st === "COMPLETED" ? `<span style="font-size:11px; color:#10B981; font-weight:700;">DONE</span>` : ''}
                </td>
            </tr>
        `;
    }).join("");
}

async function updateActionStatus(actionId, status) {
    try {
        const res = await fetch(`${API_BASE_URL}/api/actions/${actionId}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: status })
        });
        const data = await res.json();
        if (data.success) {
            loadDecisionCenterData();
        }
    } catch (err) {
        console.error("Error updating action status:", err);
    }
}

function handleTopActionAcknowledge() {
    if (currentTopActionId) updateActionStatus(currentTopActionId, "ACKNOWLEDGED");
}

function handleTopActionStart() {
    if (currentTopActionId) updateActionStatus(currentTopActionId, "IN_PROGRESS");
}

function handleTopActionDismiss() {
    if (currentTopActionId) updateActionStatus(currentTopActionId, "DISMISSED");
}

/* ============================================================
   PHASE 19: RESILIENCE ORCHESTRATION, INCIDENT MANAGEMENT & ALERTING
   ============================================================ */

let selectedIncidentSiteId = "ALL";
let rawIncidentsCache = [];
let currentSelectedIncidentId = null;

function handleIncidentFacilitySelection(siteId) {
    selectedIncidentSiteId = siteId;
    loadIncidentCenterData();
}

async function loadIncidentCenterData() {
    try {
        // Load Incident Summary KPIs
        const sumRes = await fetch(`${API_BASE_URL}/api/incident-summary`);
        const sumData = await sumRes.json();
        if (sumData.success && sumData.summary) {
            const s = sumData.summary;
            document.getElementById("incKpiActive").textContent = s.active_incidents || 0;
            document.getElementById("incKpiCritical").textContent = s.critical_incidents || 0;
            document.getElementById("incKpiUrgent").textContent = s.urgent_incidents || 0;
            document.getElementById("incKpiAvgResp").textContent = `${s.average_response_minutes || 0.0}m`;
            document.getElementById("incKpiAvgMit").textContent = `${s.average_mitigation_minutes || 0.0}m`;
        }

        // Load Incidents List
        const incRes = await fetch(`${API_BASE_URL}/api/incidents?site_id=${selectedIncidentSiteId}`);
        const incData = await incRes.json();
        if (incData.success && incData.incidents) {
            rawIncidentsCache = incData.incidents;
            filterIncidentTable();

            if (rawIncidentsCache.length > 0 && !currentSelectedIncidentId) {
                selectIncidentDetail(rawIncidentsCache[0].incident_id);
            }
        }

        // Refresh Header Notifications
        loadHeaderNotifications();

    } catch (err) {
        console.error("Error loading Incident Center data:", err);
    }
}

function filterIncidentTable() {
    const sevFilter = document.getElementById("incFilterSeverity").value.toUpperCase();
    const stFilter = document.getElementById("incFilterStatus").value.toUpperCase();

    let filtered = rawIncidentsCache.filter(inc => {
        if (sevFilter !== "ALL" && (inc.severity || "").toUpperCase() !== sevFilter) return false;
        if (stFilter !== "ALL" && (inc.status || "").toUpperCase() !== stFilter) return false;
        return true;
    });

    renderIncidentTable(filtered);
}

function renderIncidentTable(incidents) {
    const tbody = document.getElementById("incP19TableBody");
    if (!tbody) return;

    if (!incidents || incidents.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; color:var(--text-muted);">No active infrastructure incidents match selected filters.</td></tr>`;
        return;
    }

    tbody.innerHTML = incidents.map(inc => {
        const st = (inc.status || "OPEN").toUpperCase();
        const sev = (inc.severity || "MODERATE").toUpperCase();

        let stBadge = `<span class="ma-status-badge badge-warning" style="background:#64748B;">${st}</span>`;
        if (st === "ACKNOWLEDGED") stBadge = `<span class="ma-status-badge badge-low" style="background:#10B981;">ACKNOWLEDGED</span>`;
        else if (st === "IN_PROGRESS") stBadge = `<span class="ma-status-badge badge-warning" style="background:#06B6D4;">IN PROGRESS</span>`;
        else if (st === "MITIGATED") stBadge = `<span class="ma-status-badge badge-low" style="background:#10B981;">MITIGATED</span>`;
        else if (st === "RESOLVED" || st === "CLOSED") stBadge = `<span class="ma-status-badge badge-low" style="background:#3B82F6;">${st}</span>`;

        return `
            <tr style="cursor:pointer; ${inc.incident_id === currentSelectedIncidentId ? 'background:rgba(6,182,212,0.1);' : ''}" onclick="selectIncidentDetail('${inc.incident_id}')">
                <td>${getRiskBadgeHTML(sev)}</td>
                <td><strong style="color:var(--accent-cyan); font-size:12px;">${inc.incident_id}</strong></td>
                <td><strong>${inc.site_name || inc.site_id}</strong></td>
                <td>${inc.equipment_id} <small style="color:var(--text-muted);">(${inc.equipment_type})</small></td>
                <td style="font-weight:700; color:var(--status-danger);">${inc.risk_score} / 100</td>
                <td style="font-weight:800; font-size:13px;">${inc.priority_score} / 100</td>
                <td><small style="color:var(--text-secondary);">${inc.assigned_team || 'Operations'}</small></td>
                <td>${stBadge}</td>
                <td><small style="color:var(--text-muted);">${inc.created_at || ''}</small></td>
                <td onclick="event.stopPropagation()">
                    ${st === "OPEN" ? `<button type="button" class="btn-primary" style="padding:4px 8px; font-size:10px;" onclick="handleIncidentAction('${inc.incident_id}', 'ACKNOWLEDGE')">ACKNOWLEDGE</button>` : ''}
                    ${st === "ACKNOWLEDGED" ? `<button type="button" class="btn-success" style="padding:4px 8px; font-size:10px;" onclick="handleIncidentAction('${inc.incident_id}', 'START')">START ACTION</button>` : ''}
                    ${st === "IN_PROGRESS" ? `<button type="button" class="btn-success" style="padding:4px 8px; font-size:10px;" onclick="handleIncidentAction('${inc.incident_id}', 'COMPLETE')">COMPLETE ACTION</button>` : ''}
                    ${st === "MITIGATED" ? `<button type="button" class="btn-primary" style="padding:4px 8px; font-size:10px; background:#3B82F6;" onclick="handleIncidentAction('${inc.incident_id}', 'RESOLVE')">MARK RESOLVED</button>` : ''}
                    ${st === "RESOLVED" ? `<button type="button" class="btn-secondary" style="padding:4px 8px; font-size:10px;" onclick="handleIncidentAction('${inc.incident_id}', 'CLOSE')">CLOSE</button>` : ''}
                </td>
            </tr>
        `;
    }).join("");
}

async function selectIncidentDetail(incident_id) {
    currentSelectedIncidentId = incident_id;
    try {
        const res = await fetch(`${API_BASE_URL}/api/incidents/${incident_id}`);
        const data = await res.json();
        if (data.success && data.incident) {
            renderIncidentDetail(data.incident);
        }
    } catch (err) {
        console.error("Error fetching incident details:", err);
    }
}

function renderIncidentDetail(inc) {
    const container = document.getElementById("incDetailContainer");
    if (!container) return;

    container.style.display = "block";

    document.getElementById("dtlSevBadge").innerHTML = getRiskBadgeHTML(inc.severity);
    document.getElementById("dtlTitle").textContent = inc.title || `Incident ${inc.incident_id}`;
    document.getElementById("dtlMeta").textContent = `ID: ${inc.incident_id} | Facility: ${inc.site_name} (${inc.site_id}) | Equipment: ${inc.equipment_id} (${inc.equipment_type})`;

    document.getElementById("dtlPreRisk").textContent = `${inc.pre_action_risk_score || inc.risk_score} / 100`;
    document.getElementById("dtlPostRisk").textContent = inc.post_action_risk_score ? `Post-Action Risk: ${inc.post_action_risk_score} / 100` : "Post-Action Risk: Pending Completion";

    document.getElementById("dtlActionText").textContent = inc.recommended_action || "Perform routine technical inspection.";
    document.getElementById("dtlWhyText").textContent = inc.reason || "Operational risk mitigation.";

    document.getElementById("dtlTeamText").textContent = inc.assigned_team || "Operations Team";
    document.getElementById("dtlDriverText").textContent = inc.climate_driver || "HEAT";

    // Render Response Effectiveness Card if evaluated
    const effCard = document.getElementById("dtlEffectivenessCard");
    const eff = inc.response_effectiveness;
    if (eff && eff.effectiveness_level) {
        effCard.style.display = "block";
        document.getElementById("effPreScore").textContent = `${eff.pre_action_risk_score} / 100`;
        document.getElementById("effPostScore").textContent = `${eff.post_action_risk_score} / 100`;
        document.getElementById("effDeltaScore").textContent = `${eff.observed_risk_reduction_pts} pts`;
        document.getElementById("dtlEffBadge").textContent = eff.effectiveness_level;
        document.getElementById("dtlEffDesc").textContent = eff.description || "Observed risk reduction following preventive intervention.";
    } else {
        effCard.style.display = "none";
    }

    // Render Timeline Events
    renderIncidentAuditTimeline(inc.timeline || []);
}

function renderIncidentAuditTimeline(timeline) {
    const container = document.getElementById("dtlTimelineNodes");
    if (!container) return;

    if (!timeline || timeline.length === 0) {
        container.innerHTML = `<p style="color:var(--text-muted); font-size:11px;">No audit events recorded.</p>`;
        return;
    }

    container.innerHTML = timeline.map(evt => `
        <div style="margin-bottom:8px; border-left:3px solid var(--accent-cyan); padding-left:10px; font-size:11.5px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="color:var(--accent-cyan);">${evt.event_type}</strong>
                <small style="color:var(--text-muted);">${evt.timestamp}</small>
            </div>
            <p style="color:var(--text-primary); margin:2px 0 0;">${evt.description}</p>
            <small style="color:var(--text-muted);">Actor: ${evt.actor}</small>
        </div>
    `).join("");
}

async function handleIncidentAction(incident_id, actionType) {
    try {
        let endpoint = "";
        let body = null;

        if (actionType === "ACKNOWLEDGE") endpoint = `${API_BASE_URL}/api/incidents/${incident_id}/acknowledge`;
        else if (actionType === "START") endpoint = `${API_BASE_URL}/api/incidents/${incident_id}/start`;
        else if (actionType === "COMPLETE") {
            endpoint = `${API_BASE_URL}/api/incidents/${incident_id}/complete`;
            body = JSON.stringify({ notes: "Operator completed preventive equipment inspection." });
        }
        else if (actionType === "RESOLVE") endpoint = `${API_BASE_URL}/api/incidents/${incident_id}/resolve`;
        else if (actionType === "CLOSE") endpoint = `${API_BASE_URL}/api/incidents/${incident_id}/close`;

        const opts = { method: "POST", headers: { "Content-Type": "application/json" } };
        if (body) opts.body = body;

        const res = await fetch(endpoint, opts);
        const data = await res.json();
        if (data.success) {
            loadIncidentCenterData();
        }
    } catch (err) {
        console.error(`Error performing action ${actionType} on ${incident_id}:`, err);
    }
}

async function triggerMultiFacilityEvaluation() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/incidents/evaluate`, { method: "POST" });
        const data = await res.json();
        if (data.success) {
            loadIncidentCenterData();
        }
    } catch (err) {
        console.error("Error triggering multi-site evaluation:", err);
    }
}

async function loadHeaderNotifications() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/notifications`);
        const data = await res.json();
        if (!data.success) return;

        const badge = document.getElementById("hdrUnreadCountBadge");
        if (badge) badge.textContent = data.unread_count || 0;

        const list = document.getElementById("hdrNotificationList");
        if (!list) return;

        const notifs = data.notifications || [];
        if (notifs.length === 0) {
            list.innerHTML = `<p style="font-size:11px; color:var(--text-muted); text-align:center;">No notifications.</p>`;
            return;
        }

        list.innerHTML = notifs.map(n => `
            <div style="padding:6px 0; border-bottom:1px solid var(--border-color); font-size:11px; cursor:pointer;" onclick="selectIncidentDetail('${n.incident_id}'); toggleHeaderNotificationDropdown(); showView('incidents-p19', document.querySelector('.nav-item[onclick*=\\'incidents\\']'));">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="color:${n.severity === 'CRITICAL' ? '#EF4444' : 'var(--text-primary)'};">${n.title}</strong>
                    <small style="color:var(--text-muted);">${n.created_at.split(' ')[1]}</small>
                </div>
                <p style="color:var(--text-secondary); margin:2px 0 0; font-size:10.5px;">${n.message.split('\n')[0]}</p>
            </div>
        `).join("");

    } catch (err) {
        console.error("Error loading header notifications:", err);
    }
}

function toggleHeaderNotificationDropdown() {
    const dd = document.getElementById("hdrNotificationDropdown");
    if (dd) {
        dd.style.display = (dd.style.display === "none" || !dd.style.display) ? "block" : "none";
    }
}

async function markAllNotificationsRead() {
    try {
        const notifs = await (await fetch(`${API_BASE_URL}/api/notifications?unread_only=true`)).json();
        if (notifs.notifications) {
            for (const n of notifs.notifications) {
                await fetch(`${API_BASE_URL}/api/notifications/${n.notification_id}/read`, { method: "PATCH" });
            }
            loadHeaderNotifications();
        }
    } catch (err) {
        console.error("Error marking notifications read:", err);
    }
}

/* ============================================================
   PHASE 20: CONTINUOUS LEARNING, ADAPTIVE AI & PREDICTIVE MAINTENANCE
   ============================================================ */

async function loadLearningCenterData() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/learning/summary`);
        const data = await res.json();
        if (!data.success) return;

        // 1. Data Health & Eligibility Banner
        renderDataHealthAndEligibility(data.data_health, data.ml_eligibility);

        // 2. Active Registry Model & Performance Metrics
        renderActiveModelStatus(data.active_model);

        // 3. Operational Insights
        renderInsightsList(data.learning_insights);

        // 4. Statistical Anomalies Dashboard
        renderAnomaliesList(data.anomalies);

        // 5. Intervention Effectiveness Rankings
        renderInterventionsList(data.intervention_rankings);

        // 6. Advisory Adaptive Thresholds
        renderAdvisoriesList(data.advisory_thresholds);

    } catch (err) {
        console.error("Error loading Learning Center data:", err);
    }
}

function renderDataHealthAndEligibility(dh, elig) {
    if (dh) {
        document.getElementById("lrnTotalRecords").textContent = dh.total_records || 0;
        document.getElementById("lrnUsableRecords").textContent = dh.usable_training_records || 0;
        document.getElementById("lrnDataQualityPct").textContent = `${dh.data_quality_pct || 100.0}%`;
    }

    if (elig) {
        const badge = document.getElementById("lrnMlReadyBadge");
        const reason = document.getElementById("lrnMlReason");
        const card = document.getElementById("lrnEligibilityCard");

        if (elig.ml_ready) {
            badge.textContent = "SUPERVISED ML READY";
            badge.style.color = "#10B981";
            if (card) card.style.borderLeft = "4px solid #10B981";
            reason.textContent = `${elig.total_records} records verified. Training ready.`;
        } else {
            badge.textContent = "ANALYTICS ONLY";
            badge.style.color = "#F59E0B";
            if (card) card.style.borderLeft = "4px solid #F59E0B";
            reason.textContent = `${elig.reason}`;
        }
    }
}

function renderActiveModelStatus(model) {
    if (!model) {
        document.getElementById("lrnActiveModelId").textContent = "RiskModel-v1.0 (Baseline Baseline)";
        document.getElementById("lrnActiveStatusBadge").textContent = "BASELINE";
        document.getElementById("lrnActiveModelType").textContent = "Type: Baseline Rule Risk & Statistical Anomaly Model";
        document.getElementById("lrnActiveModelMeta").textContent = "Status: Supervised ML pending historical training dataset.";
        document.getElementById("lrnMetricAcc").textContent = "N/A";
        document.getElementById("lrnMetricPrec").textContent = "N/A";
        document.getElementById("lrnMetricRec").textContent = "N/A";
        document.getElementById("lrnMetricF1").textContent = "N/A";
        return;
    }

    document.getElementById("lrnActiveModelId").textContent = model.model_id || "RiskModel-v1.0";
    document.getElementById("lrnActiveStatusBadge").textContent = (model.status || "ACTIVE").toUpperCase();
    document.getElementById("lrnActiveModelType").textContent = `Type: ${model.model_type || 'Classifier'}`;
    document.getElementById("lrnActiveModelMeta").textContent = `Dataset: ${model.training_dataset_version || 'v1'} | Features: ${(model.features || []).length} | Version: ${model.version}`;

    const m = model.metrics || {};
    document.getElementById("lrnMetricAcc").textContent = m.accuracy !== undefined ? `${(m.accuracy * 100).toFixed(1)}%` : "N/A";
    document.getElementById("lrnMetricPrec").textContent = m.precision !== undefined ? `${(m.precision * 100).toFixed(1)}%` : "N/A";
    document.getElementById("lrnMetricRec").textContent = m.recall !== undefined ? `${(m.recall * 100).toFixed(1)}%` : "N/A";
    document.getElementById("lrnMetricF1").textContent = m.f1 !== undefined ? m.f1.toFixed(2) : "N/A";
}

function renderInsightsList(insights) {
    const container = document.getElementById("lrnInsightsContainer");
    if (!container) return;

    if (!insights || insights.length === 0) {
        container.innerHTML = `<p style="font-size:11.5px; color:var(--text-muted);">No insights generated yet.</p>`;
        return;
    }

    container.innerHTML = insights.map(ins => `
        <div style="background:var(--bg-primary); padding:8px 12px; border-radius:4px; border-left:3px solid var(--accent-cyan); font-size:11.5px; color:var(--text-primary);">
            ${ins}
        </div>
    `).join("");
}

function renderAnomaliesList(anomalies) {
    const tbody = document.getElementById("lrnAnomaliesTableBody");
    if (!tbody) return;

    if (!anomalies || anomalies.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted);"> Zero statistical anomalies detected across all regional facilities.</td></tr>`;
        return;
    }

    tbody.innerHTML = anomalies.map(a => `
        <tr>
            <td>${getRiskBadgeHTML(a.classification)}</td>
            <td><strong>${a.site_name}</strong> <small style="color:var(--text-muted);">(${a.site_id})</small></td>
            <td>${a.equipment_id} <small style="color:var(--text-muted);">(${a.equipment_type})</small></td>
            <td style="font-weight:700; color:var(--status-danger);">${a.current_risk} / 100</td>
            <td style="font-weight:600; color:var(--text-secondary);">${a.historical_baseline_risk} / 100</td>
            <td style="font-weight:700; color:${a.deviation_pts >= 0 ? '#EF4444' : '#10B981'};">${a.deviation_pts >= 0 ? '+' : ''}${a.deviation_pts} pts</td>
            <td><strong style="color:var(--accent-cyan); font-size:13px;">${a.anomaly_score} / 100</strong></td>
            <td><small style="color:var(--text-primary); font-size:11px;">${a.explanation}</small></td>
        </tr>
    `).join("");
}

function renderInterventionsList(rankings) {
    const container = document.getElementById("lrnInterventionsContainer");
    if (!container) return;

    if (!rankings || rankings.length === 0) {
        container.innerHTML = `<p style="font-size:11.5px; color:var(--text-muted);">No intervention outcomes evaluated yet.</p>`;
        return;
    }

    container.innerHTML = rankings.map(r => `
        <div style="background:var(--bg-primary); padding:10px; border-radius:6px; border:1px solid var(--border-color); font-size:11.5px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <strong style="color:var(--text-primary);">${r.action}</strong>
                <span class="ma-status-badge badge-low" style="background:#10B981; font-size:9px;">${r.evidence_strength} EVIDENCE</span>
            </div>
            <small style="color:var(--text-secondary); display:block;">Sample Size: ${r.sample_size} events | Avg Risk Reduction: <strong style="color:var(--accent-cyan);">${r.avg_risk_reduction_pts} pts</strong></small>
            <p style="color:var(--text-muted); margin:4px 0 0; font-size:10.5px;">${r.explanation}</p>
        </div>
    `).join("");
}

function renderAdvisoriesList(advisories) {
    const container = document.getElementById("lrnAdvisoriesContainer");
    if (!container) return;

    if (!advisories || advisories.length === 0) {
        container.innerHTML = `<p style="font-size:11.5px; color:var(--text-muted);">No advisory thresholds computed.</p>`;
        return;
    }

    container.innerHTML = advisories.map(adv => `
        <div style="background:var(--bg-primary); padding:10px; border-radius:6px; border:1px solid var(--border-color); font-size:11.5px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <strong style="color:var(--accent-cyan);">${adv.site_name} (${adv.site_id})</strong>
                <small style="color:var(--text-muted); font-weight:700;">ADVISORY ONLY</small>
            </div>
            <div style="display:flex; gap:16px; margin:4px 0; color:var(--text-secondary); font-size:11px;">
                <div>Global Warn: <strong>${adv.global_warning_threshold}</strong></div>
                <div>Advisory Warn: <strong style="color:#F59E0B;">${adv.advisory_warning_threshold}</strong></div>
                <div>Advisory Crit: <strong style="color:#EF4444;">${adv.advisory_critical_threshold}</strong></div>
            </div>
            <p style="color:var(--text-muted); margin:4px 0 0; font-size:10.5px;">${adv.advisory_reason}</p>
        </div>
    `).join("");
}

async function handleTrainModel() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/learning/train`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model_type: "RandomForest", force: false })
        });
        const data = await res.json();
        if (data.success) {
            alert(`Model trained successfully! New Model ID: ${data.model_id} (F1 Score: ${data.metrics.f1})`);
            loadLearningCenterData();
        } else {
            alert(`Model Training Advisory: ${data.error || 'Insufficient training data.'}`);
        }
    } catch (err) {
        console.error("Error training ML model:", err);
    }
}

/* ============================================================

   PHASE 21: INTERACTIVE DIGITAL TWIN & WHAT-IF SIMULATOR
   ============================================================ */

let selectedScenarioSiteId = "SITE-001";

function handleScenarioFacilitySelection(siteId) {
    selectedScenarioSiteId = siteId;
    runDigitalTwinSimulation();
}

function updateSliderPreview(sliderName, value, unit) {
    const previewElem = document.getElementById(`valSlide${sliderName}`);
    if (previewElem) {
        previewElem.textContent = `${value}${unit}`;
    }
}

async function applyPresetScenario(presetId, element) {
    // Highlight active preset button
    document.querySelectorAll('.btn-scenario').forEach(btn => btn.classList.remove('active'));
    if (element) element.classList.add('active');

    try {
        const res = await fetch(`${API_BASE_URL}/api/scenarios/presets`);
        const data = await res.json();
        if (!data.success || !data.presets) return;

        const preset = data.presets.find(p => p.id === presetId);
        if (!preset) return;

        const inp = preset.inputs;
        if (inp.temperature !== undefined) {
            document.getElementById("slideTemp").value = inp.temperature;
            updateSliderPreview("Temp", inp.temperature, "°C");
        }
        if (inp.humidity !== undefined) {
            document.getElementById("slideHum").value = inp.humidity;
            updateSliderPreview("Hum", inp.humidity, "%");
        }
        if (inp.rainfall !== undefined) {
            document.getElementById("slideRain").value = inp.rainfall;
            updateSliderPreview("Rain", inp.rainfall, " mm");
        }
        if (inp.duration_hours !== undefined) {
            document.getElementById("slideDur").value = inp.duration_hours;
            updateSliderPreview("Dur", inp.duration_hours, " hrs");
        }

        if (inp.transformer_load !== undefined) {
            document.getElementById("slideTxLoad").value = inp.transformer_load;
            updateSliderPreview("TxLoad", inp.transformer_load, "%");
        }
        if (inp.transformer_cooling !== undefined) {
            document.getElementById("slideTxCool").value = inp.transformer_cooling;
            updateSliderPreview("TxCool", inp.transformer_cooling, "%");
        }
        if (inp.chiller_capacity !== undefined) {
            document.getElementById("slideChCap").value = inp.chiller_capacity;
            updateSliderPreview("ChCap", inp.chiller_capacity, "%");
        }
        if (inp.pump_flow !== undefined) {
            document.getElementById("slidePumpFlow").value = inp.pump_flow;
            updateSliderPreview("PumpFlow", inp.pump_flow, "%");
        }

        // Toggles
        document.getElementById("tglTxCoolFail").checked = !!inp.toggle_cooling_failure;
        document.getElementById("tglChillerRest").checked = !!inp.toggle_chiller_restriction;
        document.getElementById("tglPumpFail").checked = !!inp.toggle_pump_failure;

        // Auto-run simulation
        runDigitalTwinSimulation();

    } catch (err) {
        console.error("Error applying preset scenario:", err);
    }
}

async function runDigitalTwinSimulation() {
    try {
        const payload = {
            site_id: selectedScenarioSiteId,
            inputs: {
                temperature: parseFloat(document.getElementById("slideTemp").value),
                humidity: parseFloat(document.getElementById("slideHum").value),
                rainfall: parseFloat(document.getElementById("slideRain").value),
                rain_probability: parseFloat(document.getElementById("slideHum").value * 0.8),
                wind_speed: 12.0,
                duration_hours: parseFloat(document.getElementById("slideDur").value),
                transformer_load: parseFloat(document.getElementById("slideTxLoad").value),
                transformer_cooling: parseFloat(document.getElementById("slideTxCool").value),
                chiller_capacity: parseFloat(document.getElementById("slideChCap").value),
                pump_flow: parseFloat(document.getElementById("slidePumpFlow").value),
                toggle_cooling_failure: document.getElementById("tglTxCoolFail").checked,
                toggle_chiller_restriction: document.getElementById("tglChillerRest").checked,
                toggle_pump_failure: document.getElementById("tglPumpFail").checked
            }
        };

        const res = await fetch(`${API_BASE_URL}/api/scenarios/simulate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success) {
            renderDigitalTwinResults(data);
        }

    } catch (err) {
        console.error("Error running Digital Twin simulation:", err);
    }
}

function renderDigitalTwinResults(data) {
    // Baseline & Scenario Delta Cards
    const baseRisk = data.baseline.system_risk;
    const simRisk = data.scenario.system_risk;
    const delta = data.risk_change;
    const resScore = data.scenario.resilience_score;
    const resClass = data.scenario.resilience_classification;

    document.getElementById("scenBaseRisk").textContent = `${baseRisk} / 100`;
    document.getElementById("scenSimRisk").textContent = `${simRisk} / 100`;

    const deltaElem = document.getElementById("scenDelta");
    deltaElem.textContent = `${delta >= 0 ? '+' : ''}${delta}`;
    deltaElem.style.color = delta > 0 ? "var(--status-danger)" : "var(--status-success)";

    document.getElementById("scenResilienceScore").textContent = `${resilienceScoreFormat(resScore)} / 100`;
    const resBadge = document.getElementById("scenResilienceClassBadge");
    if (resBadge) {
        resBadge.textContent = resClass;
        resBadge.style.background = resScore >= 60.0 ? "#10B981" : (resScore >= 40.0 ? "#F59E0B" : "#EF4444");
    }

    // ML Status Badge
    const mlBadge = document.getElementById("dtMlStatusBadge");
    if (mlBadge && data.ml_integration) {
        if (data.ml_integration.ml_available) {
            mlBadge.textContent = `ACTIVE ML MODEL (${data.ml_integration.ml_model_id})`;
            mlBadge.style.background = "#10B981";
        } else {
            mlBadge.textContent = "DIGITAL TWIN SIMULATION (ANALYTICS ONLY)";
            mlBadge.style.background = "#64748B";
        }
    }

    // Equipment Breakdown
    const eq = data.equipment || {};
    document.getElementById("scenTxRiskVal").textContent = `${eq.transformer ? eq.transformer.risk : '--'} / 100`;
    document.getElementById("scenChRiskVal").textContent = `${eq.chiller ? eq.chiller.risk : '--'} / 100`;
    document.getElementById("scenWpRiskVal").textContent = `${eq.water_pump ? eq.water_pump.risk : '--'} / 100`;

    // Primary Risk Driver
    document.getElementById("scenPrimaryDriver").textContent = data.primary_driver || "Equipment Stress Overload";
    document.getElementById("scenPrimaryReason").textContent = data.primary_reason || "Cascade propagation modeling.";

    // Digital Twin Cascade Diagram
    const flowContainer = document.getElementById("scenCascadeChainDiagram");
    if (flowContainer && data.cascade_path) {
        flowContainer.innerHTML = data.cascade_path.map((node, idx) => `
            <div class="flow-node">
                <strong>${node.node}</strong>
                <small>${node.value}</small>
                <div style="font-weight:700; color:var(--accent-cyan); font-size:10px; margin-top:2px;">${node.impact}</div>
            </div>
            ${idx < data.cascade_path.length - 1 ? '<div class="flow-connector">--&gt;</div>' : ''}
        `).join("");
    }

    // Interventions Matrix
    renderInterventionsMatrix(data.interventions || []);
}

function resilienceScoreFormat(score) {
    return score !== undefined ? score.toFixed(1) : "0.0";
}

function renderInterventionsMatrix(interventions) {
    const tbody = document.getElementById("scenInterventionTableBody");
    if (!tbody) return;

    if (!interventions || interventions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No intervention strategies evaluated.</td></tr>`;
        return;
    }

    tbody.innerHTML = interventions.map(inv => `
        <tr style="${inv.is_recommended ? 'background:rgba(16,185,129,0.08); font-weight:700;' : ''}">
            <td><strong>${inv.strategy}</strong></td>
            <td style="color:var(--status-danger);">${inv.simulated_system_risk} / 100</td>
            <td style="color:var(--accent-cyan);">${inv.simulated_resilience_score} / 100</td>
            <td style="color:#10B981;">-${inv.risk_reduction_pts} pts</td>
            <td>
                ${inv.is_recommended ? '<span class="ma-status-badge badge-low" style="background:#10B981;">RECOMMENDED OPTION</span>' : '<span style="color:var(--text-muted); font-size:11px;">SIMULATED</span>'}
            </td>
        </tr>
    `).join("");
}

/* ============================================================
   PHASE 22: RESILIENCE OPTIMIZATION & PRESCRIPTIVE ACTION PLANNER
   ============================================================ */

let currentOptimizationId = null;

async function runOptimizationEngine() {
    try {
        const payload = {
            site_id: selectedScenarioSiteId,
            scenario: {
                temperature: parseFloat(document.getElementById("slideTemp").value),
                humidity: parseFloat(document.getElementById("slideHum").value),
                rainfall: parseFloat(document.getElementById("slideRain").value),
                duration_hours: parseFloat(document.getElementById("slideDur").value),
                transformer_load: parseFloat(document.getElementById("slideTxLoad").value),
                transformer_cooling: parseFloat(document.getElementById("slideTxCool").value),
                chiller_capacity: parseFloat(document.getElementById("slideChCap").value),
                pump_flow: parseFloat(document.getElementById("slidePumpFlow").value),
                toggle_cooling_failure: document.getElementById("tglTxCoolFail").checked,
                toggle_chiller_restriction: document.getElementById("tglChillerRest").checked,
                toggle_pump_failure: document.getElementById("tglPumpFail").checked
            }
        };

        const res = await fetch(`${API_BASE_URL}/api/optimization/optimize`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (data.success && data.optimization) {
            currentOptimizationId = data.optimization.optimization_id;
            renderOptimizationResults(data.optimization);
        }

    } catch (err) {
        console.error("Error running optimization engine:", err);
    }
}

function renderOptimizationResults(opt) {
    const rec = opt.recommended_plan;
    if (!rec) return;

    // Recommended Plan Highlight Card
    document.getElementById("optRecPlanName").textContent = rec.strategy_name;
    document.getElementById("optRecScoreVal").textContent = `${rec.objective_score} / 100`;
    
    const classBadge = document.getElementById("optRecScoreClass");
    if (classBadge) {
        classBadge.textContent = rec.score_classification;
        classBadge.style.background = rec.objective_score >= 61.0 ? "#10B981" : (rec.objective_score >= 41.0 ? "#F59E0B" : "#EF4444");
    }

    document.getElementById("optRecRationale").textContent = opt.rationale;
    document.getElementById("optRecRiskRed").textContent = `-${rec.risk_reduction_pts} pts`;
    document.getElementById("optRecDisrupt").textContent = rec.operational_disruption;
    document.getElementById("optRecTime").textContent = `${rec.response_time_minutes} mins`;
    document.getElementById("optRecResource").textContent = rec.resource_level;

    // Lifecycle badge
    const lifeBadge = document.getElementById("optLifecycleBadge");
    if (lifeBadge) {
        lifeBadge.textContent = opt.lifecycle_status;
        lifeBadge.style.background = opt.lifecycle_status === "APPROVED" ? "#10B981" : (opt.lifecycle_status === "IN_PROGRESS" ? "#06B6D4" : "#F59E0B");
    }

    // Candidate Plans Table
    const tbody = document.getElementById("optCandidateTableBody");
    if (tbody && opt.candidate_plans) {
        tbody.innerHTML = opt.candidate_plans.map(plan => `
            <tr style="${plan.plan_id === rec.plan_id ? 'background:rgba(6,182,212,0.08); font-weight:700;' : ''}">
                <td><strong>${plan.strategy_name}</strong></td>
                <td style="color:var(--accent-cyan);">${plan.objective_score} (${plan.score_classification})</td>
                <td style="color:var(--status-danger);">${plan.simulated_system_risk} / 100</td>
                <td style="color:#10B981;">-${plan.risk_reduction_pts} pts</td>
                <td>${plan.operational_disruption}</td>
                <td>${plan.response_time_minutes} min</td>
                <td>${plan.resource_level}</td>
            </tr>
        `).join("");
    }

    // Action Plan Timeline
    const timelineContainer = document.getElementById("optTimelineContainer");
    if (timelineContainer && opt.action_timeline) {
        timelineContainer.innerHTML = opt.action_timeline.map(step => `
            <div style="background:var(--bg-secondary); padding:8px 12px; border-radius:4px; border-left:3px solid var(--accent-cyan);">
                <div style="display:flex; justify-content:space-between; font-size:10px; font-weight:800; color:var(--accent-cyan);">
                    <span>${step.phase}</span>
                    <span>${step.time}</span>
                </div>
                <div style="font-size:11.5px; color:var(--text-primary); margin-top:2px;">${step.action}</div>
            </div>
        `).join("");
    }

    // Robustness & Sensitivity
    const rob = opt.robustness_analysis || {};
    const robBadge = document.getElementById("optRobustnessBadge");
    if (robBadge) {
        robBadge.textContent = rob.status_badge || "ROBUST RECOMMENDATION";
        robBadge.style.background = rob.is_robust ? "#10B981" : "#F59E0B";
    }
    document.getElementById("optRobustnessDesc").textContent = rob.explanation || "Plan stability analysis across temperature variations.";

    const sensContainer = document.getElementById("optSensitivityContainer");
    if (sensContainer && opt.sensitivity_analysis) {
        sensContainer.innerHTML = opt.sensitivity_analysis.map(s => `
            <div style="display:flex; justify-content:space-between; color:var(--text-secondary);">
                <span>${s.variable}</span>
                <strong style="color:${s.impact_level === 'HIGH' ? '#EF4444' : '#F59E0B'};">+${s.risk_delta} pts (${s.impact_level})</strong>
            </div>
        `).join("");
    }
}

async function approveOptimizationPlan() {
    if (!currentOptimizationId) {
        alert("Please run 'OPTIMIZE RESPONSE' first before approving an action plan.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/api/optimization/${currentOptimizationId}/approve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ operator_name: "Shift Engineer" })
        });
        const data = await res.json();
        if (data.success && data.optimization) {
            alert(`Action Plan Approved! Status: APPROVED for ${data.optimization.optimization_id}`);
            renderOptimizationResults(data.optimization);
        }
    } catch (err) {
        console.error("Error approving action plan:", err);
    }
}

async function promoteOptimizationToIncident() {
    if (!currentOptimizationId) {
        alert("Please run 'OPTIMIZE RESPONSE' first before promoting to Incidents.");
        return;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/api/optimization/${currentOptimizationId}/promote`, {
            method: "POST"
        });
        const data = await res.json();
        if (data.success) {
            alert(`Approved Plan Promoted to Incident Command Center! Created Incident ID: ${data.incident.incident_id}`);
            if (data.optimization) {
                renderOptimizationResults(data.optimization);
            }
        } else {
            alert(`Promotion failed: ${data.detail || data.error || 'Unable to promote.'}`);
        }
    } catch (err) {
        console.error("Error promoting plan to incident:", err);
    }
}


/* ============================================================
   PHASE 6: REAL-TIME IoT & DEVICE REGISTRY CONTROLLER
   ============================================================ */

let telemetryHistoryChart = null;

async function loadIotRegistryData(siteId = null) {
    const sId = siteId || currentSelectedSiteId;
    if (!sId || sId === "ALL") return;

    try {
        const devRes = await fetch(`${API_BASE_URL}/api/v1/devices`);
        const devData = await devRes.json();
        if (!devData.success) return;

        const telRes = await fetch(`${API_BASE_URL}/api/facilities/${sId}/telemetry`);
        const telData = await telRes.json();
        if (!telData.success) return;

        const telemetryMode = telData.telemetry.telemetry_source || "SIMULATION";
        const modeSelector = document.getElementById("globalTelemetryModeSelector");
        if (modeSelector) {
            modeSelector.value = telemetryMode;
        }

        const compBody = document.getElementById("iotDeviceTableBody");
        if (!compBody) return;

        const devices = devData.devices.filter(d => d.location === sId);
        if (devices.length === 0) {
            compBody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 20px; color: var(--text-muted);">No IoT devices registered for this facility.</td></tr>`;
            return;
        }

        let tableHtml = "";
        devices.forEach(dev => {
            const assetType = dev.asset_type.toLowerCase();
            const assetInfo = telData.telemetry.assets[assetType] || {};
            const source = assetInfo.source || "SIMULATED";
            const connection = assetInfo.connection || dev.status || "OFFLINE";
            
            const errors = assetInfo.data_quality?.validation_errors || [];
            const isHealthy = errors.length === 0;
            const signal = dev.signal_quality || 100;
            
            const connClass = connection === "ONLINE" ? "lvl-NORMAL" : (connection === "STALE" ? "lvl-WARNING" : "lvl-CRITICAL");
            const srcClass = source === "HARDWARE" || source === "MEASURED" ? "live-weather" : "pred-sim";
            const dqClass = isHealthy ? "lvl-NORMAL" : "lvl-CRITICAL";

            tableHtml += `
                <tr>
                    <td style="font-size: 13.5px;"><strong>${dev.device_id}</strong></td>
                    <td style="font-size: 14.5px; font-weight: 600; text-transform: uppercase;">${dev.asset_type} <span style="font-size: 11.5px; color: var(--text-muted); font-weight: 500; margin-left: 4px;">(${dev.asset_id})</span></td>
                    <td style="font-size: 13.5px; color: var(--text-secondary);">${dev.location}</td>
                    <td style="font-size: 13.5px; color: var(--text-secondary); text-transform: uppercase;">${dev.protocol}</td>
                    <td style="font-size: 11.5px;"><span class="prov-badge ${srcClass}">${source}</span></td>
                    <td style="font-size: 11.5px;"><span class="status-badge ${connClass}">${connection}</span></td>
                    <td style="font-size: 13.5px; color: var(--text-secondary); font-weight: 700;">${signal}%</td>
                    <td style="font-size: 11.5px;"><span class="status-badge ${dqClass}">${isHealthy ? 'VALID' : 'FAULT'}</span></td>
                    <td style="text-align: center;"><button class="btn-primary" style="padding: 6px 12px; font-size: 12px; font-weight: 700; border: none; background: var(--brand-accent, #06B6D4); color: #0B1120; cursor: pointer;" onclick="openTelemetryDetail('${dev.device_id}')">INSPECT</button></td>
                </tr>
            `;
        });
        compBody.innerHTML = tableHtml;

    } catch (err) {
        console.error("Error loading IoT registry table:", err);
    }
}

async function handleTelemetryModeChange(mode) {
    if (!currentSelectedSiteId || currentSelectedSiteId === "ALL") return;
    try {
        const res = await fetch(`${API_BASE_URL}/api/facilities/${currentSelectedSiteId}/telemetry-mode`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: mode })
        });
        const data = await res.json();
        if (data.success) {
            loadIotRegistryData();
            fetchRegionalStatus();
        }
    } catch (err) {
        console.error("Error changing telemetry mode:", err);
    }
}

async function openTelemetryDetail(deviceId) {
    try {
        const modal = document.getElementById("telemetryDetailModal");
        if (!modal) return;

        const devRes = await fetch(`${API_BASE_URL}/api/v1/devices/${deviceId}`);
        const devData = await devRes.json();
        if (!devData.success) return;

        const dev = devData.device;

        const latestRes = await fetch(`${API_BASE_URL}/api/v1/telemetry/latest?device_id=${deviceId}`);
        const latestData = await latestRes.json();
        if (!latestData.success) return;

        const latest = latestData.latest || {};

        document.getElementById("telDtlDeviceId").textContent = `DEVICE: ${deviceId}`;
        document.getElementById("telDtlTitle").textContent = `${dev.asset_type.toUpperCase()} MONITORING`;
        document.getElementById("telDtlMetadata").textContent = `Asset ID: ${dev.asset_id} | Location: ${dev.location} | Firmware: ${dev.firmware_version}`;

        const grid = document.getElementById("telDtlMeasurementsGrid");
        let gridHtml = "";
        
        let primaryMeasurement = null;
        
        for (const [key, details] of Object.entries(latest)) {
            if (!primaryMeasurement) primaryMeasurement = key;
            
            const qualityColor = details.quality === "VALID" ? "#22C55E" : "#EF4444";
            gridHtml += `
                <div style="background: rgba(0,0,0,0.15); border: 1px solid var(--border-subtle); padding: 10px; border-radius: 4px; display: flex; flex-direction: column; justify-content: space-between;">
                    <span style="color: var(--text-muted); font-size: 11px; font-weight: 700; text-transform: uppercase;">${key.replace('_', ' ')}</span>
                    <strong style="font-size: 16px; color: var(--text-primary); margin: 4px 0;">${details.value.toFixed(2)} <span style="font-size: 12px; font-weight: 500; color: var(--text-muted);">${details.unit}</span></strong>
                    <span style="color: ${qualityColor}; font-size: 10.5px; font-weight: 700;">● ${details.quality}</span>
                </div>
            `;
        }
        if (!gridHtml) {
            gridHtml = `<div style="grid-column: span 2; text-align: center; color: var(--text-muted); padding: 10px;">No active telemetry streams.</div>`;
        }
        grid.innerHTML = gridHtml;

        const diagContainer = document.getElementById("telDtlDiagnosticsContainer");
        const diagText = document.getElementById("telDtlDiagnosticsText");
        
        let errors = [];
        for (const [key, details] of Object.entries(latest)) {
            if (details.quality !== "VALID") {
                errors.push(`${key}: ${details.quality}`);
            }
        }

        if (errors.length > 0) {
            diagText.textContent = `Fault status detected: ${errors.join(', ')}. Value out of operating bounds or sensor stuck.`;
            diagContainer.style.display = "block";
            document.getElementById("telDtlQualityBadge").textContent = "FAULT";
            document.getElementById("telDtlQualityBadge").style.background = "#EF4444";
        } else {
            diagContainer.style.display = "none";
            document.getElementById("telDtlQualityBadge").textContent = "VALID";
            document.getElementById("telDtlQualityBadge").style.background = "#10B981";
        }

        modal.style.display = "flex";
        modal.classList.remove("hidden");

        if (primaryMeasurement) {
            loadTelemetryHistoryChart(deviceId, primaryMeasurement);
        }

    } catch (err) {
        console.error("Error opening telemetry details modal:", err);
    }
}

function closeTelemetryDetail() {
    const modal = document.getElementById("telemetryDetailModal");
    if (modal) {
        modal.style.display = "none";
        modal.classList.add("hidden");
    }
}

async function loadTelemetryHistoryChart(deviceId, measurement) {
    try {
        const res = await fetch(`${API_BASE_URL}/api/v1/telemetry/history?device_id=${deviceId}&measurement=${measurement}&limit=30`);
        const data = await res.json();
        if (!data.success) return;

        const history = data.history || [];
        const canvas = document.getElementById("telemetryDetailChart");
        if (!canvas) return;

        const labels = history.map(pt => pt.timestamp.split(' ')[1] || pt.timestamp);
        const values = history.map(pt => pt.value);
        const unit = history.length > 0 ? history[0].unit : "";

        if (telemetryHistoryChart) {
            telemetryHistoryChart.destroy();
        }

        telemetryHistoryChart = new Chart(canvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: `${measurement.toUpperCase()} (${unit})`,
                    data: values,
                    borderColor: 'var(--brand-accent, #06B6D4)',
                    backgroundColor: 'rgba(6, 182, 212, 0.05)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.15,
                    pointRadius: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        grid: { color: 'var(--border-subtle)' },
                        ticks: { color: 'var(--text-secondary)' }
                    },
                    x: {
                        grid: { color: 'transparent' },
                        ticks: { color: 'var(--text-secondary)', maxTicksLimit: 6 }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });

    } catch (err) {
        console.error("Error loading telemetry history chart:", err);
    }
}

