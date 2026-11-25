// Alt çekmece: alttan açılan, sürüklenebilen yüzen panel.
// 21st.dev "Drawer" (wensity) bileşeninin davranışından düz JS'e uyarlandı:
// tutamaç, aşağı sürükleyince kapanma, 500/250 ms açılış/kapanış, odak tuzağı, × düğmesi.
//
// Üç hâl: "kapali", "kisa" (yalnız başlık ve iki satır görünür), "tam".

const KISA_GORUNEN = 132; // kısa hâlde görünen yükseklik (px)
const KAPATMA_ORANI = 0.3; // yüksekliğin %30'undan fazla aşağı çekilirse bir hâl aşağı iner
const HIZLI = 0.6; // px/ms: bundan hızlı fiske de aynı sayılır
const ODAKLANABILIR = 'button, [href], input, [tabindex]:not([tabindex="-1"])';

export function cekmeceKur(kok) {
  const arka = document.createElement("div");
  arka.className = "cekmece-arka";
  const panel = document.createElement("section");
  panel.className = "cekmece";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", "Ayrıntı");
  panel.dataset.durum = "kapali";
  panel.innerHTML = '<div class="tutamac" aria-hidden="true"><span></span></div>' +
    '<button type="button" class="kapat" aria-label="Kapat">×</button><div class="govde"></div>';
  kok.append(arka, panel);
  const govde = panel.querySelector(".govde");

  // Kısa hâlde panelin ne kadar aşağıda duracağı
  const kisaKayma = () => Math.max(0, panel.offsetHeight - KISA_GORUNEN);

  function durumYap(durum) {
    panel.dataset.durum = durum;
    arka.classList.toggle("gorunur", durum === "tam");
    panel.style.removeProperty("--surukle");
    panel.style.setProperty("--kisa-kayma", kisaKayma() + "px");
    panel.setAttribute("aria-modal", String(durum === "tam"));
    if (durum === "tam") panel.querySelector(".kapat").focus({ preventScroll: true });
  }

  const api = {
    ac(icerik, { tam = false } = {}) {
      govde.replaceChildren(icerik);
      govde.scrollTop = 0;
      // Önce kapalı yerden başlasın ki kayarak gelsin
      if (panel.dataset.durum === "kapali") panel.style.setProperty("--kisa-kayma", kisaKayma() + "px");
      void panel.offsetWidth; // kapalı konumdan kayarak gelsin
      durumYap(tam ? "tam" : "kisa");
    },
    tamYap: () => durumYap("tam"),
    kisalt: () => durumYap("kisa"),
    kapat: () => durumYap("kapali"),
    acikMi: () => panel.dataset.durum !== "kapali",
    durum: () => panel.dataset.durum,
  };

  panel.querySelector(".kapat").onclick = () => api.kapat();
  arka.onclick = () => api.kisalt();

  // Kısa hâldeyken başlığa dokunmak paneli açar
  govde.addEventListener("click", (olay) => {
    if (panel.dataset.durum === "kisa" && !olay.target.closest("button")) api.tamYap();
  });

  // Sürükleme: tutamaçtan (ya da kısa hâlde panelin herhangi bir yerinden)
  let baslangic = null;
  panel.addEventListener("pointerdown", (olay) => {
    const tutamactan = olay.target.closest(".tutamac");
    if (!tutamactan && panel.dataset.durum !== "kisa") return;
    if (olay.target.closest("button")) return;
    baslangic = { y: olay.clientY, t: performance.now() };
    panel.setPointerCapture(olay.pointerId);
    panel.classList.add("surukleniyor");
  });
  panel.addEventListener("pointermove", (olay) => {
    if (!baslangic) return;
    panel.style.setProperty("--surukle", olay.clientY - baslangic.y + "px");
  });
  const birak = (olay) => {
    if (!baslangic) return;
    const dy = olay.clientY - baslangic.y;
    const hiz = dy / Math.max(1, performance.now() - baslangic.t);
    baslangic = null;
    panel.classList.remove("surukleniyor");
    const asagi = dy > panel.offsetHeight * KAPATMA_ORANI || hiz > HIZLI;
    const yukari = dy < -40 || hiz < -HIZLI;
    if (Math.abs(dy) < 6) { // sürükleme değil, dokunma
      panel.style.removeProperty("--surukle");
      if (panel.dataset.durum === "kisa") api.tamYap();
      return;
    }
    if (panel.dataset.durum === "tam") durumYap(asagi ? "kisa" : "tam");
    else if (asagi) api.kapat();
    else durumYap(yukari ? "tam" : "kisa");
  };
  panel.addEventListener("pointerup", birak);
  panel.addEventListener("pointercancel", birak);

  // Odak tuzağı: tam hâldeyken Tab panelin içinde döner
  panel.addEventListener("keydown", (olay) => {
    if (olay.key !== "Tab" || panel.dataset.durum !== "tam") return;
    const ogeler = [...panel.querySelectorAll(ODAKLANABILIR)].filter((e) => !e.disabled);
    if (!ogeler.length) return;
    const ilk = ogeler[0], son = ogeler[ogeler.length - 1];
    if (olay.shiftKey && document.activeElement === ilk) { son.focus(); olay.preventDefault(); }
    else if (!olay.shiftKey && document.activeElement === son) { ilk.focus(); olay.preventDefault(); }
  });

  addEventListener("resize", () => panel.style.setProperty("--kisa-kayma", kisaKayma() + "px"));
  return api;
}
