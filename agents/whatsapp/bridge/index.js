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
const logger = pino({ level: 'silent' });

let sock = null;
let connectionStatus = 'disconnected';

// --- WhatsApp Connection ---

async function connectWA() {
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

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect } = update;
        
        if (connection === 'close') {
            const reason = lastDisconnect?.error?.output?.statusCode;
            connectionStatus = 'disconnected';
            
            if (reason !== DisconnectReason.loggedOut) {
                // Reconnect after 5 seconds
                setTimeout(connectWA, 5000);
            } else {
                console.log('[BRIDGE] Logged out. Delete auth_info/ and restart to re-auth.');
            }
        } else if (connection === 'open') {
            connectionStatus = 'connected';
            console.log('[BRIDGE] WhatsApp connected!');
        }
    });
}

// --- API Routes ---

// Send a message
app.post('/send', async (req, res) => {
    if (connectionStatus !== 'connected') {
        return res.json({ error: 'WhatsApp not connected', status: connectionStatus });
    }
    
    const { to, text } = req.body;
    if (!to || !text) {
        return res.json({ error: 'Missing "to" or "text" in body' });
    }
    
    try {
        const result = await sock.sendMessage(to, { text });
        res.json({ status: 'sent', key: result.key });
    } catch (e) {
        res.json({ error: e.message });
    }
});

// Read unread messages
app.get('/read', async (req, res) => {
    if (connectionStatus !== 'connected') {
        return res.json({ error: 'WhatsApp not connected', status: connectionStatus, messages: [] });
    }
    
    // Return empty for now — full implementation would store messages
    res.json({ messages: [], count: 0 });
});

// Connection status
app.get('/status', (req, res) => {
    res.json({
        status: connectionStatus,
        user: sock?.user || null,
    });
});

// Health check
app.get('/health', (req, res) => {
    res.json({ status: 'ok', whatsapp: connectionStatus });
});

// --- Start ---

app.listen(PORT, () => {
    console.log(`[BRIDGE] WhatsApp bridge running on http://localhost:${PORT}`);
    connectWA();
});