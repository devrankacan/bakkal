const sepet = {};

const barkodInput   = document.getElementById("barkodInput");
const urunBilgi     = document.getElementById("urunBilgi");
const sepetBody     = document.getElementById("sepetBody");
const toplamEl      = document.getElementById("toplamFiyat");
const badgeEl       = document.getElementById("sepetBadge");
const kalemSayisiEl = document.getElementById("sepetKalemSayisi");
const toplamAdetEl  = document.getElementById("sepetToplamAdet");

barkodInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const barkod = barkodInput.value.trim();
    if (barkod) { urunAra(barkod); barkodInput.value = ""; }
  }
});

async function urunAra(barkod) {
  try {
    const res  = await fetch(`/api/urun/${encodeURIComponent(barkod)}`);
    const data = await res.json();
    if (data.hata) {
      urunBilgi.className = "urun-bilgi urun-bilgi-hata";
      urunBilgi.innerHTML = `✕ &nbsp;Ürün bulunamadı: <strong>${barkod}</strong>`;
    } else {
      urunBilgi.className = "urun-bilgi urun-bilgi-ok";
      urunBilgi.innerHTML = `✓ &nbsp;<strong>${data.ad}</strong> — ${fmt(data.fiyat)} &nbsp;|&nbsp; Stok: ${data.stok}`;
      sepeteEkle(data);
    }
  } catch {
    urunBilgi.className = "urun-bilgi urun-bilgi-hata";
    urunBilgi.textContent = "Bağlantı hatası.";
  }
}

function sepeteEkle(urun) {
  if (sepet[urun.id]) sepet[urun.id].adet++;
  else sepet[urun.id] = { ...urun, adet: 1 };
  sepetGuncelle();
}

function adetDegistir(id, delta) {
  if (!sepet[id]) return;
  sepet[id].adet += delta;
  if (sepet[id].adet <= 0) delete sepet[id];
  sepetGuncelle();
}

function sepettenCikar(id) { delete sepet[id]; sepetGuncelle(); }

function fmt(fiyat) { return "₺" + fiyat.toFixed(2).replace(".", ","); }

function sepetGuncelle() {
  const ids = Object.keys(sepet);
  const toplamAdet = ids.reduce((s, id) => s + sepet[id].adet, 0);
  const toplamFiyat = ids.reduce((s, id) => s + sepet[id].fiyat * sepet[id].adet, 0);

  badgeEl.textContent = ids.length;
  kalemSayisiEl.textContent = ids.length;
  toplamAdetEl.textContent = toplamAdet;

  if (ids.length === 0) {
    sepetBody.innerHTML = '<tr id="bosSepet"><td colspan="5" class="bos-mesaj">Sepet boş — barkod okutun</td></tr>';
    toplamEl.textContent = "₺0,00";
    return;
  }

  let html = "";
  for (const id of ids) {
    const item = sepet[id];
    const ara = item.fiyat * item.adet;
    html += `
      <tr>
        <td style="font-weight:600;max-width:180px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${item.ad}</td>
        <td style="text-align:center;">
          <div class="adet-kontrol" style="justify-content:center;">
            <button class="adet-btn" onclick="adetDegistir(${id},-1)">−</button>
            <span class="adet-sayi">${item.adet}</span>
            <button class="adet-btn" onclick="adetDegistir(${id},1)">+</button>
          </div>
        </td>
        <td style="text-align:right;color:#6b7280;">${fmt(item.fiyat)}</td>
        <td style="text-align:right;font-weight:700;">${fmt(ara)}</td>
        <td style="text-align:center;"><button class="silme-btn" onclick="sepettenCikar(${id})">×</button></td>
      </tr>`;
  }
  sepetBody.innerHTML = html;
  toplamEl.textContent = fmt(toplamFiyat);
}

function sepetTemizle() {
  for (const k in sepet) delete sepet[k];
  sepetGuncelle();
  urunBilgi.className = "urun-bilgi gizli";
  barkodInput.focus();
}

function odemeYap() {
  if (Object.keys(sepet).length === 0) return;
  const toplam = Object.values(sepet).reduce((s, i) => s + i.fiyat * i.adet, 0);
  document.getElementById("modalToplam").textContent = fmt(toplam);
  document.getElementById("alinanPara").value = "";
  document.getElementById("paraUstu").textContent = "—";
  document.getElementById("odemeModal").classList.remove("gizli");
  setTimeout(() => document.getElementById("alinanPara").focus(), 50);
}

function modalKapat() {
  document.getElementById("odemeModal").classList.add("gizli");
  barkodInput.focus();
}

function paraHesapla() {
  const toplam = Object.values(sepet).reduce((s, i) => s + i.fiyat * i.adet, 0);
  const alinan = parseFloat(document.getElementById("alinanPara").value) || 0;
  const ustu = alinan - toplam;
  document.getElementById("paraUstu").textContent = ustu >= 0 ? fmt(ustu) : "—";
}

async function odemeOnayla() {
  const payload = {
    sepet: Object.values(sepet).map(i => ({ id: i.id, ad: i.ad, fiyat: i.fiyat, adet: i.adet }))
  };
  try {
    const res  = await fetch("/api/satis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (data.basari) {
      modalKapat();
      alert(`✓ Satış tamamlandı\nToplam: ${fmt(data.toplam)}`);
      sepetTemizle();
    } else {
      alert("Hata: " + data.hata);
    }
  } catch { alert("Bağlantı hatası."); }
}

document.getElementById("odemeModal").addEventListener("click", e => {
  if (e.target === document.getElementById("odemeModal")) modalKapat();
});
