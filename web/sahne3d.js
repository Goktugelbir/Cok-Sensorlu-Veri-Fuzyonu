// 3D sahne: 2D haritayla aynı veriyi (sensörler, ölçümler, füzyon izleri) üç boyutlu gösterir.
// Simülasyon 2 boyutludur; hava araçlarının yüksekliği sadece görseldir. Füzyon izleri,
// kestirimin kendisi olduğu için zemin düzleminde çizilir.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const RENK = {
  arka: 0x07111f, zemin: 0x0a1626, saha: 0x0d1d31, izgaraAna: 0x1f3d60, izgaraInce: 0x132840,
  sinir: 0x3d77b8, direk: 0x9fb3c8, kapali: 0x5a6675,
  radar: 0xff8a4c, kamera: 0x2fd39a, konum: 0x9a86ff,
  dost: 0x4c9bff, dusman: 0xff5a5a, gercek: 0xe3eaf3, rota: 0x6f8199,
  donus: 0xffc44d, karistirma: 0xff3b3b, sis: 0xd5dee8,
};
const HAVA_IRTIFA = 450;          // hava araçlarının görsel yüksekliği (m)
const DIREK = { radar: 260, kamera: 160 };
const OLCUM_PENCERE = 3, IZ_KUYRUK = 60;   // 3D'de iz şeridi 60 s geriye uzanır
const MERKEZ = 5000;              // saha 10 km x 10 km; sahne merkezi saha merkezidir
const BASLANGIC_KAMERA = new THREE.Vector3(-3400, 7200, 9000);

// Simülasyon (x doğu, y kuzey) -> three.js (x, yükseklik, z güney)
const v3 = (x, y, h = 0) => new THREE.Vector3(x - MERKEZ, h, MERKEZ - y);

let kutu, renderer, sahne, kamera, kontrol, etiketKutu;
let veri = null, durum = null, gorunur = false, olcek = 1;
const nesne = {};                 // kalıcı sahne nesneleri
const etiketler = new Map();      // anahtar -> {el, konum: Vector3, gorunur}
const darbeler = [];              // konum bildirimi darbeleri (gerçek zamanlı animasyon)
let sonOlcumT = null, takip = "genel";
// Kayıt modu (GIF üretimi, araclar/sahne3d_gif.py): animasyonlar gerçek saat yerine
// sabit adımlarla ilerleyen sanal bir saatle çizilir
let kayit = false, sanalSaat = 0;
const saat = () => (kayit ? sanalSaat : performance.now());

// ---------------------------------------------------------------- dokular
function daireDokusu() {
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const g = c.getContext("2d"), r = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  r.addColorStop(0, "rgba(255,255,255,1)"); r.addColorStop(0.55, "rgba(255,255,255,0.9)");
  r.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = r; g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}
function sisDokusu() {
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const g = c.getContext("2d"), r = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  r.addColorStop(0, "rgba(255,255,255,0.85)"); r.addColorStop(0.5, "rgba(255,255,255,0.35)");
  r.addColorStop(1, "rgba(255,255,255,0)");
  g.fillStyle = r; g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}
function yaziSprite(metin, renk = "#7f9bbd", genislik = 520) {
  const c = document.createElement("canvas"); c.width = 256; c.height = 128;
  const g = c.getContext("2d");
  g.font = "600 56px system-ui, sans-serif"; g.fillStyle = renk;
  g.textAlign = "center"; g.textBaseline = "middle"; g.fillText(metin, 128, 64);
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthWrite: false }));
  s.scale.set(genislik, genislik / 2, 1);
  return s;
}
const saydam = (renk, opaklik) => new THREE.MeshBasicMaterial({
  color: renk, transparent: true, opacity: opaklik, depthWrite: false, side: THREE.DoubleSide });

