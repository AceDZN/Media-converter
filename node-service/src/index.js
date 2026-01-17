/**
 * Media Converter Service - Node.js Version
 */
const express = require('express');
const path = require('path');
const fs = require('fs').promises;
const { exec } = require('child_process');
const { promisify } = require('util');
const config = require('./config');
const convertRoutes = require('./routes/convert');

const execAsync = promisify(exec);
const app = express();

// Middleware
app.use(express.json());

// CORS middleware
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  next();
});

// Serve static files from uploads directory
app.use('/uploads', express.static(config.uploadDir));

/**
 * Health check endpoint
 */
app.get('/health', async (req, res) => {
  let libreofficeAvailable = false;
  let popplerAvailable = false;

  // Check LibreOffice
  try {
    await execAsync('soffice --version', { timeout: 5000 });
    libreofficeAvailable = true;
  } catch {}

  // Check Poppler
  try {
    await execAsync('pdftoppm -v', { timeout: 5000 });
    popplerAvailable = true;
  } catch {}

  const status = libreofficeAvailable && popplerAvailable ? 'healthy' : 'degraded';

  res.json({
    status,
    version: '1.0.0',
    runtime: 'Node.js',
    libreoffice_available: libreofficeAvailable,
    poppler_available: popplerAvailable,
  });
});

/**
 * Root endpoint
 */
app.get('/', (req, res) => {
  res.json({
    service: 'Media Converter (Node.js)',
    version: '1.0.0',
    docs: '/docs',
    health: '/health',
  });
});

// API routes
app.use('/api/v1/convert', convertRoutes);

/**
 * Start server
 */
async function start() {
  // Ensure upload directory exists
  await fs.mkdir(config.uploadDir, { recursive: true });

  app.listen(config.port, '0.0.0.0', () => {
    console.log(`Media Converter (Node.js) v1.0.0`);
    console.log(`Server running on http://0.0.0.0:${config.port}`);
    console.log(`Upload directory: ${path.resolve(config.uploadDir)}`);
  });
}

start().catch(console.error);
