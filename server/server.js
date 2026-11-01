const express = require('express');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json({ limit: '10mb' }));

// In-memory / persistent mock store for demo cloud sync
const cloudSync = {
  backups: new Map(),
  invoices: new Map(),
};

// Health Check Endpoint
app.get('/api/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'Kapda Bill Backend API',
    uptime: process.uptime(),
    timestamp: new Date().toISOString()
  });
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
