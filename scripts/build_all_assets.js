const fs = require("fs");
const path = require("path");
const zlib = require("zlib");
const { execSync } = require("child_process");

const ROOT = path.resolve(__dirname, "..");
const SCRATCH = "/Users/keshav.qw/.gemini/antigravity-ide/brain/069b2db3-48e0-4a6c-b411-27f81ea6db9a/scratch";
const MASTER_FG = path.join(SCRATCH, "master_fg.png");
const MASTER_SQ = path.join(SCRATCH, "master_sq.png");
const MASTER_ROUND = path.join(SCRATCH, "master_round.png");

// Save master square to src/icons/app_icon.png
fs.copyFileSync(MASTER_SQ, path.join(ROOT, "src/icons/app_icon.png"));

// 1. Android Mipmap Foreground Icons
const foregrounds = [
  { size: 108, dir: "android/app/src/main/res/mipmap-mdpi" },
  { size: 162, dir: "android/app/src/main/res/mipmap-hdpi" },
  { size: 216, dir: "android/app/src/main/res/mipmap-xhdpi" },
  { size: 324, dir: "android/app/src/main/res/mipmap-xxhdpi" },
  { size: 432, dir: "android/app/src/main/res/mipmap-xxxhdpi" }
];

for(const f of foregrounds){
  const outPath = path.join(ROOT, f.dir, "ic_launcher_foreground.png");
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  execSync(`sips -z ${f.size} ${f.size} "${MASTER_FG}" --out "${outPath}"`);
  console.log(`Generated foreground: ${outPath} (${f.size}x${f.size})`);
}

// 2. Android Mipmap Standard Icons
const standards = [
  { size: 48, dir: "android/app/src/main/res/mipmap-mdpi" },
  { size: 72, dir: "android/app/src/main/res/mipmap-hdpi" },
  { size: 96, dir: "android/app/src/main/res/mipmap-xhdpi" },
  { size: 144, dir: "android/app/src/main/res/mipmap-xxhdpi" },
  { size: 192, dir: "android/app/src/main/res/mipmap-xxxhdpi" }
];

for(const s of standards){
  const outPath = path.join(ROOT, s.dir, "ic_launcher.png");
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  execSync(`sips -z ${s.size} ${s.size} "${MASTER_SQ}" --out "${outPath}"`);
  console.log(`Generated standard launcher: ${outPath} (${s.size}x${s.size})`);
}

// 3. Android Mipmap Round Icons
for(const s of standards){
  const outPath = path.join(ROOT, s.dir, "ic_launcher_round.png");
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  execSync(`sips -z ${s.size} ${s.size} "${MASTER_ROUND}" --out "${outPath}"`);
  console.log(`Generated round launcher: ${outPath} (${s.size}x${s.size})`);
}

// 4. Web / PWA Icons
const pwaIcons = [
  { size: 192, name: "icon-192.png", master: MASTER_SQ },
  { size: 512, name: "icon-512.png", master: MASTER_SQ },
  { size: 512, name: "icon-maskable-512.png", master: MASTER_SQ }
];

for(const p of pwaIcons){
  const outSrc = path.join(ROOT, "src/icons", p.name);
  execSync(`sips -z ${p.size} ${p.size} "${p.master}" --out "${outSrc}"`);
  
  // Copy to dist, public, android assets
  const targets = [
    path.join(ROOT, "dist", p.name),
    path.join(ROOT, "public", p.name),
    path.join(ROOT, "android/app/src/main/assets/public", p.name)
  ];
  for(const t of targets){
    fs.mkdirSync(path.dirname(t), { recursive: true });
    fs.copyFileSync(outSrc, t);
  }
  console.log(`Generated PWA icon: ${p.name}`);
}

// 5. Generate Splash Screens
// Helper to generate a splash screen of width x height with white background and centered logo
const splashResolutions = [
  { w: 1280, h: 1920, file: "android/app/src/main/res/drawable-port-xxxhdpi/splash.png" },
  { w: 960,  h: 1600, file: "android/app/src/main/res/drawable-port-xxhdpi/splash.png" },
  { w: 720,  h: 1280, file: "android/app/src/main/res/drawable-port-xhdpi/splash.png" },
  { w: 480,  h: 800,  file: "android/app/src/main/res/drawable-port-hdpi/splash.png" },
  { w: 320,  h: 480,  file: "android/app/src/main/res/drawable-port-mdpi/splash.png" },
  { w: 1920, h: 1280, file: "android/app/src/main/res/drawable-land-xxxhdpi/splash.png" },
  { w: 1600, h: 960,  file: "android/app/src/main/res/drawable-land-xxhdpi/splash.png" },
  { w: 1280, h: 720,  file: "android/app/src/main/res/drawable-land-xhdpi/splash.png" },
  { w: 800,  h: 480,  file: "android/app/src/main/res/drawable-land-hdpi/splash.png" },
  { w: 480,  h: 320,  file: "android/app/src/main/res/drawable-land-mdpi/splash.png" },
  { w: 480,  h: 320,  file: "android/app/src/main/res/drawable/splash.png" }
];

