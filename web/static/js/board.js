// board.js - Canvas-based Monopoly board renderer (HiDPI-aware)
"use strict";

const BOARD_SIZE = 640;
const CORNER = 86;
const SIDE_W = 52;

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
    const BS = BOARD_SIZE, C = CORNER, S = SIDE_W;
    if (pos === 0)  return [BS-C, BS-C, BS, BS];
    if (pos === 10) return [0, BS-C, C, BS];
    if (pos === 20) return [0, 0, C, C];
    if (pos === 30) return [BS-C, 0, BS, C];
    if (pos >= 1 && pos <= 9) {
        const x = BS - C - pos * S;
        return [x, BS-C, x+S, BS];
    }
    if (pos >= 11 && pos <= 19) {
        const y = BS - C - (pos-10) * S;
        return [0, y, C, y+S];
    }
    if (pos >= 21 && pos <= 29) {
        const x = C + (pos-21) * S;
        return [x, 0, x+S, C];
    }
    if (pos >= 31 && pos <= 39) {
        const y = C + (pos-31) * S;
        return [BS-C, y, BS, y+S];
    }
    return [0, 0, 0, 0];
}

function drawBoard(ctx, boardSpaces, boardState, players, freeParkingPot, dice, posOverrides) {
    ctx.clearRect(0, 0, BOARD_SIZE, BOARD_SIZE);
    const BS = BOARD_SIZE, C = CORNER;

    for (const sp of boardSpaces) {
        const pos = sp.pos;
        const [x1, y1, x2, y2] = squareRect(pos);
        const w = x2 - x1, h = y2 - y1;
        const cx = (x1 + x2) / 2, cy = (y1 + y2) / 2;

        ctx.fillStyle = "#f0f9f0";
        ctx.fillRect(x1, y1, w, h);
        ctx.strokeStyle = "#2e7d32";
        ctx.lineWidth = 0.5;
        ctx.strokeRect(x1, y1, w, h);

        if (sp.type === "property" && sp.color) {
            const bandH = 12;
            ctx.fillStyle = COLOR_HEX[sp.color] || "#888";
            if (pos >= 1 && pos <= 9)   ctx.fillRect(x1, y1, w, bandH);
            else if (pos >= 11 && pos <= 19) ctx.fillRect(x2-bandH, y1, bandH, h);
            else if (pos >= 21 && pos <= 29) ctx.fillRect(x1, y2-bandH, w, bandH);
            else if (pos >= 31 && pos <= 39) ctx.fillRect(x1, y1, bandH, h);
        }

        drawSquareLabel(ctx, sp, pos, x1, y1, x2, y2, cx, cy, w, h);

        const bs = boardState && boardState[String(pos)];
        
        if (bs && bs.houses > 0) {
            if (bs.houses === 5) {
                ctx.fillStyle = "#E74C3C";
                if (pos >= 1 && pos <= 9)        ctx.fillRect(x1+14, y1+14, 24, 8);
                else if (pos >= 11 && pos <= 19) ctx.fillRect(x2-22, y1+14, 8, 24);
                else if (pos >= 21 && pos <= 29) ctx.fillRect(x1+14, y2-22, 24, 8);
                else if (pos >= 31 && pos <= 39) ctx.fillRect(x1+14, y1+14, 8, 24);
            } else {
                ctx.fillStyle = "#27AE60";
                for (let hi = 0; hi < bs.houses; hi++) {
                    if (pos >= 1 && pos <= 9)        ctx.fillRect(x1+3+hi*10, y1+14, 8, 6);
                    else if (pos >= 11 && pos <= 19) ctx.fillRect(x2-21, y1+3+hi*10, 6, 8);
                    else if (pos >= 21 && pos <= 29) ctx.fillRect(x1+3+hi*10, y2-20, 8, 6);
                    else if (pos >= 31 && pos <= 39) ctx.fillRect(x1+15, y1+3+hi*10, 6, 8);
                }
            }
        }
    }

    if (freeParkingPot > 0) {
        const [x1,y1,x2,y2] = squareRect(20);
        ctx.fillStyle = "#1b5e20";
        ctx.font = "bold 9px Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("$"+freeParkingPot.toLocaleString(), (x1+x2)/2, (y1+y2)/2+20);
    }

    ctx.fillStyle = "#e8f5e9";
    ctx.fillRect(C, C, BS-2*C, BS-2*C);
    ctx.strokeStyle = "#2e7d32";
    ctx.lineWidth = 2;
    ctx.strokeRect(C, C, BS-2*C, BS-2*C);

    drawCenter(ctx, dice);
    drawTokens(ctx, players, boardState, posOverrides);
}

