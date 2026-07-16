#!/usr/bin/env node
/**
 * WhatsApp Bridge — Baileys microservice for KAGE OS.
 * Exposes POST /send, GET /read, GET /status on localhost:3030
 * Auth creds stored in ./auth_info/
 */

const express = require('express');
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const path = require('path');
const fs = require('fs');

const app = express();
app.use(express.json());

const PORT = 3030;
const AUTH_DIR = path.join(__dirname, 'auth_info');
if (!fs.existsSync(AUTH_DIR)) {
    fs.mkdirSync(AUTH_DIR, { recursive: true });
}

const logger = pino({ level: 'silent' });

let sock = null;
let connectionStatus = 'disconnected';
const messageBuffer = [];
const MAX_MESSAGES = 100;

function formatJid(target) {
    if (!target) return target;
    if (target.includes('@s.whatsapp.net') || target.includes('@g.us')) {
        return target;
    }
    const cleanNum = target.replace(/[^0-9]/g, '');
    return `${cleanNum}@s.whatsapp.net`;
}

// --- WhatsApp Connection ---

async function connectWA() {
    try {
        const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
        const { version } = await fetchLatestBaileysVersion();
        
        sock = makeWASocket({
            version,
            auth: state,
            printQRInTerminal: true,
            logger,
            browser: ['KAGE OS', 'Safari', '3.0'],
        });

        sock.ev.on('creds.update', saveCreds);

        sock.ev.on('messages.upsert', (m) => {
            if (m.type === 'notify' || m.type === 'append') {
                for (const msg of m.messages) {
                    if (!msg.key.fromMe) {
                        messageBuffer.push({
                            id: msg.key.id,
                            from: msg.key.remoteJid,
                            senderName: msg.pushName || 'Unknown',
                            timestamp: msg.messageTimestamp,
                            text: msg.message?.conversation || msg.message?.extendedTextMessage?.text || '',
                        });
                        if (messageBuffer.length > MAX_MESSAGES) {
                            messageBuffer.shift();
                        }
                    }
                }
            }
        });

        sock.ev.on('connection.update', (update) => {
            const { connection, lastDisconnect } = update;
            
            if (connection === 'close') {
                const reason = lastDisconnect?.error?.output?.statusCode;
                connectionStatus = 'disconnected';
                
                if (reason !== DisconnectReason.loggedOut) {
                    setTimeout(connectWA, 5000);
                } else {
                    console.log('[BRIDGE] Logged out. Delete auth_info/ and restart to re-auth.');
                }
            } else if (connection === 'open') {
                connectionStatus = 'connected';
                console.log('[BRIDGE] WhatsApp connected!');
            }
        });
    } catch (err) {
        console.error('[BRIDGE] Connection error:', err.message);
        connectionStatus = 'error';
        setTimeout(connectWA, 10000);
    }
}

// --- API Routes ---

// Send a message
app.post('/send', async (req, res) => {
    if (connectionStatus !== 'connected') {
        return res.status(400).json({ error: 'WhatsApp not connected', status: connectionStatus });
    }
    
    const { to, text } = req.body;
    if (!to || !text) {
        return res.status(400).json({ error: 'Missing "to" or "text" in body' });
    }
    
    try {
        const jid = formatJid(to);
        const result = await sock.sendMessage(jid, { text });
        res.json({ status: 'sent', jid, key: result.key });
    } catch (e) {
        res.status(500).json({ error: e.message });
    }
});

// Read unread/recent messages
app.get('/read', async (req, res) => {
    const unread = messageBuffer.splice(0, messageBuffer.length);
    res.json({ count: unread.length, messages: unread, whatsapp: connectionStatus });
});

// Connection status
app.get('/status', (req, res) => {
    res.json({
        status: connectionStatus,
        user: sock?.user || null,
        buffered_messages: messageBuffer.length,
    });
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', whatsapp: connectionStatus });
});

// Stop bridge
app.post('/stop', (req, res) => {
    res.json({ status: 'stopping' });
    process.exit(0);
});

// --- Start ---

app.listen(PORT, () => {
    console.log(`[BRIDGE] WhatsApp bridge running on http://localhost:${PORT}`);
    connectWA();
});
