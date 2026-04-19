// app.js - Main application logic for Monopoly web client
"use strict";

let sessionId = null;
let gameState = null;
let boardSpaces = [];
let colorGroups = {};
let autoRunning = false;
let autoTimer = null;
let lastDice = null;

const settings = { showDice: true, animate: true };
const SPEED_DELAYS = { 1: 2000, 2: 1000, 3: 500, 4: 200, 5: 50 };
const PLAYER_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12"];

function setupCanvas(canvas) {
    const dpr = window.devicePixelRatio || 1;
    // Use container width on small screens, otherwise default 640
    const container = canvas.parentElement;
    const maxW = container ? container.clientWidth : 640;
    const displaySize = Math.min(640, maxW);
    canvas.width = displaySize * dpr;
    canvas.height = displaySize * dpr;
    canvas.style.width = displaySize + "px";
    canvas.style.height = displaySize + "px";
    const ctx = canvas.getContext("2d");
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    const scale = (displaySize / 640) * dpr;
    ctx.scale(scale, scale);
    return ctx;
}

// ── API helpers ──────────────────────────────────────────────────────────────

async function api(path, body) {
    const resp = await fetch("/api" + path, {
        method: body ? "POST" : "GET",
        headers: body ? { "Content-Type": "application/json" } : {},
        body: body ? JSON.stringify(body) : undefined,
    });
    return resp.json();
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
    const data = await api("/constants");
    boardSpaces = data.board_spaces;
    colorGroups = data.color_groups || {};

    buildSetupRows(2);
    document.querySelectorAll("#player-count-row .radio-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelector("#player-count-row .selected").classList.remove("selected");
            btn.classList.add("selected");
            buildSetupRows(parseInt(btn.dataset.val));
        });
    });

    document.getElementById("btn-start").addEventListener("click", startGame);
    document.getElementById("btn-next").addEventListener("click", nextTurn);
    document.getElementById("btn-auto").addEventListener("click", toggleAuto);
    document.getElementById("btn-props").addEventListener("click", openPropsModal);
    document.getElementById("btn-trade").addEventListener("click", openTradeModal);
    document.getElementById("btn-save").addEventListener("click", saveGame);
    document.getElementById("btn-load-file").addEventListener("click", () => document.getElementById("load-file-input").click());
    document.getElementById("load-file-input").addEventListener("change", loadGame);
    document.getElementById("btn-new").addEventListener("click", () => { stopAuto(); showScreen("setup"); });
    document.getElementById("btn-menu").addEventListener("click", () => { stopAuto(); showScreen("setup"); });
    document.getElementById("btn-settings").addEventListener("click", () => {
        document.getElementById("setting-dice").checked = settings.showDice;
        document.getElementById("setting-animate").checked = settings.animate;
        document.getElementById("settings-overlay").classList.remove("hidden");
    });
    
    // Log filter event listeners
    document.getElementById("log-player-filter").addEventListener("change", renderLog);
    document.getElementById("log-type-filter").addEventListener("change", renderLog);
    document.getElementById("log-clear-btn").addEventListener("click", clearLog);

    // Redraw board on resize/orientation change (for mobile)
    let resizeTimer = null;
    window.addEventListener("resize", () => {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(() => { if (gameState) refreshBoard(); }, 150);
    });
});

function buildSetupRows(count) {
    const container = document.getElementById("player-rows");
    container.innerHTML = "";
    const names = ["Alice", "Bob", "Carol", "Dave"];
    const strats = ["Aggressive", "Conservative", "Balanced", "Random", "HyperAggressive", "Human"];
    for (let i = 0; i < count; i++) {
        const row = document.createElement("div");
        row.className = "player-row";
        row.innerHTML = `
            <div class="color-dot" style="background:${PLAYER_COLORS[i]}"></div>
            <input type="text" class="p-name" value="${names[i]}" placeholder="Name">
            <select class="p-strat">${strats.map(s => `<option value="${s}"${i===0?" selected":""}>${s}</option>`).join("")}</select>
        `;
        if (i === 0) row.querySelector("select").value = "Human";
        else row.querySelector("select").value = strats[i % strats.length];
        container.appendChild(row);
    }
}

function showScreen(name) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    document.getElementById(name + "-screen").classList.add("active");
}

// ── Settings ─────────────────────────────────────────────────────────────────

