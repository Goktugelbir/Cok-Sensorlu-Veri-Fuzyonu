"""Görselleştirme: harita animasyonu (GIF), karşılaştırma grafiği ve özet figür."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from PIL import Image

from .saha import SAHA_BOYUTU
from .sensorler import SENSORLER, sensor_durumu

# Renkler (sabit sırayla atanır; aynı varlık her figürde aynı rengi taşır)
RENK = {
    "fuzyon": "#2a78d6", "radar": "#eb6834", "kamera": "#1baf7a", "konum": "#4a3aa7",
    "dost": "#2a78d6", "dusman": "#e34948",
    "gercek": "#c3c2b7", "metin": "#0b0b0b", "ikincil": "#52514e", "izgara": "#e1e0d9",
    "zemin": "#fcfcfb",
}
SENSOR_ETIKET = {"radar": "Radar", "kamera": "EO/termal kamera", "konum": "Konum bildirimi"}
KISALTMA = {"radar": "R", "kamera": "K", "konum": "B"}
KONFIG_ETIKET = {"radar": "Sadece radar", "kamera": "Sadece kamera",
                 "konum": "Sadece konum bildirimi", "fuzyon": "Füzyon"}
KONFIG_RENK = {"fuzyon": RENK["fuzyon"], "radar": RENK["radar"],
               "kamera": RENK["kamera"], "konum": RENK["konum"]}


def _eksen_hazirla(ax):
    ax.set_facecolor(RENK["zemin"])
    ax.set_xlim(0, SAHA_BOYUTU / 1000)
    ax.set_ylim(0, SAHA_BOYUTU / 1000)
    ax.set_aspect("equal")
    ax.grid(color=RENK["izgara"], linewidth=0.6)
    ax.tick_params(colors=RENK["ikincil"], labelsize=8)
    for k in ax.spines.values():
        k.set_color(RENK["izgara"])
    ax.set_xlabel("x (km)", color=RENK["ikincil"], fontsize=8)
    ax.set_ylabel("y (km)", color=RENK["ikincil"], fontsize=8)


def _gercek_rotalar(ax, hedefler, t=None):
    for h in hedefler:
        ax.plot(h.konum[:, 0] / 1000, h.konum[:, 1] / 1000, color=RENK["gercek"], lw=1.0, zorder=1)
        if t is not None:
            p = h.konum_at(t) / 1000
            ax.plot(*p, "o", color=RENK["ikincil"], ms=4, zorder=2)


def _iz_gecmisleri(gecmis, t_bas=-np.inf, t_son=np.inf):
    """iz_id -> (zamanlar, konumlar, dost) sözlüğü."""
    izler = {}
    for t, resim, _ in gecmis:
        if not (t_bas <= t <= t_son):
            continue
        for iz in resim:
            k = izler.setdefault(iz["id"], {"t": [], "p": [], "dost": False})
            k["t"].append(t)
            k["p"].append(iz["konum"])
            k["dost"] = k["dost"] or iz["dost"]
    return izler


def gif_olustur(senaryo, hedefler, olcumler, gecmis, yol, kare_araligi=3.0, iz_kuyrugu=40.0):
    """Füzyon sonucunun harita animasyonunu GIF olarak kaydeder."""
    fig, ax = plt.subplots(figsize=(6.4, 6.8), dpi=80)
    fig.patch.set_facecolor(RENK["zemin"])
    kareler = []
    zamanlar = {t: (resim, guven) for t, resim, guven in gecmis}
    tum_olcum = [o for s in olcumler for o in olcumler[s]]
    olcum_t = np.array([o.t_olcum for o in tum_olcum])

    for t in sorted(zamanlar):
        if t % kare_araligi > 1e-6 or t == 0:
            continue
        resim, guven = zamanlar[t]
        ax.clear()
        _eksen_hazirla(ax)
        _gercek_rotalar(ax, hedefler, t)

        # Sensör menzil daireleri
        for ad in ("radar", "kamera"):
            s = SENSORLER[ad]
            d = sensor_durumu(senaryo, ad, t)
            stil = "--" if d["aktif"] else ":"
            renk = RENK[ad] if d["aktif"] else RENK["ikincil"]
            ax.add_patch(plt.Circle(s.konum / 1000, d["menzil"] / 1000, fill=False,
                                    ls=stil, lw=1.2, color=renk, zorder=1))
            ax.plot(*(s.konum / 1000), marker="^", color=renk, ms=8, zorder=3)

        # Son 3 saniyenin ham ölçümleri
        secili = np.where((olcum_t > t - 3.0) & (olcum_t <= t))[0]
        for ad in SENSORLER:
            pts = np.array([tum_olcum[i].z for i in secili if tum_olcum[i].sensor == ad]).reshape(-1, 2)
            if len(pts):
                ax.scatter(pts[:, 0] / 1000, pts[:, 1] / 1000, s=9, color=RENK[ad], alpha=0.8,
                           linewidths=0, zorder=5)

        # Füzyon izleri: kalın çizgi + ID + güven skoru + destekleyen sensörler
        kuyruk = _iz_gecmisleri(gecmis, t - iz_kuyrugu, t)
        for iz in resim:
            k = kuyruk[iz["id"]]
            p = np.array(k["p"]) / 1000
            renk = RENK["dost"] if iz["dost"] else RENK["dusman"]
            ax.plot(p[:, 0], p[:, 1], color=renk, lw=3.0, solid_capstyle="round", zorder=4)
            sens = ",".join(KISALTMA[s] for s in iz["sensorler"]) or "-"
            ax.text(p[-1, 0] + 0.12, p[-1, 1] + 0.12, f"T{iz['id']} {iz['skor']:.2f} [{sens}]",
                    fontsize=7.5, color=RENK["metin"], zorder=5,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec=renk, lw=0.8, alpha=0.85))

        # Başlık ve sensör durumu
        durumlar = []
        for ad in SENSORLER:
            d = sensor_durumu(senaryo, ad, t)
            not_ = "KAPALI" if not d["aktif"] else ("KARIŞTIRMA" if d["karistirma"] else
                                                    ("SİS" if d["gurultu_carpani"] > 1 else "açık"))
            durumlar.append(f"{SENSOR_ETIKET[ad]}: {not_} (güven {guven.get(ad, 1):.2f})")
        ax.set_title(f"Senaryo: {senaryo}   t = {t:.0f} s", fontsize=11, color=RENK["metin"], loc="left")
        ax.text(0.0, -0.13, "\n".join(durumlar), transform=ax.transAxes, fontsize=7.5,
                color=RENK["ikincil"], va="top")

        lejant = [
            Line2D([], [], color=RENK["gercek"], lw=1.2, label="Gerçek rota"),
            Line2D([], [], color=RENK["dost"], lw=3, label="Füzyon izi (dost)"),
            Line2D([], [], color=RENK["dusman"], lw=3, label="Füzyon izi (diğer)"),
        ] + [Line2D([], [], ls="", marker="o", ms=4, color=RENK[ad], label=SENSOR_ETIKET[ad])
             for ad in SENSORLER]
        ax.legend(handles=lejant, loc="upper right", bbox_to_anchor=(1.0, -0.11), ncol=2, fontsize=7,
                  frameon=False)
        fig.subplots_adjust(left=0.1, right=0.97, top=0.94, bottom=0.2)

        fig.canvas.draw()
        kareler.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba())[..., :3]).quantize(
            colors=128, method=Image.Quantize.MEDIANCUT))
    plt.close(fig)
    kareler[0].save(yol, save_all=True, append_images=kareler[1:], duration=150, loop=0, optimize=True)


def karsilastirma_grafigi(sonuclar, yol):
    """sonuclar[senaryo][konfig] = ölçüt sözlüğü -> 2x2 gruplu çubuk grafik."""
    senaryolar = list(sonuclar)
    konfigler = ["fuzyon", "radar", "kamera", "konum"]
    olcutler = [("rmse", "RMSE (m) — düşük iyi"), ("kacirma", "Kaçırma oranı (%) — düşük iyi"),
                ("yanlis_iz", "Yanlış iz sayısı — düşük iyi"), ("id_switch", "ID switch sayısı — düşük iyi")]
    fig, eksenler = plt.subplots(2, 2, figsize=(11, 7), dpi=110)
    fig.patch.set_facecolor(RENK["zemin"])
    genislik = 0.2
    x = np.arange(len(senaryolar))
    for ax, (anahtar, baslik) in zip(eksenler.flat, olcutler):
        ax.set_facecolor(RENK["zemin"])
        for i, k in enumerate(konfigler):
            deger = np.array([sonuclar[s][k][anahtar] for s in senaryolar], float)
            if anahtar == "kacirma":
                deger = deger * 100
            ax.bar(x + (i - 1.5) * genislik, deger, genislik * 0.9, color=KONFIG_RENK[k],
                   label=KONFIG_ETIKET[k], zorder=2)
        ax.set_xticks(x, senaryolar, fontsize=9, color=RENK["metin"])
        ax.set_title(baslik, fontsize=10, color=RENK["metin"], loc="left")
        ax.grid(axis="y", color=RENK["izgara"], lw=0.6, zorder=0)
        ax.tick_params(axis="y", colors=RENK["ikincil"], labelsize=8)
        for k in ("top", "right"):
            ax.spines[k].set_visible(False)
        for k in ("left", "bottom"):
            ax.spines[k].set_color(RENK["gercek"])
        if anahtar in ("yanlis_iz", "id_switch"):
            # Sayma ölçütleri: tamsayı eksen, sıfırdan başlar (hepsi sıfırsa da okunur kalır)
            ax.yaxis.get_major_locator().set_params(integer=True)
            ax.set_ylim(0, max(ax.get_ylim()[1], 1))
            if all(sonuclar[s][k][anahtar] == 0 for s in senaryolar for k in konfigler):
                ax.text(0.5, 0.5, "Hiçbir senaryo ve konfigürasyonda oluşmadı (tümü 0)",
                        transform=ax.transAxes, ha="center", fontsize=9, color=RENK["ikincil"])
    tutamac, etiket = eksenler[0, 0].get_legend_handles_labels()
    fig.legend(tutamac, etiket, loc="upper right", ncol=4, fontsize=9, frameon=False)
    fig.suptitle("Füzyon ve tek sensör karşılaştırması", fontsize=12, color=RENK["metin"], x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(yol, facecolor=fig.get_facecolor())
    plt.close(fig)


def ozet_figur(hedefler, veriler, yol):
    """Tek bakışta özet: her satır bir senaryo; sütunlar ham ölçümler, tek sensörler, füzyon.

    veriler: [(senaryo, olcumler, {konfig: gecmis}, {konfig: ölçütler}, açıklama), ...]
    """
    sutunlar = ["ham", "radar", "kamera", "konum", "fuzyon"]
    fig, eksenler = plt.subplots(len(veriler), len(sutunlar), figsize=(17, 4.2 * len(veriler)), dpi=90)
    fig.patch.set_facecolor(RENK["zemin"])
    eksenler = np.atleast_2d(eksenler)
    for r, (senaryo, olcumler, gecmisler, metrikler, aciklama) in enumerate(veriler):
        for c, sutun in enumerate(sutunlar):
            ax = eksenler[r, c]
            _eksen_hazirla(ax)
            _gercek_rotalar(ax, hedefler)
            if sutun == "ham":
                for ad, liste in olcumler.items():
                    pts = np.array([o.z for o in liste]).reshape(-1, 2)
                    ax.scatter(pts[:, 0] / 1000, pts[:, 1] / 1000, s=1, color=RENK[ad], alpha=0.25,
                               linewidths=0, label=SENSOR_ETIKET[ad])
                ax.set_title(f"{senaryo}: ham ölçümler", fontsize=9, loc="left", color=RENK["metin"])
                if r == 0:
                    ax.legend(fontsize=7, markerscale=6, loc="upper right")
                continue
            for k in _iz_gecmisleri(gecmisler[sutun]).values():
                p = np.array(k["p"]) / 1000
                ax.plot(p[:, 0], p[:, 1], lw=2.0, color=RENK["dost"] if k["dost"] else RENK["dusman"])
            m = metrikler[sutun]
            ax.set_title(f"{KONFIG_ETIKET[sutun]}\nRMSE {m['rmse']:.1f} m · kaçırma %{100 * m['kacirma']:.0f}"
                         f" · ID sw. {m['id_switch']}", fontsize=9, loc="left", color=RENK["metin"])
        eksenler[r, 0].annotate(aciklama, xy=(0, 1.2), xycoords="axes fraction", fontsize=10,
                                fontweight="bold", color=RENK["metin"])
    fig.subplots_adjust(left=0.04, right=0.99, top=0.88, bottom=0.07, wspace=0.25, hspace=0.55)
    fig.savefig(yol, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
