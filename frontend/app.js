const API_BASE_URL = (window.location.protocol.startsWith("http")) ? "" : "http://127.0.0.1:5050";

let fleetTimer = null;
let fleetDataCache = [];
let fleetSummaryCache = {};
let selectedDetailTxId = null;
const visibleTxMap = { "TX-001": true, "TX-002": true, "TX-003": true, "TX-004": true, "TX-005": true };

const TX_COLORS = {
    "TX-001": "#70e000",
    "TX-002": "#ffaa00",
    "TX-003": "#ff4d4d",
    "TX-004": "#00d2ff",
    "TX-005": "#d8b4f8"
};


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

    document.getElementById("btnStartFleet").disabled = true;
    document.getElementById("btnStopFleet").disabled = false;

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

    document.getElementById("btnStartFleet").disabled = false;
    document.getElementById("btnStopFleet").disabled = true;

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

    document.getElementById("fltTotalMonitored").textContent = summary.total_monitored || 5;
    document.getElementById("fltNormalCount").textContent = summary.normal_count || 0;
    document.getElementById("fltWatchCount").textContent = summary.watch_count || 0;
    document.getElementById("fltWarningCount").textContent = summary.warning_count || 0;
    document.getElementById("fltCriticalCount").textContent = summary.critical_count || 0;

    const avgRisk = summary.fleet_risk !== undefined ? summary.fleet_risk.toFixed(1) : "--";
    document.getElementById("fltAvgRisk").textContent = `${avgRisk} / 100`;
    document.getElementById("fltAvgRiskLevel").textContent = summary.fleet_status || "LOW";

    const h = summary.highest_risk_transformer;
    if (h) {
        document.getElementById("fltHighestRisk").textContent = h.transformer_id;
        document.getElementById("fltHighestRiskScore").textContent = `Score: ${h.score.toFixed(1)} (${h.level})`;
    }

    const stateBadge = document.getElementById("fleetStateBadge");
    if (stateBadge) {
        stateBadge.textContent = `FLEET STATUS: ${summary.fleet_status || "NORMAL"}`;
        stateBadge.className = `badge-ew ew-${(summary.fleet_status || "NORMAL").toLowerCase()}`;
    }
}


function renderTopPriorityPanel(fleetList) {
    if (!fleetList || fleetList.length === 0) return;

    // Rank #1 transformer
    const topTx = fleetList[0];

    document.getElementById("prioTxName").textContent = `${topTx.transformer_id} — ${topTx.display_name}`;
    document.getElementById("prioTxLoc").textContent = `Location: ${topTx.location} | Priority Rank #1`;

    document.getElementById("prioCurrentScore").textContent = `${topTx.cascade.score.toFixed(1)} / 100`;
    
    const fc60 = topTx.predictive_forecast?.forecast?.["60m"]?.cascade_score;
    document.getElementById("prioForecastScore").textContent = fc60 !== undefined ? `${fc60.toFixed(1)} / 100` : "--";

    const ew = topTx.explainability?.early_warning_state || "NORMAL";
    const ewElem = document.getElementById("prioEarlyWarning");
    ewElem.textContent = ew;
    ewElem.className = `hz-level ew-${ew.toLowerCase()}`;

    const topFactors = topTx.explainability?.top_factors || [];
    if (topFactors.length > 0) {
        document.getElementById("prioRiskFactor").textContent = `${topFactors[0].description} (SHAP ${topFactors[0].shap_value > 0 ? '+' : ''}${topFactors[0].shap_value})`;
    } else {
        document.getElementById("prioRiskFactor").textContent = "Operational telemetry stable.";
    }

    document.getElementById("prioActionText").textContent = topTx.decision_support?.detailed_guidance || topTx.recommendation || "Continue normal monitoring.";
}