// ---------------------------------------------------------------- kurulum
function kur(hedefKutu) {
  kutu = hedefKutu;
  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  kutu.prepend(renderer.domElement);
  etiketKutu = kutu.querySelector("#sahne-etiketler");

  sahne = new THREE.Scene();
  sahne.background = new THREE.Color(RENK.arka);
  kamera = new THREE.PerspectiveCamera(45, 1, 10, 90000);
  kamera.position.copy(BASLANGIC_KAMERA);
  kontrol = new OrbitControls(kamera, renderer.domElement);
  kontrol.enableDamping = true; kontrol.dampingFactor = 0.08;
  kontrol.maxPolarAngle = Math.PI * 0.47; kontrol.minDistance = 400; kontrol.maxDistance = 32000;
  kontrol.autoRotateSpeed = 0.6;

  sahne.add(new THREE.HemisphereLight(0xbcd4ff, 0x0a1626, 1.2));
  const gunes = new THREE.DirectionalLight(0xffffff, 1.6); gunes.position.set(4000, 9000, 3000);
  sahne.add(gunes);

  zeminKur();
  nesne.daire = daireDokusu();
  nesne.sisDoku = sisDokusu();
  sisKur();

  new ResizeObserver(boyutla).observe(kutu);
  boyutla();
  requestAnimationFrame(dongu);
}

function zeminKur() {
  const zemin = new THREE.Mesh(new THREE.PlaneGeometry(18000, 18000),
    new THREE.MeshStandardMaterial({ color: RENK.zemin, roughness: 1 }));
  zemin.rotation.x = -Math.PI / 2; sahne.add(zemin);
  const saha = new THREE.Mesh(new THREE.PlaneGeometry(10000, 10000),
    new THREE.MeshStandardMaterial({ color: RENK.saha, roughness: 1 }));
  saha.rotation.x = -Math.PI / 2; saha.position.y = 0.5; sahne.add(saha);
  const ince = new THREE.GridHelper(10000, 50, RENK.izgaraInce, RENK.izgaraInce); ince.position.y = 1;
  const ana = new THREE.GridHelper(10000, 10, RENK.izgaraAna, RENK.izgaraAna); ana.position.y = 1.5;
  sahne.add(ince, ana);
  const sinir = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(
    [v3(0, 0, 2), v3(10000, 0, 2), v3(10000, 10000, 2), v3(0, 10000, 2)]),
    new THREE.LineBasicMaterial({ color: RENK.sinir }));
  sahne.add(sinir);
  for (let km = 0; km <= 10; km += 2) {
    const a = yaziSprite(`${km} km`); a.position.copy(v3(km * 1000, -420, 60)); sahne.add(a);
    if (km > 0) { const b = yaziSprite(`${km} km`); b.position.copy(v3(-520, km * 1000, 60)); sahne.add(b); }
  }
  const k = yaziSprite("K ↑", "#a9c4e6", 600); k.position.copy(v3(5000, 10550, 80)); sahne.add(k);
}

function sisKur() {
  // Sis bulutu: sahaya dağılmış yumuşak sprite'lar; sadece sis etkinken görünür
  nesne.sis = [];
  let tohum = 7;
  const rast = () => (tohum = (tohum * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 70; i++) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({
      map: nesne.sisDoku, color: RENK.sis, transparent: true, opacity: 0, depthWrite: false }));
    const boy = 1600 + rast() * 1800;
    s.scale.set(boy, boy * 0.55, 1);
    s.position.copy(v3(rast() * 11000 - 500, rast() * 11000 - 500, 60 + rast() * 380));
    s.userData = { faz: rast() * 6.28, x0: s.position.x };
    sahne.add(s); nesne.sis.push(s);
  }
  nesne.sisHedef = 0; nesne.sisSeviye = 0;
}

// ---------------------------------------------------------------- veriye bağlı nesneler
function temizle() {
  for (const ad of ["sensorler", "hedefler", "karistirici", "rotalar"]) {
    if (!nesne[ad]) continue;
    const grup = nesne[ad].grup || nesne[ad];
    grup.traverse(o => { o.geometry?.dispose?.(); });
    sahne.remove(grup);
  }
  for (const iz of Object.values(nesne.izler || {})) { iz.grup.traverse(o => o.geometry?.dispose?.()); sahne.remove(iz.grup); }
  for (const p of Object.values(nesne.olcumNokta || {})) { p.geometry.dispose(); sahne.remove(p); }
  for (const e of etiketler.values()) e.el.remove();
  etiketler.clear();
  darbeler.splice(0).forEach(d => { d.mesh.geometry.dispose(); sahne.remove(d.mesh); });
  sonOlcumT = null;
}