window.closeSettings = function() {
    settings.showDice = document.getElementById("setting-dice").checked;
    settings.animate = document.getElementById("setting-animate").checked;
    document.getElementById("settings-overlay").classList.add("hidden");
    if (gameState) refreshBoard();
};

// ── Start game ───────────────────────────────────────────────────────────────

async function startGame() {
    const rows = document.querySelectorAll("#player-rows .player-row");
    const players = [];
    rows.forEach((row, i) => {
        players.push({
            name: row.querySelector(".p-name").value || ("Player" + (i+1)),
            strategy: row.querySelector(".p-strat").value,
            color: PLAYER_COLORS[i],
        });
    });
    const money = parseInt(document.getElementById("starting-money").value) || 1500;
    const resp = await api("/new_game", { players, starting_money: money });
    if (resp.error) { alert(resp.error); return; }
    sessionId = resp.session_id;
    gameState = resp.state;
    lastDice = null;
    autoRunning = false;
    document.getElementById("log-content").innerHTML = "";
    showScreen("game");
    refreshUI();
}

// ── Turn processing ──────────────────────────────────────────────────────────

async function nextTurn() {
    if (!sessionId || (gameState && gameState.game_over)) return;
    document.getElementById("btn-next").disabled = true;

    const prePosMap = {};
    if (gameState) gameState.players.forEach(p => { if (!p.bankrupt) prePosMap[p.name] = p.position; });

    const resp = await api("/next_turn", { session_id: sessionId });
    if (resp.error) { alert(resp.error); document.getElementById("btn-next").disabled = false; return; }

    gameState = resp.state;
    extractDice(resp.log);
    appendLog(resp.log);

    const afterAnim = async () => {
        if (resp.pending) {
            await handlePending(resp.pending);
        }
        refreshUI();
        document.getElementById("btn-next").disabled = false;
        if (gameState.game_over) {
            showWinner();
        }
    };

    if (settings.animate) {
        await animateMovement(prePosMap, afterAnim);
    } else {
        await afterAnim();
    }
}

function extractDice(log) {
    for (let i = log.length - 1; i >= 0; i--) {
        const m = log[i].match(/Rolled (\d+)\+(\d+)=/);
        if (m) { lastDice = [parseInt(m[1]), parseInt(m[2])]; return; }
    }
}

async function handlePending(pending) {
    if (pending.type === "buy") {
        const choice = await showModal(
            "Buy Property?",
            `<p><b>${pending.property}</b> is available for <b>$${pending.price}</b></p>
             <p>Your cash: $${pending.cash}</p>`,
            [{ text: "Buy", value: true, cls: "btn-green" },
             { text: "Pass", value: false, cls: "btn-grey" }]
        );
        const resp = await api("/decide", { session_id: sessionId, type: "buy", choice });
        if (resp.log) appendLog(resp.log);
        gameState = resp.state;
    } else if (pending.type === "trade") {
        const offeredProps = pending.offered_props.map(p => p.name).join(", ") || "nothing";
        const requestedProps = pending.requested_props.map(p => p.name).join(", ") || "nothing";
        const netInfo = pending.recipient_net > 0 
            ? `<p style="color:#4CAF50">Fair value: +$${Math.round(pending.recipient_net)} in your favor</p>`
            : pending.recipient_net < 0
            ? `<p style="color:#FF7043">Fair value: -$${Math.round(-pending.recipient_net)} against you</p>`
            : `<p style="color:#FFD700">Fair value: Even trade</p>`;
        
        const choice = await showModal(
            "Trade Offer",
            `<p><b>${pending.proposer}</b> offers you a trade:</p>
             <p><b>They offer:</b> ${offeredProps}${pending.offered_cash > 0 ? ` + $${pending.offered_cash}` : ""}</p>
             <p><b>You give:</b> ${requestedProps}${pending.requested_cash > 0 ? ` + $${pending.requested_cash}` : ""}</p>
             ${netInfo}`,
            [{ text: "Accept", value: true, cls: "btn-green" },
             { text: "Decline", value: false, cls: "btn-grey" }]
        );
        const resp = await api("/decide", { session_id: sessionId, type: "trade", choice });
        if (resp.log) appendLog(resp.log);
        gameState = resp.state;
    }
}