function drawSquareLabel(ctx, sp, pos, x1, y1, x2, y2, cx, cy, w, h) {
    ctx.fillStyle = "#1a1a1a";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    const isCorner = (pos === 0 || pos === 10 || pos === 20 || pos === 30);
    if (isCorner) {
        ctx.font = "bold 8px Arial";
        const lines = (ABBREV[pos] || "").split("\n");
        lines.forEach((l, i) => ctx.fillText(l, cx, cy + (i - (lines.length-1)/2) * 10));
        return;
    }

    const isLeft  = (pos >= 11 && pos <= 19);
    const isRight = (pos >= 31 && pos <= 39);
    const isTop   = (pos >= 21 && pos <= 29);
    const isBot   = (pos >= 1  && pos <= 9);

    const abbr = ABBREV[pos] || sp.name;
    const lines = abbr.split("\n");
    const bandH = sp.type === "property" ? 12 : 0;

    if (isLeft || isRight) {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(isLeft ? Math.PI/2 : -Math.PI/2);
        ctx.font = "bold 6px Arial";
        const lh = 8;
        const totalH = (lines.length - 1) * lh;
        lines.forEach((l, i) => ctx.fillText(l, 0, -totalH/2 + i*lh));
        if (sp.price) {
            ctx.fillStyle = "#555";
            ctx.font = "5px Arial";
            // After rotation, Y axis points toward/away from center.
            // Negative Y = toward center (where price should be, near the color band)
            ctx.fillText("$"+sp.price, 0, -h/2 + 8);
        }
        ctx.restore();
    } else {
        ctx.font = "bold 6px Arial";
        const lh = 8;
        let midY = cy + (isBot ? bandH/2 : -bandH/2);
        const totalH = (lines.length - 1) * lh;
        lines.forEach((l, i) => ctx.fillText(l, cx, midY - totalH/2 + i*lh));
        if (sp.price) {
            ctx.fillStyle = "#555";
            ctx.font = "5px Arial";
            ctx.fillText("$"+sp.price, cx, isBot ? y2-7 : y1+7);
        }
    }
}

function drawCenter(ctx, dice) {
    const cx = BOARD_SIZE/2, cy = BOARD_SIZE/2;
    ctx.textAlign = "center";
    if (dice) {
        ctx.fillStyle = "#c62828";
        ctx.font = "bold italic 22px Georgia";
        ctx.fillText("MONOPOLY", cx, cy-55);
        ctx.fillStyle = "#1b5e20";
        ctx.font = "bold 12px Arial";
        ctx.fillText("SIMULATOR", cx, cy-28);
        drawDie(ctx, cx-50, cy+14, dice[0], 44);
        drawDie(ctx, cx+6,  cy+14, dice[1], 44);
        ctx.fillStyle = "#1b5e20";
        ctx.font = "bold 11px Arial";
        let txt = dice[0]+" + "+dice[1]+" = "+(dice[0]+dice[1]);
        if (dice[0]===dice[1]) txt += "  Doubles!";
        ctx.fillText(txt, cx, cy+68);
    } else {
        ctx.fillStyle = "#c62828";
        ctx.font = "bold italic 22px Georgia";
        ctx.fillText("MONOPOLY", cx, cy-10);
        ctx.fillStyle = "#1b5e20";
        ctx.font = "bold 12px Arial";
        ctx.fillText("SIMULATOR", cx, cy+18);
    }
}

function drawTokens(ctx, players, boardState, posOverrides) {
    const offsets = [[14,14],[30,14],[14,30],[30,30]];
    const groups = {};
    for (const p of players) {
        if (p.bankrupt) continue;
        const pos = (posOverrides && posOverrides[p.name] !== undefined)
                    ? posOverrides[p.name] : p.position;
        (groups[pos] = groups[pos] || []).push(p);
    }
    for (const pos in groups) {
        const [x1,y1,x2,y2] = squareRect(parseInt(pos));
        const bx = (x1+x2)/2 - 22, by = (y1+y2)/2 - 16;
        groups[pos].forEach((p, i) => {
            if (i >= 4) return;
            const tx = bx + offsets[i][0], ty = by + offsets[i][1];
            ctx.beginPath();
            ctx.arc(tx, ty, 10, 0, Math.PI*2);
            ctx.fillStyle = p.color;
            ctx.fill();
            ctx.strokeStyle = "#fff";
            ctx.lineWidth = 2;
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
    const half = size/2;
    ctx.fillStyle = "#fff";
    ctx.fillRect(cx-half, cy-half, size, size);
    ctx.strokeStyle = "#333";
    ctx.lineWidth = 2;
    ctx.strokeRect(cx-half, cy-half, size, size);
    const r = Math.max(3, size/10), s = 0.30*size;
    const dots = {
        1:[[0,0]], 2:[[-s,-s],[s,s]], 3:[[-s,-s],[0,0],[s,s]],
        4:[[-s,-s],[s,-s],[-s,s],[s,s]], 5:[[-s,-s],[s,-s],[0,0],[-s,s],[s,s]],
        6:[[-s,-0.38*size],[s,-0.38*size],[-s,0],[s,0],[-s,0.38*size],[s,0.38*size]]
    };
    ctx.fillStyle = "#222";
    for (const [dx,dy] of (dots[value]||[])) {
        ctx.beginPath(); ctx.arc(cx+dx, cy+dy, r, 0, Math.PI*2); ctx.fill();
    }
}