function veriAyarla(yeni) {
  if (!renderer || yeni === veri) return;
  temizle();
  veri = yeni;
  sensorleriKur();
  hedefleriKur();
  karistiriciKur();
  nesne.izler = {};
  nesne.olcumNokta = {};
  for (const ad of ["radar", "kamera", "konum"]) {
    const p = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({
      size: 70, map: nesne.daire, vertexColors: true, transparent: true, depthWrite: false, alphaTest: 0.02 }));
    p.userData.renk = new THREE.Color(RENK[ad]);
    sahne.add(p); nesne.olcumNokta[ad] = p;
  }
  // Takip menüsü
  const sec = document.getElementById("sahneKamera");
  if (sec) {
    sec.innerHTML = `<option value="genel">Kamera: genel bakış</option>` +
      veri.hedefler.map(h => `<option value="${h.id}">Takip: ${h.ad}</option>`).join("");
    sec.value = veri.hedefler.some(h => String(h.id) === takip) ? takip : "genel";
  }
}

function etiket(anahtar, sinif) {
  let e = etiketler.get(anahtar);
  if (!e) {
    const el = document.createElement("div"); el.className = "s3-etiket " + (sinif || "");
    etiketKutu.appendChild(el);
    // alt: etiket noktanın altında durur (hedef adları); diğerleri noktanın üstünde
    e = { el, konum: new THREE.Vector3(), gorunur: false, metin: "", alt: sinif === "hedef" };
    etiketler.set(anahtar, e);
  }
  return e;
}
function etiketYaz(e, html) { if (e.metin !== html) { e.el.innerHTML = html; e.metin = html; } }

function sensorleriKur() {
  const grup = new THREE.Group(); nesne.sensorler = { grup };
  for (const ad of ["radar", "kamera"]) {
    const s = veri.sensorler[ad], p = v3(s.konum[0], s.konum[1]), h = DIREK[ad];
    const direkMalz = new THREE.MeshStandardMaterial({ color: RENK.direk, roughness: 0.6, metalness: 0.3 });
    const direk = new THREE.Mesh(new THREE.CylinderGeometry(22, 48, h, 12), direkMalz);
    direk.position.set(p.x, h / 2, p.z);
    const basMalz = new THREE.MeshStandardMaterial({ color: RENK[ad], emissive: RENK[ad], emissiveIntensity: 0.5 });
    const bas = new THREE.Mesh(ad === "radar" ? new THREE.BoxGeometry(240, 70, 26) : new THREE.BoxGeometry(80, 56, 100), basMalz);
    bas.position.set(p.x, h + 30, p.z);
    const halka = new THREE.Mesh(new THREE.RingGeometry(0.988, 1, 160).rotateX(-Math.PI / 2), saydam(RENK[ad], 0.85));
    halka.position.set(p.x, 3, p.z);
    grup.add(direk, bas, halka);
    const o = { direk, bas, basMalz, halka, h, p };
    if (ad === "radar") {
      const kubbeGeo = new THREE.SphereGeometry(1, 48, 16, 0, Math.PI * 2, 0, Math.PI / 2);
      o.kubbe = new THREE.Mesh(kubbeGeo, saydam(RENK.radar, 0.035));
      o.kubbe.position.set(p.x, 0, p.z); grup.add(o.kubbe);
      // Kubbenin biçimini belli eden iki yükseklik halkası (kubbe yüksekliği görseldir)
      o.kafes = new THREE.Group(); o.kafes.position.set(p.x, 0, p.z);
      for (const oran of [0.45, 0.8]) {
        const h = new THREE.Mesh(new THREE.RingGeometry(0.994, 1, 128).rotateX(-Math.PI / 2), saydam(RENK.radar, 0.22));
        h.scale.setScalar(Math.sqrt(1 - oran * oran)); h.position.y = oran; o.kafes.add(h);
      }
      grup.add(o.kafes);
      // Dönen tarama ışını: önde parlak dilim, arkasında sönen iz
      o.tarama = new THREE.Group(); o.tarama.position.set(p.x, 4, p.z);
      [0.2, 0.1, 0.05, 0.025].forEach((op, i) => {
        const dilim = new THREE.Mesh(new THREE.CircleGeometry(1, 32, -i * 0.22, 0.22).rotateX(-Math.PI / 2),
          saydam(RENK.radar, op));
        o.tarama.add(dilim);
      });
      grup.add(o.tarama);
    } else {
      o.koni = new THREE.Mesh(new THREE.ConeGeometry(1, 1, 96, 1, true), saydam(RENK.kamera, 0.06));
      o.koni.position.set(p.x, h / 2, p.z); o.koni.scale.y = h;
      grup.add(o.koni);
    }
    nesne.sensorler[ad] = o;
  }
  sahne.add(grup);
}