function makePng(w, h, rgba){
  const crcTable = [];
  for(let n=0; n<256; n++){
    let c = n;
    for(let k=0; k<8; k++){
      if(c & 1) c = 0xedb88320 ^ (c >>> 1);
      else c = c >>> 1;
    }
    crcTable[n] = c;
  }
  function crc32(b){
    let c = 0xffffffff;
    for(let i=0; i<b.length; i++) c = crcTable[(c ^ b[i]) & 0xff] ^ (c >>> 8);
    return (c ^ 0xffffffff) >>> 0;
  }
  function chunk(type, d){
    const len = Buffer.alloc(4); len.writeUInt32BE(d.length, 0);
    const typeBuf = Buffer.from(type, "ascii");
    const crcBuf = Buffer.alloc(4);
    crcBuf.writeUInt32BE(crc32(Buffer.concat([typeBuf, d])), 0);
    return Buffer.concat([len, typeBuf, d, crcBuf]);
  }
  const sig = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4);
  ihdr[8] = 8; ihdr[9] = 6;
  const scanlines = Buffer.alloc(h * (1 + w * 4));
  for(let y=0; y<h; y++){
    scanlines[y * (1 + w * 4)] = 0;
    rgba.copy(scanlines, y * (1 + w * 4) + 1, y * w * 4, (y+1) * w * 4);
  }
  return Buffer.concat([sig, chunk("IHDR", ihdr), chunk("IDAT", zlib.deflateSync(scanlines)), chunk("IEND", Buffer.alloc(0))]);
}

// Decode MASTER_SQ
const sqBuf = fs.readFileSync(MASTER_SQ);
let pos = 8, idat = [];
while(pos < sqBuf.length){
  const len = sqBuf.readUInt32BE(pos);
  const type = sqBuf.toString("ascii", pos+4, pos+8);
  if(type === "IDAT") idat.push(sqBuf.slice(pos+8, pos+8+len));
  pos += 12 + len;
}
const sqRaw = zlib.inflateSync(Buffer.concat(idat));
const sqImg = Buffer.alloc(1024 * 1024 * 4);
const stride = 1 + 1024 * 4;
for(let y = 0; y < 1024; y++){
  const fType = sqRaw[y * stride];
  const scan = sqRaw.slice(y * stride + 1, (y + 1) * stride);
  for(let x = 0; x < 1024 * 4; x++){
    let a = x >= 4 ? sqImg[(y * 1024 * 4) + (x - 4)] : 0;
    let b = y > 0 ? sqImg[((y - 1) * 1024 * 4) + x] : 0;
    let c = (x >= 4 && y > 0) ? sqImg[((y - 1) * 1024 * 4) + (x - 4)] : 0;
    let val = scan[x];
    if(fType === 1) val = (val + a) & 0xff;
    else if(fType === 2) val = (val + b) & 0xff;
    else if(fType === 3) val = (val + Math.floor((a + b) / 2)) & 0xff;
    else if(fType === 4){
      let p = a + b - c;
      let pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
      let pr = (pa <= pb && pa <= pc) ? a : (pb <= pc ? b : c);
      val = (val + pr) & 0xff;
    }
    sqImg[(y * 1024 * 4) + x] = val;
  }
}

for(const res of splashResolutions){
  const outPath = path.join(ROOT, res.file);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });

  // Logo size on splash: ~35% of min dimension
  const minDim = Math.min(res.w, res.h);
  const logoTargetSize = Math.max(120, Math.round(minDim * 0.45));
  const scale = logoTargetSize / 1024;
  const startX = Math.round((res.w - logoTargetSize) / 2);
  const startY = Math.round((res.h - logoTargetSize) / 2);

  const splashRgba = Buffer.alloc(res.w * res.h * 4);
  // Fill with white
  for(let i = 0; i < res.w * res.h; i++){
    splashRgba[i * 4] = 255;
    splashRgba[i * 4 + 1] = 255;
    splashRgba[i * 4 + 2] = 255;
    splashRgba[i * 4 + 3] = 255;
  }

  // Draw logo
  for(let dy = 0; dy < logoTargetSize; dy++){
    const sy = Math.min(1023, Math.floor(dy / scale));
    const dstY = startY + dy;
    if(dstY < 0 || dstY >= res.h) continue;
    for(let dx = 0; dx < logoTargetSize; dx++){
      const sx = Math.min(1023, Math.floor(dx / scale));
      const dstX = startX + dx;
      if(dstX < 0 || dstX >= res.w) continue;

      const srcIdx = (sy * 1024 + sx) * 4;
      const dstIdx = (dstY * res.w + dstX) * 4;
      splashRgba[dstIdx] = sqImg[srcIdx];
      splashRgba[dstIdx + 1] = sqImg[srcIdx + 1];
      splashRgba[dstIdx + 2] = sqImg[srcIdx + 2];
    }
  }

  fs.writeFileSync(outPath, makePng(res.w, res.h, splashRgba));
  console.log(`Generated splash screen: ${res.file} (${res.w}x${res.h})`);
}

console.log("All icons and splash screens successfully generated!");