function showWinner() {
    showModal("Game Over!",
        gameState.winner
            ? `<p style="font-size:24px;text-align:center;color:#FFD700">${gameState.winner} wins!</p>`
            : `<p>No winner — turn limit reached.</p>`,
        [{ text: "OK", value: true, cls: "btn-green" }]
    );
}

// ── Animation ────────────────────────────────────────────────────────────────

function animateMovement(prePosMap, callback) {
    return new Promise(resolve => {
        let moved = null;
        for (const p of gameState.players) {
            if (p.bankrupt) continue;
            const old = prePosMap[p.name];
            if (old !== undefined && old !== p.position) {
                moved = { name: p.name, from: old, to: p.position };
                break;
            }
        }
        if (!moved || (moved.to === 10 && moved.from === 30)) {
            callback().then(resolve);
            return;
        }

        const path = [];
        let pos = moved.from;
        while (pos !== moved.to) {
            pos = (pos + 1) % 40;
            path.push(pos);
            if (path.length > 40) break;
        }
        if (!path.length) { callback().then(resolve); return; }

        const delays = easeDelays(path.length, 2000);
        let step = 0;

        function tick() {
            if (step >= path.length) {
                callback().then(resolve);
                return;
            }
            const canvas = document.getElementById("board-canvas");
            const ctx = setupCanvas(canvas);
            const overrides = {};
            overrides[moved.name] = path[step];
            drawBoard(ctx, boardSpaces, gameState.board, gameState.players,
                      gameState.free_parking_pot,
                      settings.showDice ? lastDice : null, overrides);
            step++;
            setTimeout(tick, delays[step - 1]);
        }
        tick();
    });
}

function easeDelays(n, totalMs) {
    if (n <= 0) return [];
    if (n === 1) return [Math.min(totalMs, 400)];
    const eps = 0.15;
    const speeds = [];
    for (let i = 0; i < n; i++) speeds.push(Math.sin(Math.PI * i / (n - 1)) + eps);
    const maxS = Math.max(...speeds);
    const raw = speeds.map(s => maxS / s);
    const total = raw.reduce((a, b) => a + b, 0);
    return raw.map(d => Math.max(20, Math.round(d / total * totalMs)));
}

// ── Auto run ─────────────────────────────────────────────────────────────────

function toggleAuto() {
    if (autoRunning) stopAuto();
    else startAuto();
}

function startAuto() {
    autoRunning = true;
    document.getElementById("btn-auto").textContent = "Pause";
    runAutoStep();
}

function stopAuto() {
    autoRunning = false;
    if (autoTimer) { clearTimeout(autoTimer); autoTimer = null; }
    document.getElementById("btn-auto").textContent = "Auto Run";
}

async function runAutoStep() {
    if (!autoRunning || !sessionId) return;
    if (gameState && gameState.game_over) { stopAuto(); showWinner(); return; }

    const speed = parseInt(document.getElementById("speed-slider").value) || 3;

    // Check if next player is human
    const currentP = gameState.players.find(p => p.name === gameState.current_player);
    if (currentP && currentP.strategy === "Human") {
        // Process human turn with next_turn (shows pending dialog)
        await nextTurn();
        if (!autoRunning) return;
        autoTimer = setTimeout(runAutoStep, SPEED_DELAYS[speed]);
        return;
    }

    // AI turns: batch up to speed-based count
    const count = speed >= 4 ? 10 : 1;
    const prePosMap = {};
    gameState.players.forEach(p => { if (!p.bankrupt) prePosMap[p.name] = p.position; });

    const resp = await api("/auto_turns", { session_id: sessionId, count });
    if (resp.error) { stopAuto(); return; }
    gameState = resp.state;
    extractDice(resp.log);
    appendLog(resp.log);

    const doAnimate = settings.animate && speed <= 3 && count === 1;

    const afterAnim = async () => {
        refreshUI();
        if (gameState.game_over) { stopAuto(); showWinner(); return; }
        if (resp.human_next && autoRunning) {
            // Next is human — run their turn via nextTurn which shows dialogs
            await nextTurn();
        }
        if (autoRunning) {
            autoTimer = setTimeout(runAutoStep, SPEED_DELAYS[speed]);
        }
    };

    if (doAnimate) {
        await animateMovement(prePosMap, afterAnim);
    } else {
        await afterAnim();
    }
}

// ── UI refresh ───────────────────────────────────────────────────────────────

