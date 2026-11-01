const express = require('express');
const cors = require('cors');

const fs = require('fs');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json({ limit: '10mb' }));

const DB_FILE = path.join(__dirname, 'cloud_db.json');

// In-memory + persistent disk store for SaaS multi-shop catalog sync
const cloudSync = {
  backups: new Map(),
  invoices: new Map(),
  shops: new Map(),
};

// Load saved data from disk if exists
try {
  if (fs.existsSync(DB_FILE)) {
    const raw = fs.readFileSync(DB_FILE, 'utf8');
    const parsed = JSON.parse(raw);
    if (parsed.shops && Array.isArray(parsed.shops)) {
      parsed.shops.forEach(s => cloudSync.shops.set(s.shopId, s));
    }
    if (parsed.backups && typeof parsed.backups === 'object') {
      Object.entries(parsed.backups).forEach(([k, v]) => cloudSync.backups.set(k, v));
    }
    if (parsed.invoices && typeof parsed.invoices === 'object') {
      Object.entries(parsed.invoices).forEach(([k, v]) => cloudSync.invoices.set(k, v));
    }
    console.log(`[KapdaBill SaaS] Loaded ${cloudSync.shops.size} registered shops from disk.`);
  }
} catch (e) {
  console.warn('[KapdaBill SaaS] Warning: Could not read cloud_db.json:', e.message);
}

function saveDbToDisk() {
  try {
    const data = {
      shops: Array.from(cloudSync.shops.values()),
      backups: Object.fromEntries(cloudSync.backups),
      invoices: Object.fromEntries(cloudSync.invoices)
    };
    fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2), 'utf8');
  } catch (e) {
    console.warn('[KapdaBill SaaS] Warning: Could not write cloud_db.json:', e.message);
  }
}

// Health Check Endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'Kapda Bill Backend API',
    uptime: process.uptime(),
    registeredShops: cloudSync.shops.size,
    timestamp: new Date().toISOString()
  });
});

// SaaS Shop Lookup & Registration Endpoint
app.post('/api/shops/lookup', (req, res) => {
  const { shopName, mobile, address } = req.body;
  if (!mobile && !shopName) {
    return res.status(400).json({ error: 'Shop name or mobile number is required' });
  }

  const cleanPhone = mobile ? String(mobile).replace(/\D/g, '').slice(-10) : '';
  const shopId = cleanPhone ? ('shop_' + cleanPhone) : ('shop_' + String(shopName).trim().toLowerCase().replace(/\s+/g, '_'));

  // Dual Lookup: Check by mobile or by Shop Name
  let existing = null;
  if (cleanPhone && cloudSync.shops.has('shop_' + cleanPhone)) {
    existing = cloudSync.shops.get('shop_' + cleanPhone);
  } else if (shopName) {
    const qName = String(shopName).trim().toLowerCase();
    for (const s of cloudSync.shops.values()) {
      if (s.shopName && s.shopName.toLowerCase() === qName) {
        existing = s;
        break;
      }
    }
  }

  if (existing) {
    const backup = cloudSync.backups.get(existing.shopId);
    return res.json({
      exists: true,
      shopId: existing.shopId,
      shop: existing,
      data: backup ? backup.data : null,
      message: 'Shop already registered. Restoring catalog items.'
    });
  }

  // Register brand new shop with clean slate (0 items)
  const newShop = {
    shopId,
    shopName: shopName ? String(shopName).trim() : 'Bill Book Store',
    mobile: cleanPhone || '',
    address: address ? String(address).trim() : '',
    createdAt: new Date().toISOString()
  };
  cloudSync.shops.set(shopId, newShop);
  saveDbToDisk();

  res.json({
    exists: false,
    isNew: true,
    shopId,
    shop: newShop,
    data: null,
    message: 'New shop registered successfully with clean catalog (0 items).'
  });
});

// SaaS Admin Endpoint: List all registered shops
app.get('/api/shops', (req, res) => {
  const allShops = Array.from(cloudSync.shops.values());
  res.json({ count: allShops.length, shops: allShops });
});

// CSV parser endpoint (handles CSV item lists if shopkeeper uploads to backend)
app.post('/api/items/csv', (req, res) => {
  const { csvText } = req.body;
  if (!csvText) {
    return res.status(400).json({ error: 'csvText is required in request body' });
  }

  const lines = csvText.split(/\r?\n/).filter(l => l.trim().length > 0);
  if (lines.length <= 1) {
    return res.json({ items: [] });
  }

  const header = lines[0].split(',').map(h => h.trim().toLowerCase());
  let nameIdx = header.findIndex(h => h.includes('name') || h.includes('item') || h.includes('सामान'));
  if (nameIdx === -1) nameIdx = 0;
  let hsnIdx = header.findIndex(h => h.includes('hsn') || h.includes('code'));
  let gstIdx = header.findIndex(h => h.includes('gst') || h.includes('rate') || h.includes('tax'));

  const items = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',').map(c => c.trim().replace(/^["']|["']$/g, ''));
    if (!cols[nameIdx]) continue;
    items.push({
      name: cols[nameIdx],
      hsn: hsnIdx !== -1 && cols[hsnIdx] ? cols[hsnIdx] : '',
      gst: gstIdx !== -1 && cols[gstIdx] ? cols[gstIdx].replace(/%/g, '') : 'auto'
    });
  }

  res.json({ count: items.length, items });
});

// Cloud Backup Storage API
app.post('/api/backup/:shopId', (req, res) => {
  const { shopId } = req.params;
  const backupData = req.body;
  if (!shopId || !backupData) {
    return res.status(400).json({ error: 'shopId and backup data required' });
  }
  cloudSync.backups.set(shopId, {
    data: backupData,
    savedAt: new Date().toISOString()
  });
  saveDbToDisk();
  res.json({ success: true, message: 'Backup saved to cloud', shopId });
});

app.get('/api/backup/:shopId', (req, res) => {
  const { shopId } = req.params;
  const backup = cloudSync.backups.get(shopId);
  if (!backup) {
    return res.status(404).json({ error: 'No backup found for this shop ID' });
  }
  res.json(backup);
});

// Cloud Invoices API (store and retrieve invoices for WhatsApp PDF links)
app.post('/api/invoices', (req, res) => {
  const bill = req.body;
  if (!bill || !bill.no) {
    return res.status(400).json({ error: 'Valid invoice object with "no" is required' });
  }
  cloudSync.invoices.set(bill.no, bill);
  if(bill.id) cloudSync.invoices.set(bill.id, bill);
  saveDbToDisk();
  res.json({
    success: true,
    message: 'Invoice saved to cloud',
    billNo: bill.no,
    viewUrl: `/invoice.html#id=${encodeURIComponent(bill.no)}`
  });
});

app.get('/api/invoices/:id', (req, res) => {
  const { id } = req.params;
  const bill = cloudSync.invoices.get(id);
  if (!bill) {
    return res.status(404).json({ error: 'Invoice not found in cloud' });
  }
  res.json(bill);
});

// Start Server
app.listen(PORT, () => {
  console.log(`Kapda Bill API server listening on port ${PORT}`);
});
