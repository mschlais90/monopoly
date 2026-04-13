// app.js - Main application logic for Monopoly web client
"use strict";

let sessionId = null;
let gameState = null;
let boardSpaces = [];
let autoRunning = false;
let autoTimer = null;
let lastDice = null;

const settings = { showDice: true, animate: true };
const SPEED_DELAYS = { 1: 2000, 2: 1000, 3: 500, 4: 200, 5: 50 };
const PLAYER_COLORS = ["#E74C3C", "#3498DB", "#2ECC71", "#F39C12"];

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
            const overrides = {};
            overrides[moved.name] = path[step];
            drawBoard(
                document.getElementById("board-canvas").getContext("2d"),
                boardSpaces, gameState.board, gameState.players,
                gameState.free_parking_pot,
                settings.showDice ? lastDice : null,
                overrides
            );
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
    const ctx = canvas.getContext("2d");
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
            propsHtml = p.properties.map(pr => {
                const c = pr.color ? COLOR_HEX[pr.color] || "#888" : "#aaa";
                const h = pr.houses === 5 ? " H" : pr.houses > 0 ? " " + pr.houses + "h" : "";
                const mg = pr.mortgaged ? " [M]" : "";
                return `<span style="color:${c}">${pr.name}${h}${mg}</span>`;
            }).join("");
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

// ── Log ──────────────────────────────────────────────────────────────────────

function appendLog(lines) {
    if (!lines || !lines.length) return;
    const el = document.getElementById("log-content");
    for (const line of lines) {
        const div = document.createElement("div");
        div.textContent = line;
        if (line.startsWith("===")) div.className = "log-turn";
        else if (line.includes("bought")) div.className = "log-buy";
        else if (line.includes("rent") || line.includes("owes")) div.className = "log-rent";
        else if (line.includes("jail") || line.includes("Jail")) div.className = "log-jail";
        else if (line.includes("CHANCE") || line.includes("COMM.")) div.className = "log-card";
        else if (line.includes("built") || line.includes("house") || line.includes("hotel")) div.className = "log-build";
        else if (line.includes("TRADE")) div.className = "log-trade";
        else if (line.includes("BANKRUPT")) div.className = "log-bankrupt";
        el.appendChild(div);
    }
    el.scrollTop = el.scrollHeight;
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
                    actionsHtml += `<button style="background:#2980B9"
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
