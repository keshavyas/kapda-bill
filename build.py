import json, re, pathlib
try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

root=pathlib.Path(__file__).parent; src=(root/'src/app.html').read_text(encoding='utf-8'); d=root/'dist'; d.mkdir(exist_ok=True)
VER="1.0.0"
head='''<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#2563eb">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<link rel="manifest" href="manifest.json">
<link rel="icon" href="icon-192.png">
<link rel="apple-touch-icon" href="icon-192.png">
<script src="capacitor.js"></script>
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}[hidden]{display:none!important}img{max-width:100%}</style>
</head>
<body>
'''
(d/'index.html').write_text(head+src+'\n</body>\n</html>\n',encoding='utf-8')

# Copy capacitor runtime if available
cap_src = root/'node_modules/@capacitor/core/dist/capacitor.js'
if cap_src.exists():
    (d/'capacitor.js').write_text(cap_src.read_text(encoding='utf-8'), encoding='utf-8')
else:
    (d/'capacitor.js').write_text('/* Capacitor dummy web fallback */', encoding='utf-8')

# Copy standalone invoice viewer
inv_src = root/'src/invoice.html'
if inv_src.exists():
    (d/'invoice.html').write_text(inv_src.read_text(encoding='utf-8'), encoding='utf-8')

(d/'manifest.json').write_text(json.dumps({"name":"Bill Book","short_name":"Bill Book","start_url":"./index.html","scope":"./","display":"standalone","orientation":"portrait","background_color":"#f8fafc","theme_color":"#2563eb","lang":"hi",
 "icons":[{"src":"icon-192.png","sizes":"192x192","type":"image/png","purpose":"any"},{"src":"icon-512.png","sizes":"512x512","type":"image/png","purpose":"any"},{"src":"icon-maskable-512.png","sizes":"512x512","type":"image/png","purpose":"maskable"}]},ensure_ascii=False,indent=1),encoding='utf-8')
sw='''/* Kapda Bill service worker: makes the app open without internet. */
const CACHE="kapdabill-%s";
const SHELL=["./","./index.html","./manifest.json","./icon-192.png","./icon-512.png","./icon-maskable-512.png"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(SHELL)).then(()=>self.skipWaiting()));});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener("fetch",e=>{
  const req=e.request; if(req.method!=="GET") return;
  const url=new URL(req.url);
  const isFont=url.hostname==="fonts.googleapis.com"||url.hostname==="fonts.gstatic.com";
  if(url.origin!==location.origin&&!isFont) return;
  if(req.mode==="navigate"){ // network first so updates arrive, cache when offline
    e.respondWith(fetch(req).then(r=>{const cp=r.clone(); caches.open(CACHE).then(c=>c.put("./index.html",cp)); return r;}).catch(()=>caches.match("./index.html")));
    return; }
  e.respondWith(caches.match(req).then(hit=>hit||fetch(req).then(r=>{ if(r.ok||r.type==="opaque"){const cp=r.clone(); caches.open(CACHE).then(c=>c.put(req,cp));} return r; })));
});
'''%VER
(d/'sw.js').write_text(sw,encoding='utf-8')

if HAS_PIL:
    font=None
    for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        try: font=f; ImageFont.truetype(f,10)
        except Exception: font=None
    def icon(size,maskable):
        im=Image.new("RGB",(size,size),"#2563eb"); dr=ImageDraw.Draw(im); s=size/512
        inset=0.18 if maskable else 0.12
        x0,y0,x1,y1=size*(0.5-0.5+inset+0.06),size*inset,size*(1-inset-0.06),size*(1-inset)
        dr.rounded_rectangle([x0,y0,x1,y1],radius=int(28*s),fill="#F2B01E")
        n=7; w=(x1-x0)/n
        pts=[(x0,y1-20*s)]+[(x0+w*i+w/2, y1+ (0 if i%1 else 0)) for i in range(0)]
        for i in range(n): dr.polygon([(x0+w*i,y1-1),(x0+w*i+w/2,y1-22*s),(x0+w*(i+1),y1-1)],fill="#2563eb")
        f=ImageFont.truetype(font,int(200*s*(0.85 if maskable else 1))) if font else ImageFont.load_default()
        dr.text((size/2,(y0+y1)/2-18*s),"₹",font=f,fill="#2563eb",anchor="mm")
        for k in range(2):
            yy=y1-(70+k*34)*s*(0.9 if maskable else 1); dr.rounded_rectangle([x0+40*s,yy,x1-40*s,yy+12*s],radius=int(6*s),fill="#2563eb")
        return im
    icon(192,False).save(d/'icon-192.png'); icon(512,False).save(d/'icon-512.png'); icon(512,True).save(d/'icon-maskable-512.png')

# Mirror to public folder for Vercel/hosts expecting public/
import shutil
pub = root / 'public'
pub.mkdir(exist_ok=True)
for item in d.iterdir():
    if item.is_file():
        shutil.copy2(item, pub / item.name)

# Mirror to Android assets directory for Capacitor APK
android_pub = root / 'android/app/src/main/assets/public'
if android_pub.exists():
    for item in d.iterdir():
        if item.is_file():
            shutil.copy2(item, android_pub / item.name)

print("built",[p.name for p in d.iterdir()])