function renderFleetTable(fleetList) {
    const tbody = document.getElementById("fleetTableBody");
    if (!tbody) return;

    if (!fleetList || fleetList.length === 0) {
        tbody.innerHTML = `<tr><td colspan="12" class="placeholder-text">No active fleet data.</td></tr>`;
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
            <tr onclick="openTransformerDetail('${tx.transformer_id}')" class="fleet-row">
                <td><strong>#${tx.priority_rank}</strong></td>
                <td><code>${tx.transformer_id}</code></td>
                <td><strong>${tx.display_name}</strong></td>
                <td>${tx.location}</td>
                <td>${tx.health.risk.toFixed(1)}</td>
                <td>${tx.operational.risk.toFixed(1)}%</td>
                <td>${tx.climate.climate_stress.toFixed(1)}</td>
                <td><strong class="score-cell">${score.toFixed(1)}</strong></td>
                <td><strong>${fc60}</strong></td>
                <td><span class="${trendClass}">${trend}</span></td>
                <td><span class="${statusClass}">${level}</span></td>
                <td><button onclick="event.stopPropagation(); openTransformerDetail('${tx.transformer_id}')" class="btn-primary btn-sm">INSPECT</button></td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}


function renderFleetHeatmap(fleetList) {
    const container = document.getElementById("fleetHeatmapGrid");
    if (!container) return;

    if (!fleetList || fleetList.length === 0) {
        container.innerHTML = `<p class="placeholder-text">Waiting for fleet telemetry...</p>`;
        return;
    }

    let html = "";
    fleetList.forEach(tx => {
        const score = tx.cascade.score;
        const level = tx.cascade.level;
        const ew = tx.explainability?.early_warning_state || "NORMAL";
        const fc60 = tx.predictive_forecast?.forecast?.["60m"]?.cascade_score?.toFixed(1) || "--";

        html += `
            <div class="hm-card hm-${level.toLowerCase()}" onclick="openTransformerDetail('${tx.transformer_id}')">
                <div class="hm-header">
                    <code>${tx.transformer_id}</code>
                    <span class="hm-rank">Rank #${tx.priority_rank}</span>
                </div>
                <h4>${tx.display_name}</h4>
                <small>${tx.location}</small>
                
                <div class="hm-score">
                    <strong>${score.toFixed(1)}</strong>
                    <span>/ 100</span>
                </div>

                <div class="hm-footer">
                    <span class="badge-ew ew-${ew.toLowerCase()}">${ew}</span>
                    <small>+60m: ${fc60}</small>
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
            <div class="climate-card">
                <div class="climate-header">
                    <strong>${tx.location}</strong>
                    <small>TX: ${tx.transformer_id}</small>
                </div>
                <div class="climate-main">
                    <div><small>STRESS</small><strong>${c.climate_stress}</strong></div>
                    <div><small>TEMP</small><strong>${c.temperature} °C</strong></div>
                    <div><small>RAIN</small><strong>${c.rain} mm</strong></div>
                    <div><small>WIND</small><strong>${c.wind} km/h</strong></div>
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

    // Setup chart toggles
    const togglesContainer = document.getElementById("chartToggles");
    if (togglesContainer && togglesContainer.children.length === 0) {
        let toggleHtml = "";
        Object.keys(TX_COLORS).forEach(txId => {
            toggleHtml += `
                <label class="chart-toggle-lbl" style="color: ${TX_COLORS[txId]}">
                    <input type="checkbox" checked onchange="toggleTxVisibility('${txId}', this.checked)">
                    ${txId}
                </label>
            `;
        });
        togglesContainer.innerHTML = toggleHtml;
    }

    const padding = 35;
    const chartW = width - padding * 2;
    const chartH = height - padding * 2;

    // Draw horizontal grid lines
    ctx.strokeStyle = "rgba(49, 93, 77, 0.3)";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#6a8c80";
    ctx.font = "10px Segoe UI, sans-serif";

    [0, 25, 50, 75, 100].forEach(val => {
        const y = height - padding - (val / 100) * chartH;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(width - padding, y);
        ctx.stroke();
        ctx.fillText(val.toString(), 5, y + 3);
    });

    // Draw line for each transformer
    Object.keys(historyMap).forEach(txId => {
        if (!visibleTxMap[txId]) return;

        const history = historyMap[txId];
        if (!history || history.length < 2) return;

        const step = chartW / (history.length - 1);
        ctx.beginPath();
        ctx.strokeStyle = TX_COLORS[txId] || "#70e000";
        ctx.lineWidth = 2.5;

        history.forEach((pt, i) => {
            const x = padding + i * step;
            const y = height - padding - (pt.cascade_score / 100) * chartH;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.stroke();

        // End circle
        const lastPt = history[history.length - 1];
        const lastX = padding + (history.length - 1) * step;
        const lastY = height - padding - (lastPt.cascade_score / 100) * chartH;

        ctx.beginPath();
        ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
        ctx.fillStyle = TX_COLORS[txId] || "#70e000";
        ctx.fill();
    });
}


function toggleTxVisibility(txId, isVisible) {
    visibleTxMap[txId] = isVisible;
    fetchFleetHistory();
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
    document.getElementById("dtlTxId").textContent = tx.transformer_id;
    document.getElementById("dtlTxName").textContent = tx.display_name;
    document.getElementById("dtlTxLoc").textContent = `Location: ${tx.location} | Timestamp: ${tx.timestamp}`;

    const scBadge = document.getElementById("dtlScenarioBadge");
    if (scBadge) {
        scBadge.textContent = `SCENARIO: ${tx.scenario?.name || "NORMAL"}`;
    }

    document.getElementById("dtlCascadeScore").textContent = `${tx.cascade.score.toFixed(1)} / 100`;
    document.getElementById("dtlCascadeLevel").textContent = tx.cascade.level;

    document.getElementById("dtlHealthRisk").textContent = tx.health.risk.toFixed(1);
    document.getElementById("dtlHealthIdx").textContent = `Index: ${tx.health.index.toFixed(1)}`;

    document.getElementById("dtlOpRisk").textContent = `${tx.operational.risk.toFixed(1)} %`;

    document.getElementById("dtlClimateStress").textContent = tx.climate.climate_stress.toFixed(1);
    document.getElementById("dtlPeakTime").textContent = `Peak: ${tx.climate.peak_time || "--"}`;

    // Multi-horizon forecast
    if (tx.predictive_forecast) {
        const pf = tx.predictive_forecast;
        if (pf.current) {
            document.getElementById("dtlNowScore").textContent = pf.current.score.toFixed(1);
            document.getElementById("dtlNowLevel").textContent = pf.current.level;
        }
        if (pf.forecast) {
            const f15 = pf.forecast["15m"];
            const f30 = pf.forecast["30m"];
            const f60 = pf.forecast["60m"];

            if (f15) {
                document.getElementById("dtl15mScore").textContent = f15.cascade_score.toFixed(1);
                document.getElementById("dtl15mLevel").textContent = f15.level;
                document.getElementById("dtl15mProb").textContent = `Prob: ${f15.event_probability_pct}%`;
            }
            if (f30) {
                document.getElementById("dtl30mScore").textContent = f30.cascade_score.toFixed(1);
                document.getElementById("dtl30mLevel").textContent = f30.level;
                document.getElementById("dtl30mProb").textContent = `Prob: ${f30.event_probability_pct}%`;
            }
            if (f60) {
                document.getElementById("dtl60mScore").textContent = f60.cascade_score.toFixed(1);
                document.getElementById("dtl60mLevel").textContent = f60.level;
                document.getElementById("dtl60mProb").textContent = `Prob: ${f60.event_probability_pct}%`;
            }
        }
    }

    // Top SHAP factors
    const topFactors = tx.explainability?.top_factors || [];
    renderDetailTopFactors(topFactors);

    // Decision support
    document.getElementById("dtlRecommendation").textContent = tx.decision_support?.detailed_guidance || tx.recommendation || "Continue normal monitoring.";
}


function renderDetailTopFactors(factors) {
    const container = document.getElementById("dtlShapContainer");
    if (!container) return;

    if (!factors || factors.length === 0) {
        container.innerHTML = `<p class="placeholder-text">No active risk factors reported.</p>`;
        return;
    }

    const maxShap = Math.max(...factors.map(f => f.abs_shap), 0.01);

    let html = "";
    factors.forEach((f, idx) => {
        const barPct = Math.min(Math.round((f.abs_shap / maxShap) * 100), 100);
        const isInc = f.direction === "increases_risk";
        const dirClass = isInc ? "dir-increasing" : "dir-decreasing";
        const dirText = isInc ? "Increasing Risk" : "Decreasing Risk";

        html += `
            <div class="factor-item">
                <div class="factor-header">
                    <span class="factor-name">${idx + 1}. ${f.description}</span>
                    <span class="factor-badge ${dirClass}">${dirText}</span>
                </div>
                <div class="factor-bar-wrapper">
                    <div class="factor-bar ${dirClass}" style="width: ${barPct}%;"></div>
                </div>
                <div class="factor-details">
                    <span>Feature: <code>${f.feature}</code> = ${f.value}</span>
                    <span>SHAP Impact: ${f.shap_value > 0 ? '+' : ''}${f.shap_value} (${f.impact})</span>
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
            body: JSON.stringify({ scenario: scenarioName, location: "Coimbatore" })
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

        fetchScenarioComparisonChart();

    } catch (e) {
        console.error("Climate Scenario Execution Error:", e);
    }
}

async function fetchScenarioComparisonChart() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/scenario-summary`);
        const result = await response.json();
        if (!result.success) return;

        const container = document.getElementById("scenarioBarsContainer");
        if (!container) return;

        const scenarios = result.scenarios || [];
        let html = "";

        scenarios.forEach(sc => {
            const isActive = sc.scenario === currentScenarioName;
            const barClass = isActive ? "scen-bar-fill active-bar" : "scen-bar-fill";
            const hPct = Math.min(Math.max(sc.system_risk, 8), 100);

            html += `
                <div class="scen-bar-item" title="${sc.label}: ${sc.system_risk} / 100">
                    <small style="font-size:0.65rem; color:#e0f5ed; margin-bottom:4px;">${sc.system_risk}</small>
                    <div class="${barClass}" style="height: ${hPct}%;"></div>
                    <span class="scen-bar-lbl">${sc.icon} ${sc.scenario.replace('_', ' ')}</span>
                </div>
            `;
        });

        container.innerHTML = html;

    } catch (e) {
        console.error("Scenario Summary Fetch Note:", e);
    }
}


/* PHASE 11A: SITE LOCATION CONFIGURATION & MAP LOGIC */
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

async function confirmSite() {
    const siteId = document.getElementById("siteInputId").value.trim();
    const siteName = document.getElementById("siteInputName").value.trim();
    const lat = parseFloat(document.getElementById("siteInputLat").value);
    const lon = parseFloat(document.getElementById("siteInputLon").value);
    const txId = document.getElementById("siteInputTx").value.trim();
    const chId = document.getElementById("siteInputCh").value.trim();
    const wpId = document.getElementById("siteInputWp").value.trim();

    if (!siteId || !siteName || isNaN(lat) || isNaN(lon) || !txId || !chId || !wpId) {
        alert("Please ensure all Site ID, Site Name, Latitude, Longitude, and Asset IDs are non-empty and valid.");
        return;
    }

    if (lat < -90 || lat > 90) {
        alert(`Invalid latitude (${lat}). Latitude must be between -90 and 90 degrees.`);
        return;
    }

    if (lon < -180 || lon > 180) {
        alert(`Invalid longitude (${lon}). Longitude must be between -180 and 180 degrees.`);
        return;
    }

    try {
        const payload = {
            site_id: siteId,
            site_name: siteName,
            latitude: lat,
            longitude: lon,
            transformer_id: txId,
            chiller_id: chId,
            water_pump_id: wpId
        };

        const res = await fetch(`${API_BASE_URL}/api/site/configure`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const result = await res.json();
        if (!result.success) {
            alert("Site Configuration Failed:\n" + result.error);
            return;
        }

        updateHeaderSiteBanner(result.site);
        runClimateScenario(currentScenarioName, null);
        analyzeNextFleetSample();

    } catch (e) {
        console.error("Confirm site exception:", e);
    }
}

function updateHeaderSiteBanner(site) {
    if (!site) return;

    const nameElem = document.getElementById("hdrSiteName");
    const idElem = document.getElementById("hdrSiteId");
    const coordsElem = document.getElementById("hdrCoordinates");

    if (nameElem) nameElem.innerText = site.site_name || "Coimbatore Industrial Facility";
    if (idElem) idElem.innerText = site.site_id || "SITE-001";
    if (coordsElem && site.location) {
        const latStr = site.location.latitude >= 0 ? `${site.location.latitude}° N` : `${Math.abs(site.location.latitude)}° S`;
        const lonStr = site.location.longitude >= 0 ? `${site.location.longitude}° E` : `${Math.abs(site.location.longitude)}° W`;
        coordsElem.innerText = `${latStr}, ${lonStr}`;
    }
}

async function fetchSiteConfig() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/site/config`);
        const result = await res.json();
        if (result.success && result.site) {
            const site = result.site;
            document.getElementById("siteInputId").value = site.site_id;
            document.getElementById("siteInputName").value = site.site_name;
            document.getElementById("siteInputLat").value = site.location.latitude;
            document.getElementById("siteInputLon").value = site.location.longitude;
            document.getElementById("siteInputTx").value = site.assets.transformer_id;
            document.getElementById("siteInputCh").value = site.assets.chiller_id;
            document.getElementById("siteInputWp").value = site.assets.water_pump_id;

            updateHeaderSiteBanner(site);
            initSiteMap(site.location.latitude, site.location.longitude);
        }
    } catch (e) {
        console.error("Fetch Site Config Exception:", e);
    }
}


