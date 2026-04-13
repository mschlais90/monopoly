// board.js - Canvas-based Monopoly board renderer
"use strict";

const BOARD_SIZE = 640;
const CORNER = 80;
const SIDE_W = 48;  // width of non-corner squares along the edge
const SIDE_COUNT = 9;

const COLOR_HEX = {
    brown: "#8B4513", light_blue: "#87CEEB", pink: "#FF69B4",
    orange: "#FFA500", red: "#FF4444", yellow: "#FFD700",
    green: "#228B22", dark_blue: "#00008B"
};

const ABBREV = {
    0:"GO",1:"Mediterranean\nAve",2:"Community\nChest",3:"Baltic\nAve",
    4:"Income\nTax",5:"Reading\nRR",6:"Oriental\nAve",7:"Chance",
    8:"Vermont\nAve",9:"Connecticut\nAve",10:"JAIL\nVisiting",
    11:"St.Charles\nPlace",12:"Electric\nCo.",13:"States\nAve",
    14:"Virginia\nAve",15:"Penn.\nRR",16:"St.James\nPlace",
    17:"Community\nChest",18:"Tennessee\nAve",19:"New York\nAve",
    20:"FREE\nPARKING",21:"Kentucky\nAve",22:"Chance",23:"Indiana\nAve",
    24:"Illinois\nAve",25:"B&O\nRR",26:"Atlantic\nAve",27:"Ventnor\nAve",
    28:"Water\nWorks",29:"Marvin\nGardens",30:"GO TO\nJAIL",
    31:"Pacific\nAve",32:"N.Carolina\nAve",33:"Community\nChest",
    34:"Penn.\nAve",35:"Short Line\nRR",36:"Chance",37:"Park\nPlace",
    38:"Luxury\nTax",39:"Boardwalk"
};

function squareRect(pos) {
    if (pos === 0)  return [BOARD_SIZE - CORNER, BOARD_SIZE - CORNER, BOARD_SIZE, BOARD_SIZE];
    if (pos === 10) return [0, BOARD_SIZE - CORNER, CORNER, BOARD_SIZE];
    if (pos === 20) return [0, 0, CORNER, CORNER];
    if (pos === 30) return [BOARD_SIZE - CORNER, 0, BOARD_SIZE, CORNER];

    if (pos >= 1 && pos <= 9) {
        const i = 9 - (pos - 1);
        const x = CORNER + i * SIDE_W;
        return [x, BOARD_SIZE - CORNER, x + SIDE_W, BOARD_SIZE];
    }
    if (pos >= 11 && pos <= 19) {
        const i = 9 - (pos - 11);
        return [0, CORNER + i * SIDE_W, CORNER, CORNER + (i+1) * SIDE_W];
    }
    if (pos >= 21 && pos <= 29) {
        const i = pos - 21;
        return [CORNER + i * SIDE_W, 0, CORNER + (i+1) * SIDE_W, CORNER];
    }
    if (pos >= 31 && pos <= 39) {
        const i = pos - 31;
        return [BOARD_SIZE - CORNER, CORNER + i * SIDE_W, BOARD_SIZE, CORNER + (i+1) * SIDE_W];
    }
    return [0, 0, 0, 0];
}

