// 3D sahneden kare kare ekran görüntüsü alır (Chrome DevTools Protokolü, Node.js 22+).
// araclar/sahne3d_gif.py tarafından çağrılır; elle çalıştırmak gerekmez.
//
// Kullanım: node cdp_kareler.mjs <ayarlar.json>
// ayarlar: { port, url, dizin, t0, t1, adim, genislik, yukseklik, kamera: {konum, hedef},
//            baslik, olaylar: [[t, metin], ...] }

import { readFileSync, writeFileSync } from "node:fs";

const ayar = JSON.parse(readFileSync(process.argv[2], "utf-8"));
const bekle = ms => new Promise(r => setTimeout(r, ms));

const sayfalar = await (await fetch(`http://127.0.0.1:${ayar.port}/json/list`)).json();
const ws = new WebSocket(sayfalar.find(s => s.type === "page").webSocketDebuggerUrl);
await new Promise((tamam, hata) => { ws.onopen = tamam; ws.onerror = hata; });

let sira = 0;
const bekleyen = new Map();
ws.onmessage = e => {
  const m = JSON.parse(e.data);
  if (m.id && bekleyen.has(m.id)) { bekleyen.get(m.id)(m); bekleyen.delete(m.id); }
};
const cdp = (method, params = {}) => new Promise((tamam, hata) => {
  const id = ++sira;
  bekleyen.set(id, m => (m.error ? hata(new Error(`${method}: ${JSON.stringify(m.error)}`)) : tamam(m.result)));
  ws.send(JSON.stringify({ id, method, params }));
});
const js = async ifade => {
  const r = await cdp("Runtime.evaluate", { expression: ifade, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description || r.exceptionDetails.text);
  return r.result.value;
};

await cdp("Emulation.setDeviceMetricsOverride",
  { width: ayar.genislik, height: ayar.yukseklik, deviceScaleFactor: 1, mobile: false });
await cdp("Page.navigate", { url: ayar.url });

// Veri hesaplanıp 3D sahne hazır olana kadar bekle
let hazir = false;
for (let i = 0; i < 240 && !hazir; i++) {
  await bekle(500);
  hazir = await js(`!!(window.sahne3d && typeof veri !== "undefined" && veri &&
    document.getElementById("durumMetni").textContent.includes("hazır"))`).catch(() => false);
}
if (!hazir) throw new Error("Sayfa hazır olmadı (veri ya da 3D sahne yüklenemedi)");

// Sahneyi tam ekrana al, arayüz panellerini gizle, başlık katmanını ekle
await js(`(() => {
  const s = document.createElement("style");
  s.textContent = \`
    body { overflow: hidden; }
    header, #sol, #sag, #zaman-satir, .gorunum-sec, #orta .not, .sahne-ust { display: none !important; }
    #sahne-kutu { position: fixed !important; inset: 0; aspect-ratio: auto !important;
                  border-radius: 0 !important; border: 0 !important; z-index: 10; }
    #kayit-baslik { position: fixed; left: 18px; top: 14px; z-index: 20; color: #e9f0f8;
                    font: 650 18px system-ui, sans-serif; text-shadow: 0 1px 3px #000; }
    #kayit-baslik span { display: block; font-weight: 500; font-size: 13.5px; color: #b9c9dc; margin-top: 4px; }
    #kayit-baslik b { color: #ffc44d; font-weight: 600; }\`;
  document.head.appendChild(s);
  const b = document.createElement("div"); b.id = "kayit-baslik"; document.body.appendChild(b);
  window.sahne3d.kayitModu(true);
  return true;
})()`);
await bekle(600);   // yeniden boyutlanma
await js(`sahne3d.kameraAyarla(${JSON.stringify(ayar.kamera.konum)}, ${JSON.stringify(ayar.kamera.hedef)}); true`);

const olaylar = ayar.olaylar || [];
let n = 0;
for (let t = ayar.t0; t <= ayar.t1 + 1e-9; t += ayar.adim, n++) {
  const olay = olaylar.filter(([t0]) => t >= t0).pop();
  const alt = `t = ${Math.floor(t)} s${olay ? " · " + olay[1] : ""}`;
  await js(`zamanAyarla(${t});
    document.getElementById("kayit-baslik").innerHTML = ${JSON.stringify(ayar.baslik)} + "<span>" + ${JSON.stringify(alt)} + "</span>";
    sahne3d.kayitKaresi(${n * 100}); true`);
  const r = await cdp("Page.captureScreenshot", { format: "png" });
  writeFileSync(`${ayar.dizin}/kare_${String(n).padStart(4, "0")}.png`, Buffer.from(r.data, "base64"));
}
console.log(`${n} kare kaydedildi`);
ws.close();