function refreshUI() {
    if (!gameState) return;
    refreshBoard();
    refreshPlayers();
    refreshUnowned();
    updatePlayerFilter();
    document.getElementById("turn-label").textContent = "Turn: " + gameState.turn;
    const cp = gameState.players.find(p => p.name === gameState.current_player);
    const lbl = document.getElementById("current-player-label");
    if (gameState.game_over) {
        lbl.textContent = gameState.winner ? "WINNER: " + gameState.winner + "!" : "Game Over";
        lbl.style.color = "#FFD700";
    } else if (cp) {
        lbl.textContent = "Next: " + cp.name;
        lbl.style.color = cp.color;
    }
}

function refreshBoard() {
    const canvas = document.getElementById("board-canvas");
    const ctx = setupCanvas(canvas);
    drawBoard(ctx, boardSpaces, gameState.board, gameState.players,
              gameState.free_parking_pot, settings.showDice ? lastDice : null, null);
}

function refreshPlayers() {
    const container = document.getElementById("player-panels");
    container.innerHTML = "";
    for (const p of gameState.players) {
        const div = document.createElement("div");
        div.className = "player-panel" + (p.bankrupt ? " bankrupt" : "");
        div.style.borderLeftColor = p.color;
        let propsHtml = "";
        if (p.properties.length) {
            // Group properties by color
            const grouped = {};
            for (const pr of p.properties) {
                const colorKey = pr.color || "other";
                if (!grouped[colorKey]) grouped[colorKey] = [];
                grouped[colorKey].push(pr);
            }
            
            // Sort color groups by first property position
            const sortedColors = Object.keys(grouped).sort((a, b) => {
                const aMin = Math.min(...grouped[a].map(pr => pr.pos));
                const bMin = Math.min(...grouped[b].map(pr => pr.pos));
                return aMin - bMin;
            });
            
            const parts = [];
            for (const colorKey of sortedColors) {
                const props = grouped[colorKey];
                const c = colorKey !== "other" ? COLOR_HEX[colorKey] || "#888" : "#aaa";
                const propStrs = props.map(pr => {
                    const h = pr.houses === 5 ? " H" : pr.houses > 0 ? " " + pr.houses + "h" : "";
                    const mg = pr.mortgaged ? " [M]" : "";
                    return `${pr.name}${h}${mg}`;
                });
                parts.push(`<span style="color:${c}">■ ${propStrs.join(", ")}</span>`);
            }
            propsHtml = parts.join("<br>");
        }
        div.innerHTML = `
            <div class="pp-name" style="color:${p.color}">${p.name} ${p.bankrupt ? "(BANKRUPT)" : ""}</div>
            <div class="pp-stats">Cash: $${p.money.toLocaleString()} | Net Worth: $${p.net_worth.toLocaleString()} | Pos: ${p.position}${p.in_jail ? " (JAIL)" : ""}</div>
            <div class="pp-props">${propsHtml || "<i>No properties</i>"}</div>
        `;
        container.appendChild(div);
    }
}

function refreshUnowned() {
    const list = document.getElementById("unowned-list");
    const countEl = document.getElementById("unowned-count");
    let html = "";
    let count = 0;
    for (const sp of boardSpaces) {
        if (!["property", "railroad", "utility"].includes(sp.type)) continue;
        const bs = gameState.board[String(sp.pos)];
        if (bs && bs.owner) continue;
        count++;
        const c = sp.color ? COLOR_HEX[sp.color] || "#888" : "#aaa";
        html += `<div class="unowned-item"><span class="swatch" style="background:${c}"></span>${sp.name} — $${sp.price}</div>`;
    }
    list.innerHTML = html || "<div style='padding:8px;color:#666'>All properties owned!</div>";
    countEl.textContent = `(${count})`;
}

// ── Log with filtering ───────────────────────────────────────────────────────

let logMessages = [];
let currentTurnPlayer = null;

function classifyLogType(msg) {
    const m = msg.toLowerCase();
    if (msg.startsWith("===")) return "Turn Header";
    if (m.includes("rolled") || m.includes("moves to") || m.includes("passed go") || m.includes("escaped jail")) return "Movement";
    if (m.includes("bought") || m.includes("passed on") || m.includes("unowned") || m.includes("buy")) return "Purchase";
    if (m.includes("rent") || m.includes("owes")) return "Rent";
    if (m.includes("chance") || m.includes("comm. chest") || m.includes("collected") || m.includes("advanced to")) return "Cards";
    if (m.includes("jail")) return "Jail";
    if (m.includes("built") || m.includes("house") || m.includes("hotel") || m.includes("mortgag")) return "Building";
    if (m.includes("bankrupt")) return "Bankruptcy";
    return "Other";
}