function ihaModeli(malz) {
  const g = new THREE.Group();
  const govde = new THREE.Mesh(new THREE.CylinderGeometry(16, 22, 190, 10).rotateZ(Math.PI / 2), malz);
  const kanat = new THREE.Mesh(new THREE.BoxGeometry(46, 7, 280), malz);
  const kuyruk = new THREE.Mesh(new THREE.BoxGeometry(28, 7, 100), malz); kuyruk.position.x = -85;
  const dik = new THREE.Mesh(new THREE.BoxGeometry(30, 50, 6), malz); dik.position.set(-88, 26, 0);
  g.add(govde, kanat, kuyruk, dik);
  return g;
}
function aracModeli(malz) {
  const g = new THREE.Group();
  const kasa = new THREE.Mesh(new THREE.BoxGeometry(160, 50, 80), malz); kasa.position.y = 40;
  const kabin = new THREE.Mesh(new THREE.BoxGeometry(70, 40, 70), malz); kabin.position.set(30, 85, 0);
  g.add(kasa, kabin);
  return g;
}
function insanModeli(malz) {
  const g = new THREE.Group();
  [[0, 0], [60, 40], [-50, 45], [20, -55]].forEach(([x, z]) => {
    const k = new THREE.Mesh(new THREE.CapsuleGeometry(18, 55, 4, 8), malz); k.position.set(x, 50, z); g.add(k);
  });
  return g;
}

function hedefleriKur() {
  const grup = new THREE.Group(); nesne.hedefler = { grup, liste: [] };
  const rotalar = new THREE.Group(); nesne.rotalar = rotalar;
  for (const h of veri.hedefler) {
    const malz = new THREE.MeshStandardMaterial({ color: RENK.gercek, roughness: 0.45, metalness: 0.2,
      emissive: 0x334455, emissiveIntensity: 0.6 });
    const model = h.hava ? ihaModeli(malz) : /insan/i.test(h.ad) ? insanModeli(malz) : aracModeli(malz);
    const govde = new THREE.Group(); govde.add(model); grup.add(govde);
    const o = { h, govde, model, irtifa: h.hava ? HAVA_IRTIFA : 0 };
    if (h.hava) {
      o.cizgi = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3(0, -1, 0)]),
        new THREE.LineBasicMaterial({ color: RENK.gercek, transparent: true, opacity: 0.55 }));
      o.golge = new THREE.Mesh(new THREE.CircleGeometry(80, 24).rotateX(-Math.PI / 2), saydam(0x000000, 0.45));
      grup.add(o.cizgi, o.golge);
    }
    const noktalar = h.rota.map(([x, y]) => v3(x, y, o.irtifa + 2));
    rotalar.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(noktalar),
      new THREE.LineBasicMaterial({ color: RENK.rota, transparent: true, opacity: 0.55 })));
    nesne.hedefler.liste.push(o);
  }
  sahne.add(grup, rotalar);
}

function karistiriciKur() {
  nesne.karistirici = null;
  if (!veri.karistirici) return;
  const grup = new THREE.Group(), p = v3(...veri.karistirici);
  grup.position.copy(p);
  const malz = new THREE.MeshStandardMaterial({ color: 0x8a2a2a, emissive: RENK.karistirma, emissiveIntensity: 0.4 });
  const direk = new THREE.Mesh(new THREE.CylinderGeometry(18, 40, 160, 10), malz); direk.position.y = 80;
  const anten = new THREE.Mesh(new THREE.OctahedronGeometry(45), malz); anten.position.y = 190;
  // Yanlış alarmların %70'i karıştırıcı çevresinde ~1.2 km'lik bir bulutta yoğunlaşır
  const bulut = new THREE.Mesh(new THREE.SphereGeometry(1200, 40, 16, 0, Math.PI * 2, 0, Math.PI / 2),
    saydam(RENK.karistirma, 0.0));
  const dalgalar = [0, 1, 2].map(() => {
    const d = new THREE.Mesh(new THREE.RingGeometry(0.97, 1, 96).rotateX(-Math.PI / 2), saydam(RENK.karistirma, 0));
    d.position.y = 6; grup.add(d); return d;
  });
  grup.add(direk, anten, bulut);
  sahne.add(grup);
  nesne.karistirici = { grup, malz, bulut, dalgalar, etkin: false };
}