async function fetchClimateIntelligence() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/climate-intelligence`);
        const result = await res.json();
        if (!result.success || !result.climate_intelligence) return;

        const intel = result.climate_intelligence;
        const curr = intel.current || {};
        const hw = intel.heatwave || {};
        const trend = intel.forecast_trend || {};
        const dq = intel.data_quality || {};
        const impacts = intel.asset_impacts || {};

        // Current weather
        const tempElem = document.getElementById("ciCurrTemp");
        const humElem = document.getElementById("ciCurrHum");
        const windElem = document.getElementById("ciCurrWind");
        const rainElem = document.getElementById("ciCurrRain");
        const tempSub = document.getElementById("ciTempSub");

        if (tempElem) tempElem.innerText = `${curr.temperature || '--'} °C`;
        if (humElem) humElem.innerText = `${curr.humidity || '--'} %`;
        if (windElem) windElem.innerText = `${curr.wind || '--'} km/h`;
        if (rainElem) rainElem.innerText = `${curr.rain || 0} mm`;
        if (tempSub) tempSub.innerText = `Peak: ${hw.peak_temperature || '--'} °C`;

        // Heatwave status
        const hwBadge = document.getElementById("ciHwBadge");
        const hwPeak = document.getElementById("ciHwPeak");
        const hwDur = document.getElementById("ciHwDur");
        const hwSev = document.getElementById("ciHwSev");

        if (hwBadge) {
            hwBadge.innerText = hw.severity || "NORMAL";
            hwBadge.className = `ma-status-badge ${hw.severity === 'EXTREME' || hw.severity === 'WARNING' ? 'badge-warning' : 'badge-normal'}`;
        }
        if (hwPeak) hwPeak.innerText = `${hw.peak_temperature || '--'} °C`;
        if (hwDur) hwDur.innerText = `${hw.duration_hours || 0} hrs (≥${hw.threshold_temperature || 35}°C)`;
        if (hwSev) hwSev.innerText = hw.severity || "NORMAL";

        // Trend
        const trendBadge = document.getElementById("ciTrendBadge");
        const currStress = document.getElementById("ciCurrStress");
        const chg6h = document.getElementById("ciChg6h");
        const chg24h = document.getElementById("ciChg24h");

        if (trendBadge) {
            trendBadge.innerText = trend.trend || "STABLE";
            trendBadge.className = `ma-status-badge ${trend.trend === 'RISING' ? 'badge-warning' : 'badge-normal'}`;
        }
        if (currStress) currStress.innerText = `${trend.current_stress || '--'} / 100`;
        if (chg6h) chg6h.innerText = (trend.change_6h > 0 ? `+${trend.change_6h}` : `${trend.change_6h}`) + " pts";
        if (chg24h) chg24h.innerText = (trend.change_24h > 0 ? `+${trend.change_24h}` : `${trend.change_24h}`) + " pts";

        // Data quality
        const provElem = document.getElementById("ciProvider");
        const freshElem = document.getElementById("ciFreshness");
        const confBadge = document.getElementById("ciConfidenceBadge");

        if (provElem) provElem.innerText = dq.source || "Open-Meteo (LIVE)";
        if (freshElem) freshElem.innerText = dq.freshness || "LIVE (< 60s)";
        if (confBadge) {
            confBadge.innerText = `CONFIDENCE: ${dq.confidence || 'HIGH'}`;
            confBadge.className = `fresh-pill ${dq.confidence === 'HIGH' ? 'fresh-live' : 'fresh-ds'}`;
        }

        // Asset Impacts
        const txImp = impacts.transformer || {};
        const chImp = impacts.chiller || {};
        const wpImp = impacts.water_pump || {};

        const txScore = document.getElementById("ciTxScore");
        const txSev = document.getElementById("ciTxSev");
        const txFactors = document.getElementById("ciTxFactors");
        if (txScore) txScore.innerText = `${txImp.climate_stress || '--'} / 100`;
        if (txSev) { txSev.innerText = txImp.severity || 'LOW'; txSev.className = `fresh-pill ${txImp.severity === 'HIGH' ? 'fresh-ds' : 'fresh-hist'}`; }
        if (txFactors) txFactors.innerText = txImp.factors || "";

        const chScore = document.getElementById("ciChScore");
        const chSev = document.getElementById("ciChSev");
        const chFactors = document.getElementById("ciChFactors");
        if (chScore) chScore.innerText = `${chImp.climate_stress || '--'} / 100`;
        if (chSev) { chSev.innerText = chImp.severity || 'LOW'; chSev.className = `fresh-pill ${chImp.severity === 'HIGH' ? 'fresh-ds' : 'fresh-hist'}`; }
        if (chFactors) chFactors.innerText = chImp.factors || "";

        const wpScore = document.getElementById("ciWpScore");
        const wpSev = document.getElementById("ciWpSev");
        const wpFactors = document.getElementById("ciWpFactors");
        if (wpScore) wpScore.innerText = `${wpImp.climate_stress || '--'} / 100 (DS)`;
        if (wpSev) { wpSev.innerText = wpImp.severity || 'MEDIUM'; wpSev.className = `fresh-pill ${wpImp.severity === 'HIGH' ? 'fresh-ds' : 'fresh-hist'}`; }
        if (wpFactors) wpFactors.innerText = wpImp.factors || "";

        // Hourly Visual Chart
        const hourlyContainer = document.getElementById("ciHourlyBarsContainer");
        if (hourlyContainer && intel.visual_points) {
            let html = "";
            intel.visual_points.forEach(pt => {
                const hPct = Math.min(Math.max(pt.stress, 8), 100);
                html += `
                    <div class="ci-hourly-item" title="${pt.horizon} (${pt.time}): ${pt.temperature}°C, Stress: ${pt.stress}">
                        <small style="font-size:0.62rem; color:#e0f5ed; margin-bottom:2px;">${pt.temperature}°C</small>
                        <div class="ci-hourly-bar" style="height:${hPct}%;"></div>
                        <span class="ci-hourly-lbl">${pt.horizon}</span>
                    </div>
                `;
            });
            hourlyContainer.innerHTML = html;
        }

        // Explanations List
        const expList = document.getElementById("ciExplanationsList");
        if (expList && intel.explanation) {
            let html = "";
            intel.explanation.forEach(exp => {
                html += `<li>${exp}</li>`;
            });
            expList.innerHTML = html;
        }

    } catch (e) {
        console.error("Fetch Climate Intelligence Error:", e);
    }
}


/* PHASE 12: REAL-TIME INDUSTRIAL OT TELEMETRY FRONTEND LOGIC */
let liveOTStreamInterval = null;
let currentOTMode = "MOCK";
let currentOTScenario = "NORMAL";

async function fetchOTStatus() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/telemetry/status`);
        const result = await res.json();
        if (!result.success) return;

        currentOTMode = result.telemetry_mode || "MOCK";
        currentOTScenario = result.active_scenario || "NORMAL";

        const modeElem = document.getElementById("otModeDisplay");
        if (modeElem) {
            if (currentOTMode === "REAL_OT") {
                modeElem.innerText = "DATA MODE: REAL OT PROTOCOL CONNECTIVITY";
                modeElem.className = "prov-badge live-weather";
            } else {
                modeElem.innerText = "DATA MODE: MOCK DEMO SIMULATION MODE";
                modeElem.className = "prov-badge pred-sim";
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

        // Update Transformer Card
        const txT = tx.telemetry || {};
        const txConn = document.getElementById("otTxConn");
        const txSrc = document.getElementById("otTxSrc");
        const txFresh = document.getElementById("otTxFresh");
        if (txConn) txConn.innerText = tx.connection_status || "SIMULATED";
        if (txSrc) txSrc.innerText = tx.source || "mock_telemetry";
        if (txFresh) txFresh.innerText = tx.freshness || "RECENT";

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

        // Update Chiller Card
        const chT = ch.telemetry || {};
        const chConn = document.getElementById("otChConn");
        const chSrc = document.getElementById("otChSrc");
        const chFresh = document.getElementById("otChFresh");
        if (chConn) chConn.innerText = ch.connection_status || "SIMULATED";
        if (chSrc) chSrc.innerText = ch.source || "mock_telemetry";
        if (chFresh) chFresh.innerText = ch.freshness || "RECENT";

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

        // Update Water Pump Card
        const wpT = wp.telemetry || {};
        const wpConn = document.getElementById("otWpConn");
        const wpSrc = document.getElementById("otWpSrc");
        const wpFresh = document.getElementById("otWpFresh");
        if (wpConn) wpConn.innerText = "DECISION SUPPORT";
        if (wpSrc) wpSrc.innerText = wp.source || "mock_telemetry";
        if (wpFresh) wpFresh.innerText = wp.freshness || "RECENT";

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

async function toggleTelemetryMode() {
    const targetMode = currentOTMode === "MOCK" ? "REAL_OT" : "MOCK";
    try {
        const res = await fetch(`${API_BASE_URL}/api/telemetry/mode`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: targetMode })
        });
        const result = await res.json();
        if (result.success) {
            currentOTMode = result.telemetry_mode;
            fetchOTStatus();
            fetchLiveOTTelemetry();
        }
    } catch (e) {
        console.error("Toggle Telemetry Mode Error:", e);
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
            currentOTScenario = scenarioName;
            updateCascadeNarrative(scenarioName);
            fetchLiveOTTelemetry();
            analyzeNextFleetSample();
        }
    } catch (e) {
        console.error("Set Telemetry Scenario Error:", e);
    }
}