function drawBoard(ctx, boardSpaces, boardState, players, freeParkingPot, dice, posOverrides) {
    ctx.clearRect(0, 0, BOARD_SIZE, BOARD_SIZE);

    // Draw squares
    for (const sp of boardSpaces) {
        const pos = sp.pos;
        const [x1, y1, x2, y2] = squareRect(pos);
        const w = x2 - x1, h = y2 - y1;
        const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;

        // Background
        ctx.fillStyle = "#e8f5e9";
        ctx.fillRect(x1, y1, w, h);
        ctx.strokeStyle = "#2e7d32";
        ctx.lineWidth = 0.5;
        ctx.strokeRect(x1, y1, w, h);

        // Color band for properties
        if (sp.type === "property" && sp.color) {
            ctx.fillStyle = COLOR_HEX[sp.color] || "#888";
            if (pos >= 1 && pos <= 9) ctx.fillRect(x1, y1, w, 10);
            else if (pos >= 11 && pos <= 19) ctx.fillRect(x2 - 10, y1, 10, h);
            else if (pos >= 21 && pos <= 29) ctx.fillRect(x1, y2 - 10, w, 10);
            else if (pos >= 31 && pos <= 39) ctx.fillRect(x1, y1, 10, h);
        }

        // Label
        const abbr = ABBREV[pos] || sp.name;
        ctx.fillStyle = "#333";
        ctx.font = "bold 6px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        const lines = abbr.split("\n");
        const lh = 8;
        const startY = cy - ((lines.length - 1) * lh) / 2 + (sp.type === "property" ? 4 : 0);
        lines.forEach((line, i) => ctx.fillText(line, cx, startY + i * lh));

        // Price
        if (sp.price && (sp.type === "property" || sp.type === "railroad" || sp.type === "utility")) {
            ctx.font = "5px Arial";
            ctx.fillStyle = "#666";
            if (pos >= 1 && pos <= 9) ctx.fillText("$" + sp.price, cx, y2 - 8);
            else if (pos >= 11 && pos <= 19) ctx.fillText("$" + sp.price, x1 + 18, cy + 14);
            else if (pos >= 21 && pos <= 29) ctx.fillText("$" + sp.price, cx, y1 + 12);
            else if (pos >= 31 && pos <= 39) ctx.fillText("$" + sp.price, x2 - 18, cy + 14);
        }

        // Owner indicator
        const bs = boardState[String(pos)];
        if (bs && bs.owner) {
            const ownerPlayer = players.find(p => p.name === bs.owner);
            if (ownerPlayer) {
                ctx.fillStyle = ownerPlayer.color;
                ctx.fillRect(x1 + 1, y2 - 4, w - 2, 3);
            }
        }

        // Houses
        if (bs && bs.houses > 0 && bs.houses < 5) {
            for (let hi = 0; hi < bs.houses; hi++) {
                ctx.fillStyle = "#27AE60";
                if (pos >= 1 && pos <= 9) ctx.fillRect(x1 + 3 + hi * 10, y1 + 11, 8, 6);
                else if (pos >= 11 && pos <= 19) ctx.fillRect(x2 - 17, y1 + 3 + hi * 10, 6, 8);
                else if (pos >= 21 && pos <= 29) ctx.fillRect(x1 + 3 + hi * 10, y2 - 17, 8, 6);
                else if (pos >= 31 && pos <= 39) ctx.fillRect(x1 + 11, y1 + 3 + hi * 10, 6, 8);
            }
        } else if (bs && bs.houses === 5) {
            ctx.fillStyle = "#E74C3C";
            if (pos >= 1 && pos <= 9) ctx.fillRect(x1 + 12, y1 + 11, 24, 8);
            else if (pos >= 11 && pos <= 19) ctx.fillRect(x2 - 19, y1 + 12, 8, 24);
            else if (pos >= 21 && pos <= 29) ctx.fillRect(x1 + 12, y2 - 19, 24, 8);
            else if (pos >= 31 && pos <= 39) ctx.fillRect(x1 + 11, y1 + 12, 8, 24);
        }
    }

    // Free Parking pot
    if (freeParkingPot > 0) {
        const [x1, y1, x2, y2] = squareRect(20);
        ctx.fillStyle = "#228B22";
        ctx.font = "bold 9px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("$" + freeParkingPot.toLocaleString(), (x1+x2)/2, (y1+y2)/2 + 18);
    }

    // Center
    ctx.fillStyle = "#e8f5e9";
    ctx.fillRect(CORNER, CORNER, BOARD_SIZE - 2 * CORNER, BOARD_SIZE - 2 * CORNER);
    ctx.strokeStyle = "#2e7d32";
    ctx.lineWidth = 2;
    ctx.strokeRect(CORNER, CORNER, BOARD_SIZE - 2 * CORNER, BOARD_SIZE - 2 * CORNER);

    const ccx = BOARD_SIZE / 2, ccy = BOARD_SIZE / 2;

    if (dice) {
        ctx.fillStyle = "#c62828";
        ctx.font = "bold italic 24px Georgia";
        ctx.textAlign = "center";
        ctx.fillText("MONOPOLY", ccx, ccy - 55);
        ctx.fillStyle = "#1b5e20";
        ctx.font = "bold 13px Arial";
        ctx.fillText("SIMULATOR", ccx, ccy - 28);

        drawDie(ctx, ccx - 50, ccy + 14, dice[0], 44);
        drawDie(ctx, ccx + 6, ccy + 14, dice[1], 44);

        ctx.fillStyle = "#1b5e20";
        ctx.font = "bold 12px Arial";
        let txt = dice[0] + " + " + dice[1] + " = " + (dice[0] + dice[1]);
        if (dice[0] === dice[1]) txt += "  Doubles!";
        ctx.fillText(txt, ccx, ccy + 68);
    } else {
        ctx.fillStyle = "#c62828";
        ctx.font = "bold italic 24px Georgia";
        ctx.textAlign = "center";
        ctx.fillText("MONOPOLY", ccx, ccy - 10);
        ctx.fillStyle = "#1b5e20";
        ctx.font = "bold 13px Arial";
        ctx.fillText("SIMULATOR", ccx, ccy + 20);
    }

    // Tokens
    const offsets = [[12,12],[28,12],[12,28],[28,28]];
    const groups = {};
    for (const p of players) {
        if (p.bankrupt) continue;
        const pos = (posOverrides && posOverrides[p.name] !== undefined) ? posOverrides[p.name] : p.position;
        if (!groups[pos]) groups[pos] = [];
        groups[pos].push(p);
    }
    for (const pos in groups) {
        const [x1, y1, x2, y2] = squareRect(parseInt(pos));
        const bx = (x1 + x2) / 2 - 20;
        const by = (y1 + y2) / 2 - 14;
        groups[pos].forEach((p, i) => {
            if (i >= 4) return;
            const [ox, oy] = offsets[i];
            const tx = bx + ox, ty = by + oy;
            const r = 10;
            ctx.beginPath();
            ctx.arc(tx, ty, r, 0, Math.PI * 2);
            ctx.fillStyle = p.color;
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = "#fff";
            ctx.stroke();
            ctx.fillStyle = "#fff";
            ctx.font = "bold 9px Arial";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(p.name[0].toUpperCase(), tx, ty);
        });
    }
}

function drawDie(ctx, cx, cy, value, size) {
    const half = size / 2;
    ctx.fillStyle = "#fff";
    ctx.fillRect(cx - half, cy - half, size, size);
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 2;
    ctx.strokeRect(cx - half, cy - half, size, size);

    const r = Math.max(3, size / 10);
    const s = 0.30 * size;
    const dots = {
        1: [[0,0]],
        2: [[-s,-s],[s,s]],
        3: [[-s,-s],[0,0],[s,s]],
        4: [[-s,-s],[s,-s],[-s,s],[s,s]],
        5: [[-s,-s],[s,-s],[0,0],[-s,s],[s,s]],
        6: [[-s,-0.38*size],[s,-0.38*size],[-s,0],[s,0],[-s,0.38*size],[s,0.38*size]]
    };
    ctx.fillStyle = "#222";
    for (const [dx, dy] of (dots[value] || [])) {
        ctx.beginPath();
        ctx.arc(cx + dx, cy + dy, r, 0, Math.PI * 2);
        ctx.fill();
    }
}