// ---------------------------------------------------------------- güncelleme (zaman değişince)
function konumAt(rota, t) {
  const i0 = Math.min(Math.floor(t), rota.length - 1), i1 = Math.min(i0 + 1, rota.length - 1), f = t - i0;
  const a = rota[i0], b = rota[i1];
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, b[0] - a[0], b[1] - a[1]];
}

function guncelle(d) {
  if (!renderer || !veri) return;
  durum = d;
  const { t, katman } = d, sn = Math.min(veri.sure, Math.max(0, Math.round(t)));
  const sd = veri.durum[sn], kare = d.kareler[Math.floor(t)] || d.kareler[sn];

  // Sensörler
  for (const ad of ["radar", "kamera"]) {
    const o = nesne.sensorler[ad], s = sd[ad], aktif = s.aktif;
    const renk = aktif ? RENK[ad] : RENK.kapali;
    o.basMalz.color.setHex(renk); o.basMalz.emissive.setHex(renk);
    o.halka.material.color.setHex(renk); o.halka.material.opacity = aktif ? 0.85 : 0.35;
    o.halka.scale.setScalar(s.menzil); o.halka.visible = katman.menzil;
    if (o.kubbe) {
      o.kubbe.scale.set(s.menzil, 1100, s.menzil); o.kafes.scale.copy(o.kubbe.scale);
      const karistirma = s.etiket === "KARIŞTIRMA", kubbeRenk = karistirma ? RENK.karistirma : renk;
      o.kubbe.material.opacity = aktif ? (karistirma ? 0.07 : 0.035) : 0.012;
      o.kubbe.material.color.setHex(kubbeRenk);
      o.kafes.children.forEach(h => { h.material.color.setHex(kubbeRenk); h.material.opacity = aktif ? 0.22 : 0.08; });
      o.kubbe.visible = o.kafes.visible = katman.menzil;
      o.tarama.scale.set(s.menzil, 1, s.menzil); o.tarama.visible = aktif && katman.menzil;
    } else {
      o.koni.scale.set(s.menzil, o.h, s.menzil); o.koni.material.opacity = aktif ? 0.06 : 0.015;
      o.koni.visible = katman.menzil;
    }
    o.aktif = aktif;
    const g = kare && kare.guven[ad];
    const e = etiket("sensor-" + ad, "sensor");
    e.konum.set(o.p.x, o.h + 420, o.p.z); e.gorunur = katman.etiket;
    etiketYaz(e, `<b style="color:#${new THREE.Color(RENK[ad]).getHexString()}">${ad === "radar" ? "Radar" : "Kamera"}</b> ${s.etiket}` +
      (g !== undefined ? ` · güven ${g.toFixed(2)}` : ""));
  }
  nesne.sisHedef = sd.kamera.etiket === "SİS" ? 1 : 0;
  if (nesne.karistirici) {
    const k = nesne.karistirici; k.etkin = sd.radar.etiket === "KARIŞTIRMA";
    const e = etiket("karistirici", "tehdit");
    e.konum.copy(k.grup.position).setY(300); e.gorunur = katman.etiket;
    etiketYaz(e, `Karıştırıcı${k.etkin ? " · <b>etkin</b>" : ""}`);
  }

  // Gerçek hedefler
  for (const o of nesne.hedefler.liste) {
    const [x, y, dx, dy] = konumAt(o.h.rota, t), p = v3(x, y, o.irtifa);
    o.govde.position.copy(p);
    if (dx || dy) o.govde.rotation.y = Math.atan2(dy, dx);
    if (o.cizgi) {
      o.cizgi.position.copy(p); o.cizgi.scale.y = o.irtifa;
      o.golge.position.set(p.x, 2, p.z);
    }
    const e = etiket("hedef-" + o.h.id, "hedef");
    e.konum.set(p.x, p.y, p.z); e.gorunur = katman.etiket;
    etiketYaz(e, o.h.ad);
  }
  nesne.rotalar.visible = katman.rota;

  // Ölçümler (son 3 saniye; yeni olanlar daha belirgin)
  for (const ad of ["radar", "kamera", "konum"]) {
    const p = nesne.olcumNokta[ad], dizi = veri.olcumler[ad];
    p.visible = katman[ad];
    if (!p.visible) continue;
    let lo = 0, hi = dizi.length;
    while (lo < hi) { const m = (lo + hi) >> 1; if (dizi[m][0] < t - OLCUM_PENCERE) lo = m + 1; else hi = m; }
    const konum = [], renk = [], c = p.userData.renk;
    for (let i = lo; i < dizi.length && dizi[i][0] <= t; i++) {
      const [ti, x, y] = dizi[i], a = 0.25 + 0.75 * (1 - (t - ti) / OLCUM_PENCERE);
      konum.push(x - MERKEZ, 10, MERKEZ - y); renk.push(c.r, c.g, c.b, a);
    }
    p.geometry.dispose();
    p.geometry = new THREE.BufferGeometry();
    p.geometry.setAttribute("position", new THREE.Float32BufferAttribute(konum, 3));
    p.geometry.setAttribute("color", new THREE.Float32BufferAttribute(renk, 4));
  }
  konumDarbeleri(t, katman.konum);

  izleriGuncelle(d);
}