function updateCascadeNarrative(scName) {
    const box = document.getElementById("otCascadeNarrative");
    if (!box) return;

    if (scName === "PUMP_DEGRADATION") {
        box.innerHTML = `<strong>PUMP DEGRADATION SCENARIO PROPAGATION:</strong> Industrial Water Pump cooling flow drops (~62 L/m) ➔ Reduced cooling water flow may increase Chiller condenser heat rejection stress (TCI ↑ to 36°C) ➔ Chiller COP efficiency degrades ➔ Elevated ambient/transformer oil temperature (OTI ↑) ➔ System Cascade Risk score increases (DECISION SUPPORT ESTIMATE).`;
    } else if (scName === "CHILLER_OVERLOAD") {
        box.innerHTML = `<strong>CHILLER OVERLOAD SCENARIO PROPAGATION:</strong> HVAC Chiller power consumption surges (310 kW) ➔ Condenser heat accumulation ➔ Downstream transformer thermal stress rises (WTI ↑) ➔ System Cascade Risk score increases.`;
    } else if (scName === "HEAT_STRESS") {
        box.innerHTML = `<strong>HEAT STRESS SCENARIO PROPAGATION:</strong> Ambient temperature surge (>43°C) ➔ Increased ambient thermal dissipation resistance across Transformer top-oil and Chiller condenser coils ➔ System Cascade Risk score increases.`;
    } else if (scName === "COMBINED_CASCADE") {
        box.innerHTML = `<strong>COMBINED CASCADE SCENARIO PROPAGATION:</strong> Compound multi-asset failure combining Water Pump flow degradation, HVAC Chiller thermal overload, ambient heatwave, and Transformer winding overload ➔ System Cascade Risk escalates to CRITICAL state.`;
    } else {
        box.innerText = `Active Scenario '${scName}': Monitoring live OT / simulated telemetry stream across Transformer, Chiller, Water Pump, and Climate Risk Engine.`;
    }
}