function pickLogClass(msg) {
    const m = msg.toLowerCase();
    if (msg.startsWith("===")) return "log-turn";
    if (m.includes("bought")) return "log-buy";
    if (m.includes("rent") || m.includes("owes")) return "log-rent";
    if (m.includes("jail")) return "log-jail";
    if (m.includes("chance") || m.includes("chest")) return "log-card";
    if (m.includes("built") || m.includes("house") || m.includes("hotel")) return "log-build";
    if (m.includes("trade")) return "log-trade";
    if (m.includes("bankrupt")) return "log-bankrupt";
    return "";
}

function extractTurnPlayer(msg) {
    const match = msg.match(/^=== Turn \d+: (.+?) \(/);
    if (match) currentTurnPlayer = match[1];
}

function appendLog(lines) {
    if (!lines || !lines.length) return;
    for (const line of lines) {
        extractTurnPlayer(line);
        const player = currentTurnPlayer || "System";
        const type = classifyLogType(line);
        logMessages.push({text: line, player, type});
    }
    renderLog();
}

function renderLog() {
    const el = document.getElementById("log-content");
    const playerFilter = document.getElementById("log-player-filter").value;
    const typeFilter = document.getElementById("log-type-filter").value;
    
    el.innerHTML = "";
    for (const msg of logMessages) {
        if (playerFilter !== "All" && msg.player !== playerFilter) continue;
        if (typeFilter !== "All" && msg.type !== typeFilter) continue;
        
        const div = document.createElement("div");
        div.textContent = msg.text;
        div.className = pickLogClass(msg.text);
        el.appendChild(div);
    }
    el.scrollTop = el.scrollHeight;
}

function clearLog() {
    logMessages = [];
    currentTurnPlayer = null;
    renderLog();
}

function updatePlayerFilter() {
    if (!gameState) return;
    const select = document.getElementById("log-player-filter");
    const current = select.value;
    select.innerHTML = '<option value="All">All</option>';
    for (const p of gameState.players) {
        const opt = document.createElement("option");
        opt.value = p.name;
        opt.textContent = p.name;
        select.appendChild(opt);
    }
    if (current && Array.from(select.options).some(o => o.value === current)) {
        select.value = current;
    }
}

// ── Modal helper ─────────────────────────────────────────────────────────────

function showModal(title, bodyHtml, buttons) {
    return new Promise(resolve => {
        document.getElementById("modal-title").textContent = title;
        document.getElementById("modal-body").innerHTML = bodyHtml;
        const btns = document.getElementById("modal-btns");
        btns.innerHTML = "";
        for (const b of buttons) {
            const btn = document.createElement("button");
            btn.className = "btn " + (b.cls || "btn-grey");
            btn.textContent = b.text;
            btn.addEventListener("click", () => {
                document.getElementById("modal-overlay").classList.add("hidden");
                resolve(b.value);
            });
            btns.appendChild(btn);
        }
        document.getElementById("modal-overlay").classList.remove("hidden");
    });
}

// ── Properties Modal ─────────────────────────────────────────────────────────

let propsActiveTab = 0;

function openPropsModal() {
    const overlay = document.getElementById("props-overlay");
    overlay.classList.remove("hidden");
    buildPropsTabs();
}

window.closePropsModal = function() {
    document.getElementById("props-overlay").classList.add("hidden");
    refreshUI();
};

function buildPropsTabs() {
    const tabs = document.getElementById("props-tabs");
    tabs.innerHTML = "";
    const activePlayers = gameState.players.filter(p => !p.bankrupt);
    activePlayers.forEach((p, i) => {
        const btn = document.createElement("button");
        btn.className = "tab-btn" + (i === propsActiveTab ? " active" : "");
        btn.textContent = p.name;
        btn.style.borderBottom = "3px solid " + p.color;
        btn.addEventListener("click", () => { propsActiveTab = i; buildPropsTabs(); });
        tabs.appendChild(btn);
    });
    if (propsActiveTab >= activePlayers.length) propsActiveTab = 0;
    buildPropsBody(activePlayers[propsActiveTab]);
}

function hasFullColorSet(player, color) {
    if (!color) return false;
    const groupPositions = colorGroups[color];
    if (!groupPositions) return false;
    return groupPositions.every(pos => {
        const prop = gameState.board[String(pos)];
        return prop && prop.owner === player.name;
    });
}
function buildPropsBody(player) {
    const body = document.getElementById("props-body");
    body.innerHTML = "";
    if (!player.properties.length) {
        body.innerHTML = "<div style='padding:16px;color:#666'>No properties owned.</div>";
        return;
    }
    const isHuman = player.strategy === "Human";
    for (const prop of player.properties) {
        const row = document.createElement("div");
        row.className = "prop-row";
        const c = prop.color ? COLOR_HEX[prop.color] || "#888" : "#aaa";

        let status, statusColor;
        if (prop.mortgaged) { status = "MORTGAGED"; statusColor = "#FF7043"; }
        else if (prop.houses === 5) { status = "Hotel"; statusColor = "#E74C3C"; }
        else if (prop.houses > 0) { status = prop.houses + " House" + (prop.houses > 1 ? "s" : ""); statusColor = "#4CAF50"; }
        else { status = "No houses"; statusColor = "#888"; }

        let actionsHtml = "";
        if (isHuman) {
            if (prop.mortgaged) {
                const canUn = player.money >= prop.unmortgage_cost;
                actionsHtml += `<button style="background:${canUn?'#27AE60':'#444'}" ${canUn?"":"disabled"}
                    onclick="doUnmortgage('${player.name}',${prop.pos})">Unmortgage $${prop.unmortgage_cost}</button>`;
            } else {
                actionsHtml += `<button style="background:#c0392b" onclick="doMortgage('${player.name}',${prop.pos})">Mortgage</button>`;
                if (prop.type === "property" && prop.houses < 5) {
                    const ownsFullSet = hasFullColorSet(player, prop.color);
                    const canBuy = ownsFullSet && player.money >= prop.house_cost;
                    actionsHtml += `<button style="background:${canBuy?'#2980B9':'#444'}" ${canBuy?"":"disabled"}
                        onclick="doBuyHouse('${player.name}',${prop.pos})">+${prop.houses===4?"Hotel":"House"} $${prop.house_cost}</button>`;
                }
            }
        }

        row.innerHTML = `
            <div class="color-swatch" style="background:${c}"></div>
            <div class="prop-name">${prop.name}</div>
            <div class="prop-status" style="color:${statusColor}">${status}</div>
            <div class="prop-rent">$${prop.price}</div>
            <div class="prop-actions">${actionsHtml}</div>
        `;
        body.appendChild(row);
    }
}

window.doMortgage = async function(playerName, pos) {
    const resp = await api("/mortgage", { session_id: sessionId, player: playerName, pos });
    if (resp.error) { alert(resp.error); return; }
    gameState = resp.state;
    if (resp.log) appendLog(resp.log);
    buildPropsTabs();
    refreshUI();
};

window.doUnmortgage = async function(playerName, pos) {
    const resp = await api("/unmortgage", { session_id: sessionId, player: playerName, pos });
    if (resp.error) { alert(resp.error); return; }
    gameState = resp.state;
    if (resp.log) appendLog(resp.log);
    buildPropsTabs();
    refreshUI();
};

window.doBuyHouse = async function(playerName, pos) {
    const resp = await api("/buy_house", { session_id: sessionId, player: playerName, pos });
    if (resp.error) { alert(resp.error); return; }
    gameState = resp.state;
    if (resp.log) appendLog(resp.log);
    buildPropsTabs();
    refreshUI();
};

// ── Save / Load ──────────────────────────────────────────────────────────────


// ── Trade ────────────────────────────────────────────────────────────────────

function openTradeModal() {
    if (!gameState) return;
    const humanPlayer = gameState.players.find(p => p.strategy === "Human" && !p.bankrupt);
    if (!humanPlayer) {
        alert("No human player in game");
        return;
    }
    
    // Populate recipient dropdown
    const recipientSelect = document.getElementById("trade-recipient");
    recipientSelect.innerHTML = '<option value="">Select player...</option>';
    for (const p of gameState.players) {
        if (p.name !== humanPlayer.name && !p.bankrupt) {
            const opt = document.createElement("option");
            opt.value = p.name;
            opt.textContent = p.name;
            recipientSelect.appendChild(opt);
        }
    }
    
    // Populate property lists
    populateTradeProps("trade-offer-props", humanPlayer.properties);
    
    document.getElementById("trade-offer-cash").value = "0";
    document.getElementById("trade-request-cash").value = "0";
    document.getElementById("trade-request-props").innerHTML = "";
    document.getElementById("trade-fairness").textContent = "";
    document.getElementById("trade-overlay").classList.remove("hidden");
}

window.closeTradeModal = function() {
    document.getElementById("trade-overlay").classList.add("hidden");
};

function populateTradeProps(containerId, properties) {
    const container = document.getElementById(containerId);
    container.innerHTML = "";
    if (!properties || properties.length === 0) {
        container.innerHTML = '<div style="padding: 8px; color: #666; font-size: 11px;">No properties</div>';
        return;
    }
    for (const prop of properties) {
        const item = document.createElement("div");
        item.className = "trade-prop-item";
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.value = prop.pos;
        const colorHex = prop.color ? COLOR_HEX[prop.color] || "#888" : "#aaa";
        const swatch = document.createElement("span");
        swatch.className = "trade-prop-swatch";
        swatch.style.backgroundColor = colorHex;
        const label = document.createElement("span");
        label.textContent = prop.name;
        item.appendChild(cb);
        item.appendChild(swatch);
        item.appendChild(label);
        item.addEventListener("click", (e) => {
            if (e.target !== cb) cb.checked = !cb.checked;
        });
        container.appendChild(item);
    }
}

window.proposeTrade = async function() {
    if (!gameState) return;
    const humanPlayer = gameState.players.find(p => p.strategy === "Human" && !p.bankrupt);
    if (!humanPlayer) return;
    
    const recipientName = document.getElementById("trade-recipient").value;
    if (!recipientName) {
        alert("Please select a player to trade with");
        return;
    }
    
    const offeredPositions = Array.from(document.querySelectorAll("#trade-offer-props input:checked")).map(cb => parseInt(cb.value));
    const offeredCash = parseInt(document.getElementById("trade-offer-cash").value) || 0;
    const requestedPositions = Array.from(document.querySelectorAll("#trade-request-props input:checked")).map(cb => parseInt(cb.value));
    const requestedCash = parseInt(document.getElementById("trade-request-cash").value) || 0;
    
    if (offeredPositions.length === 0 && offeredCash === 0 && requestedPositions.length === 0 && requestedCash === 0) {
        alert("Trade must include at least one item");
        return;
    }
    
    const resp = await api("/propose_trade", {
        session_id: sessionId,
        proposer_name: humanPlayer.name,
        recipient_name: recipientName,
        offered_prop_positions: offeredPositions,
        offered_cash: offeredCash,
        requested_prop_positions: requestedPositions,
        requested_cash: requestedCash
    });
    
    if (resp.error) {
        alert(resp.error);
        return;
    }
    
    if (resp.log) appendLog(resp.log);
    gameState = resp.state;
    refreshUI();
    closeTradeModal();
};

document.getElementById("trade-recipient").addEventListener("change", function() {
    if (!gameState) return;
    const recipientName = this.value;
    if (!recipientName) {
        document.getElementById("trade-request-props").innerHTML = "";
        return;
    }
    const recipient = gameState.players.find(p => p.name === recipientName);
    if (recipient) {
        populateTradeProps("trade-request-props", recipient.properties);
    }
});

async function saveGame() {
    if (!sessionId) return;
    const resp = await api("/save", { session_id: sessionId });
    if (resp.error) { alert(resp.error); return; }
    const blob = new Blob([JSON.stringify(resp, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "monopoly_save.json";
    a.click();
    URL.revokeObjectURL(a.href);
}

async function loadGame(event) {
    const file = event.target.files[0];
    if (!file) return;
    const text = await file.text();
    let saveData;
    try { saveData = JSON.parse(text); } catch { alert("Invalid save file"); return; }
    const resp = await api("/load", { save_data: saveData });
    if (resp.error) { alert(resp.error); return; }
    sessionId = resp.session_id;
    gameState = resp.state;
    lastDice = null;
    document.getElementById("log-content").innerHTML = "";
    appendLog(["=== Game loaded from save file ==="]);
    showScreen("game");
    refreshUI();
    event.target.value = "";
}