function konumDarbeleri(t, acik) {
  // Yeni gelen konum bildirimleri, dost birliğin üstünde genişleyen mor halkalarla gösterilir
  const dizi = veri.olcumler.konum;
  if (sonOlcumT !== null && t > sonOlcumT && t - sonOlcumT < 3 && acik) {
    for (const [ti, x, y] of dizi) {
      if (ti > sonOlcumT && ti <= t && darbeler.length < 12) {
        const m = new THREE.Mesh(new THREE.RingGeometry(0.9, 1, 64).rotateX(-Math.PI / 2), saydam(RENK.konum, 0.9));
        m.position.copy(v3(x, y, 8)); sahne.add(m);
        darbeler.push({ mesh: m, bas: saat() });
      }
    }
  }
  sonOlcumT = t;
}

function serit(noktalar, renk, genislik) {
  // Zemin üstünde, eskiden yeniye doğru belirginleşen yassı iz şeridi
  const n = noktalar.length, konum = [], renkler = [], indeks = [];
  for (let i = 0; i < n; i++) {
    const a = noktalar[Math.max(0, i - 1)], b = noktalar[Math.min(n - 1, i + 1)];
    let tx = b.x - a.x, tz = b.z - a.z; const l = Math.hypot(tx, tz) || 1; tx /= l; tz /= l;
    const p = noktalar[i], w = genislik * (0.35 + 0.65 * i / Math.max(1, n - 1));
    konum.push(p.x - tz * w, p.y, p.z + tx * w, p.x + tz * w, p.y, p.z - tx * w);
    const a2 = Math.pow(i / Math.max(1, n - 1), 1.3) * 0.9;
    renkler.push(renk.r, renk.g, renk.b, a2, renk.r, renk.g, renk.b, a2);
    if (i < n - 1) { const k = 2 * i; indeks.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(konum, 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute(renkler, 4));
  g.setIndex(indeks);
  return g;
}

function izleriGuncelle(d) {
  const { t, katman, kareler, kuyruklar } = d;
  const i0 = Math.floor(t), f = t - i0, kare = kareler[i0], sonraki = kareler[i0 + 1];
  const aktif = new Set();
  if (kare && katman.iz) {
    const sonrakiler = new Map((sonraki ? sonraki.izler : []).map(iz => [iz[0], iz]));
    for (const iz of kare.izler) {
      const [id, x, y, vx, vy, skor, sens, dost, mu] = iz;
      const s2 = sonrakiler.get(id);
      const px = s2 ? x + (s2[1] - x) * f : x + vx * f, py = s2 ? y + (s2[2] - y) * f : y + vy * f;
      let o = nesne.izler[id];
      if (!o) {
        const grup = new THREE.Group();
        const malz = new THREE.MeshStandardMaterial({ emissiveIntensity: 0.9, roughness: 0.3 });
        const isaret = new THREE.Mesh(new THREE.OctahedronGeometry(70), malz);
        const sap = new THREE.Mesh(new THREE.CylinderGeometry(5, 5, 90, 6), malz);
        const donus = new THREE.Mesh(new THREE.TorusGeometry(120, 9, 8, 48).rotateX(Math.PI / 2),
          new THREE.MeshBasicMaterial({ color: RENK.donus, transparent: true, opacity: 0.9 }));
        const seritMesh = new THREE.Mesh(new THREE.BufferGeometry(), new THREE.MeshBasicMaterial({
          vertexColors: true, transparent: true, depthWrite: false, side: THREE.DoubleSide }));
        const imlec = new THREE.Group(); imlec.add(isaret, sap, donus);
        isaret.position.y = 150; sap.position.y = 70; donus.position.y = 150;
        grup.add(imlec); sahne.add(grup, seritMesh);
        o = nesne.izler[id] = { grup, imlec, isaret, malz, donus, seritMesh };
      }
      aktif.add(id);
      const renk = new THREE.Color(dost ? RENK.dost : RENK.dusman);
      o.malz.color.copy(renk); o.malz.emissive.copy(renk);
      o.grup.visible = o.seritMesh.visible = true;
      o.imlec.position.copy(v3(px, py, 0));
      o.donus.visible = !!(mu && mu[1] > 0.5);
      const kuyruk = (kuyruklar[id] || []).filter(p => p[0] > t - IZ_KUYRUK && p[0] <= i0)
        .map(p => v3(p[1], p[2], 6));
      kuyruk.push(v3(px, py, 6));
      o.seritMesh.geometry.dispose();
      o.seritMesh.geometry = kuyruk.length > 1 ? serit(kuyruk, renk, 70 * olcek) : new THREE.BufferGeometry();
      const e = etiket("iz-" + id, dost ? "dost" : "diger");
      e.konum.set(o.imlec.position.x, 330 * olcek, o.imlec.position.z); e.gorunur = katman.etiket;
      const model = mu ? (mu[1] > 0.5 ? ` · <span class="donus">dönüş %${Math.round(mu[1] * 100)}</span>` : "") : "";
      etiketYaz(e, `T${id} ${skor.toFixed(2)} [${sens.map(s => ({ radar: "R", kamera: "K", konum: "B" })[s]).join(",") || "-"}]${model}`);
    }
  }
  for (const [id, o] of Object.entries(nesne.izler || {})) {
    if (aktif.has(Number(id))) continue;
    o.grup.visible = o.seritMesh.visible = false;
    const e = etiketler.get("iz-" + id); if (e) e.gorunur = false;
  }
}

// ---------------------------------------------------------------- çizim döngüsü
function boyutla() {
  const w = kutu.clientWidth, h = kutu.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h);
  kamera.aspect = w / h; kamera.updateProjectionMatrix();
}

const gecici = new THREE.Vector3();
let sonKare = performance.now();
function dongu(simdi) {
  requestAnimationFrame(dongu);
  if (gorunur && !kayit) kareCiz(simdi);
}

function kareCiz(simdi) {
  const dt = Math.min(0.1, Math.max(0, simdi - sonKare) / 1000); sonKare = simdi;

  // Takip modu: kamera, seçilen hedefle birlikte kayar
  if (takip !== "genel" && nesne.hedefler) {
    const o = nesne.hedefler.liste.find(o => String(o.h.id) === takip);
    if (o) {
      gecici.copy(o.govde.position).sub(kontrol.target);
      kontrol.target.add(gecici); kamera.position.add(gecici);
    }
  }
  kontrol.update();

  // Uzaklaştıkça semboller büyür, yakınlaşınca küçülür (okunabilirlik için)
  olcek = THREE.MathUtils.clamp(kamera.position.distanceTo(kontrol.target) / 9000, 0.28, 1.6);
  for (const o of nesne.hedefler?.liste || []) o.model.scale.setScalar(olcek);
  for (const o of Object.values(nesne.izler || {})) o.imlec.scale.setScalar(olcek);
  for (const p of Object.values(nesne.olcumNokta || {})) p.material.size = 75 * olcek;

  // Radar taraması (görsel; gerçek tarama hızı 1 Hz)
  const r = nesne.sensorler?.radar;
  if (r) { r.tarama.rotation.y -= dt * 2.4; if (r.aktif) r.bas.rotation.y -= dt * 2.4; }
  for (const o of Object.values(nesne.izler || {})) o.donus.rotation.z += dt * 3;

  // Sis
  nesne.sisSeviye += (nesne.sisHedef - nesne.sisSeviye) * Math.min(1, dt * 2);
  for (const s of nesne.sis) {
    s.material.opacity = 0.2 * nesne.sisSeviye;
    s.visible = nesne.sisSeviye > 0.01;
    s.position.x = s.userData.x0 + Math.sin(simdi / 9000 + s.userData.faz) * 250;
  }

  // Karıştırıcı dalgaları
  const k = nesne.karistirici;
  if (k) {
    k.bulut.material.opacity += ((k.etkin ? 0.08 + 0.04 * Math.sin(simdi / 180) : 0) - k.bulut.material.opacity) * Math.min(1, dt * 4);
    k.malz.emissiveIntensity = k.etkin ? 0.6 + 0.4 * Math.sin(simdi / 120) : 0.15;
    k.dalgalar.forEach((d, i) => {
      const faz = ((simdi / 1600) + i / 3) % 1;
      d.scale.setScalar(100 + faz * 2600);
      d.material.opacity = k.etkin ? 0.7 * (1 - faz) : 0;
    });
  }

  // Konum bildirimi darbeleri
  for (let i = darbeler.length - 1; i >= 0; i--) {
    const d = darbeler[i], yas = (simdi - d.bas) / 1200;
    if (yas >= 1) { d.mesh.geometry.dispose(); sahne.remove(d.mesh); darbeler.splice(i, 1); continue; }
    d.mesh.scale.setScalar((60 + yas * 420) * Math.max(olcek, 0.5));
    d.mesh.material.opacity = 0.9 * (1 - yas);
  }

  renderer.render(sahne, kamera);

  // HTML etiketleri ekrana yansıt
  const w = kutu.clientWidth, h = kutu.clientHeight;
  for (const e of etiketler.values()) {
    if (!e.gorunur) { e.el.style.display = "none"; continue; }
    gecici.copy(e.konum).project(kamera);
    if (gecici.z > 1 || Math.abs(gecici.x) > 1.1 || Math.abs(gecici.y) > 1.1) { e.el.style.display = "none"; continue; }
    e.el.style.display = "";
    e.el.style.transform = `translate(${((gecici.x + 1) / 2 * w).toFixed(1)}px, ${((1 - gecici.y) / 2 * h).toFixed(1)}px) ` +
      (e.alt ? "translate(-50%, 14px)" : "translate(-50%, -100%)");
  }
}

// ---------------------------------------------------------------- dış arayüz
function kameraSifirla() {
  takip = "genel";
  const sec = document.getElementById("sahneKamera"); if (sec) sec.value = "genel";
  kontrol.target.set(0, 0, 0); kamera.position.copy(BASLANGIC_KAMERA);
}
function takipSec(deger) {
  if (deger === "genel") { kameraSifirla(); return; }
  takip = deger;
  const o = nesne.hedefler?.liste.find(o => String(o.h.id) === deger);
  if (o) {
    kontrol.target.copy(o.govde.position);
    kamera.position.copy(o.govde.position).add(new THREE.Vector3(-1400, 1100, 1600));
  }
}

window.sahne3d = {
  goster(hedefKutu) {
    if (!renderer) kur(hedefKutu);
    gorunur = true; boyutla();
  },
  gizle() { gorunur = false; },
  veriAyarla,
  guncelle,
  kameraSifirla,
  takipSec,
  otomatikDonus(acik) { if (kontrol) kontrol.autoRotate = acik; },
  // Kayıt modu: kare(ms) çağrıldığında sahne o sanal ana göre bir kez çizilir
  kayitModu(acik) { kayit = acik; sanalSaat = 0; sonKare = 0; },
  kayitKaresi(ms) { sanalSaat = ms; kareCiz(ms); },
  kameraAyarla(konum, hedef) {
    takip = "genel";
    kamera.position.set(...konum); kontrol.target.set(...hedef); kontrol.update();
  },
};
window.dispatchEvent(new Event("sahne3d-hazir"));