function startLiveOTStream() {
    if (liveOTStreamInterval) clearInterval(liveOTStreamInterval);
    fetchLiveOTTelemetry();
    liveOTStreamInterval = setInterval(() => {
        fetchLiveOTTelemetry();
    }, 2500);
}

function stopLiveOTStream() {
    if (liveOTStreamInterval) {
        clearInterval(liveOTStreamInterval);
        liveOTStreamInterval = null;
    }
}

function refreshLiveOTTelemetry() {
    fetchLiveOTTelemetry();
}


/* PHASE 13: INCIDENT INTELLIGENCE & REPORTING FRONTEND LOGIC */

async function fetchIncidents() {
    try {
        const res = await fetch(`${API_BASE_URL}/api/incidents`);
        const result = await res.json();
        if (!result.success || !result.data) return;

        const data = result.data;
        const activeList = data.active_incidents || [];
        const historyList = data.history || [];

        // KPI Counts
        const activeCount = activeList.length;
        const critCount = activeList.filter(i => i.severity === "CRITICAL").length;

        const activeElem = document.getElementById("incKpiActive");
        const critElem = document.getElementById("incKpiCritical");
        if (activeElem) activeElem.innerText = activeCount;
        if (critElem) critElem.innerText = critCount;

        // Update KPIs for System Risk & Vulnerable Asset if active incident exists
        if (activeList.length > 0) {
            const topInc = activeList[0];
            const sysElem = document.getElementById("incKpiSysRisk");
            const vulnElem = document.getElementById("incKpiVulnAsset");
            if (sysElem) sysElem.innerText = `${topInc.system_risk ? topInc.system_risk.toFixed(1) : '--'} / 100`;
            if (vulnElem) vulnElem.innerText = topInc.most_vulnerable_asset || '--';
        }

        // Banner update
        const banner = document.getElementById("incWarningBanner");
        const bIcon = document.getElementById("incBannerIcon");
        const bTitle = document.getElementById("incBannerTitle");
        const bSub = document.getElementById("incBannerSubtext");

        if (critCount > 0) {
            if (banner) banner.className = "inc-warning-banner inc-banner-critical";
            if (bIcon) bIcon.innerText = "🚨";
            if (bTitle) bTitle.innerText = "CRITICAL CASCADE RISK: Immediate engineering assessment recommended.";
            if (bSub) bSub.innerText = "Potential elevated multi-asset failure risk detected under climate stress conditions.";
        } else if (activeCount > 0) {
            if (banner) banner.className = "inc-warning-banner inc-banner-warning";
            if (bIcon) bIcon.innerText = "⚠";
            if (bTitle) bTitle.innerText = "WARNING: Infrastructure risk requires attention.";
            if (bSub) bSub.innerText = "Potential elevated risk detected across transformer, cooling, or climate conditions.";
        } else {
            if (banner) banner.className = "inc-warning-banner inc-banner-hidden";
        }

        // Incident Table Population
        const tbody = document.getElementById("incTableBody");
        if (!tbody) return;

        if (historyList.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #6a8c80;">No active incidents. Infrastructure operating within normal baseline limits.</td></tr>`;
            return;
        }

        let html = "";
        historyList.slice(0, 10).forEach(inc => {
            const sevColor = inc.severity === "CRITICAL" ? "#ff4d4d" : (inc.severity === "WARNING" ? "#ffb703" : "#70e000");
            const statColor = inc.status === "RESOLVED" ? "#6a8c80" : (inc.status === "ACKNOWLEDGED" ? "#ffb703" : "#ff4d4d");
            
            html += `
                <tr>
                    <td><strong>${inc.incident_id}</strong></td>
                    <td><span style="color: ${sevColor}; font-weight: 800;">${inc.severity}</span></td>
                    <td>${inc.timestamp}</td>
                    <td><strong>${inc.system_risk !== undefined ? inc.system_risk.toFixed(1) : '--'} / 100</strong></td>
                    <td><span class="prov-badge live-weather">${inc.most_vulnerable_asset || '--'}</span></td>
                    <td style="max-width: 200px; font-size: 0.7rem; color: #a0b8b0;">${inc.trigger || '--'}</td>
                    <td><span style="color: ${statColor}; font-weight: 800;">${inc.status}</span></td>
                    <td>
                        ${inc.status === "OPEN" ? `<button class="btn-inc-ack" onclick="acknowledgeIncident('${inc.incident_id}')">ACK</button>` : ''}
                        ${inc.status !== "RESOLVED" ? `<button class="btn-inc-res" onclick="resolveIncident('${inc.incident_id}')">RESOLVE</button>` : ''}
                        <button class="btn-ot-scen" style="margin-left:4px; padding:2px 6px; font-size:0.65rem;" onclick="triggerPDFReportDownload('${inc.incident_id}')">PDF</button>
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
            alert("Failed to generate PDF incident report.");
            return;
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `CascadeGuard_Incident_${incId || 'Report'}.pdf`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        console.error("Trigger PDF Download Error:", e);
    }
}


/* PHASE 14: REGIONAL MULTI-SITE COMMAND CENTER FRONTEND LOGIC */

let regionalMapInstance = null;
let regionalMarkers = {};

function initRegionalMap() {
    const mapElem = document.getElementById("regionalMap");
    if (!mapElem || regionalMapInstance) return;

    try {
        regionalMapInstance = L.map("regionalMap").setView([11.5, 78.5], 7);

        L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
            maxZoom: 18,
            attribution: "© OpenStreetMap contributors | CascadeGuard Regional Command"
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

        // Update Regional KPIs
        const monElem = document.getElementById("regKpiMonitored");
        const critElem = document.getElementById("regKpiCritical");
        const warnElem = document.getElementById("regKpiWarning");
        const riskElem = document.getElementById("regKpiRisk");
        const vulnElem = document.getElementById("regKpiVulnSite");

        if (monElem) monElem.innerText = reg.sites_monitored;
        if (critElem) critElem.innerText = reg.critical_sites;
        if (warnElem) warnElem.innerText = reg.warning_sites;
        if (riskElem) riskElem.innerText = `${reg.regional_risk.toFixed(1)} / 100`;

        const mv = reg.most_vulnerable_site || {};
        if (vulnElem) vulnElem.innerText = mv.site_name || '--';

        // Regional Alert Banner update
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

        // Most Vulnerable Highlight Card update
        const mvName = document.getElementById("mvSiteName");
        const mvId = document.getElementById("mvSiteId");
        const mvRisk = document.getElementById("mvRiskNum");
        const mvDesc = document.getElementById("mvVulnDesc");

        if (mvName) mvName.innerText = mv.site_name || "Coimbatore Industrial Facility";
        if (mvId) mvId.innerText = mv.site_id || "SITE-001";
        if (mvRisk) mvRisk.innerText = mv.system_cascade_risk ? mv.system_cascade_risk.toFixed(1) : "0.0";
        if (mvDesc) mvDesc.innerHTML = `Primary Vulnerability: <strong>${mv.vulnerable_asset || 'CHILLER'}</strong> | Status: <strong>${mv.level || 'NORMAL'}</strong>`;

        // Update Leaflet Markers
        if (regionalMapInstance) {
            sites.forEach(s => {
                const color = s.level === "CRITICAL" ? "#ff4d4d" : (s.level === "WARNING" ? "#ffb703" : "#70e000");
                const popupContent = `
                    <div style="font-family: sans-serif; font-size: 0.8rem;">
                        <strong style="color: #051410;">${s.site_name} (${s.site_id})</strong><br/>
                        <b>Cascade Risk:</b> ${s.system_cascade_risk.toFixed(1)} / 100<br/>
                        <b>Status:</b> <span style="color: ${color}; font-weight:800;">${s.level}</span><br/>
                        <b>Vulnerability:</b> ${s.most_vulnerable_asset}<br/>
                        <b>Climate Stress:</b> ${s.climate_stress.toFixed(1)}
                    </div>
                `;

                if (regionalMarkers[s.site_id]) {
                    regionalMarkers[s.site_id].setPopupContent(popupContent);
                } else {
                    const marker = L.circleMarker([s.latitude, s.longitude], {
                        color: color,
                        fillColor: color,
                        fillOpacity: 0.8,
                        radius: 10
                    }).addTo(regionalMapInstance);
                    marker.bindPopup(popupContent);
                    regionalMarkers[s.site_id] = marker;
                }
            });
        }

        // Populate Site Cards Grid
        const gridElem = document.getElementById("siteCardsGrid");
        if (gridElem) {
            let gridHtml = "";
            sites.forEach(s => {
                const sColor = s.level === "CRITICAL" ? "#ff4d4d" : (s.level === "WARNING" ? "#ffb703" : "#70e000");
                gridHtml += `
                    <div class="site-card" onclick="handleSiteSelection('${s.site_id}')">
                        <div class="site-card-header">
                            <span class="site-card-title">${s.city}</span>
                            <span class="prov-badge live-weather" style="font-size:0.6rem;">${s.site_id}</span>
                        </div>
                        <div class="site-card-score" style="color: ${sColor}">${s.system_cascade_risk.toFixed(1)}</div>
                        <div class="site-card-sub">STATUS: <strong style="color:${sColor}">${s.level}</strong></div>
                        <div style="margin-top:6px; font-size:0.65rem; color:#a0b8b0;">
                            Tx: ${s.transformer_risk.toFixed(1)} | Ch: ${s.chiller_risk.toFixed(1)} | P: ${s.water_pump_risk.toFixed(1)}
                        </div>
                    </div>
                `;
            });
            gridElem.innerHTML = gridHtml;
        }

        // Populate Site Comparison Table Body
        const compBody = document.getElementById("siteComparisonTableBody");
        if (compBody) {
            let compHtml = "";
            sites.forEach(s => {
                const cColor = s.level === "CRITICAL" ? "#ff4d4d" : (s.level === "WARNING" ? "#ffb703" : "#70e000");
                compHtml += `
                    <tr>
                        <td><strong>#${s.priority_rank}</strong></td>
                        <td><strong>${s.site_name}</strong> (${s.site_id})</td>
                        <td>${s.city}</td>
                        <td><strong style="color:${cColor}">${s.system_cascade_risk.toFixed(1)} / 100</strong></td>
                        <td><span style="color:${cColor}; font-weight:800;">${s.level}</span></td>
                        <td>${s.transformer_risk.toFixed(1)}</td>
                        <td>${s.chiller_risk.toFixed(1)}</td>
                        <td>${s.water_pump_risk.toFixed(1)}</td>
                        <td>${s.climate_stress.toFixed(1)}</td>
                        <td><span class="prov-badge live-weather">${s.most_vulnerable_asset}</span></td>
                        <td><span class="prov-badge pred-sim">${s.data_quality}</span></td>
                        <td><button class="btn-ot-scen" onclick="handleSiteSelection('${s.site_id}')">VIEW SITE</button></td>
                    </tr>
                `;
            });
            compBody.innerHTML = compHtml;
        }

    } catch (e) {
        console.error("Fetch Regional Status Error:", e);
    }
}

function handleSiteSelection(siteId) {
    if (siteId === "ALL") {
        fetchRegionalStatus();
    } else {
        // Trigger single site configuration & analysis
        fetch(`${API_BASE_URL}/api/sites/${siteId}/analyze`)
            .then(res => res.json())
            .then(data => {
                if (data.success && data.site) {
                    // Update header site banner
                    const sName = document.getElementById("hdrSiteName");
                    const sId = document.getElementById("hdrSiteId");
                    if (sName) sName.innerText = data.site.site_name;
                    if (sId) sId.innerText = data.site.site_id;
                    alert(`Switched Command Center Focus to ${data.site.site_name} (${data.site.site_id}).`);
                }
            })
            .catch(err => console.error("Site selection error:", err));
    }
}


// PHASE 15: HACKATHON DEMO MODE & GUIDED DEMO FLOW
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
                el.classList.add("active-step");
            } else {
                el.classList.remove("active-step");
            }
        }
    }
}

let isDemoRunning = false;

async function runOneClickDemoFlow() {
    if (isDemoRunning) return;
    isDemoRunning = true;
    
    const guidePanel = document.getElementById("demoGuidePanel");
    if (guidePanel) guidePanel.classList.remove("demo-guide-hidden");
    
    const btn = document.getElementById("btnOneClickDemo");
    if (btn) {
        btn.innerText = "⏳ DEMO IN PROGRESS...";
        btn.disabled = true;
    }

    try {
        // Step 1: NORMAL
        highlightDemoStep(1);
        await selectOTScenario("NORMAL");
        await new Promise(r => setTimeout(r, 2500));

        // Step 2: HEAT STRESS
        highlightDemoStep(2);
        await selectOTScenario("HEAT_STRESS");
        await new Promise(r => setTimeout(r, 3000));

        // Step 3: CHILLER OVERLOAD
        highlightDemoStep(3);
        await selectOTScenario("CHILLER_OVERLOAD");
        await new Promise(r => setTimeout(r, 3000));

        // Step 4: PUMP DEGRADATION
        highlightDemoStep(4);
        await selectOTScenario("PUMP_DEGRADATION");
        await new Promise(r => setTimeout(r, 3000));

        // Step 5 & 6: COMBINED CASCADE
        highlightDemoStep(5);
        await selectOTScenario("COMBINED_CASCADE");
        await new Promise(r => setTimeout(r, 3000));

        highlightDemoStep(6);
        await fetchIncidents();
        await new Promise(r => setTimeout(r, 2500));

        // Step 7: Incident Alert
        highlightDemoStep(7);
        await new Promise(r => setTimeout(r, 2500));

        // Step 8: PDF Report Ready
        highlightDemoStep(8);
        alert("🎉 HACKATHON DEMO FLOW COMPLETE! System Cascade Risk reached critical levels, generating dynamic SHAP XAI factors, automated incident alert webhook, and downloadable PDF report.");

    } catch (err) {
        console.error("Demo Flow Error:", err);
    } finally {
        isDemoRunning = false;
        if (btn) {
            btn.innerText = "🚀 START 1-CLICK DEMO";
            btn.disabled = false;
        }
    }
}


window.addEventListener("DOMContentLoaded", () => {
    fetchSiteConfig();
    analyzeNextFleetSample();
    runClimateScenario("NORMAL", null);
    fetchClimateIntelligence();
    fetchOTStatus();
    startLiveOTStream();
    fetchIncidents();
    setInterval(fetchIncidents, 4000);
    initRegionalMap();
    fetchRegionalStatus();
    setInterval(fetchRegionalStatus, 5000);
});