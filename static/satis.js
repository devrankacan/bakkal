const sepet = {};

const barkodInput = document.getElementById("barkodInput");
const urunBilgi   = document.getElementById("urunBilgi");
const sepetBody   = document.getElementById("sepetBody");
const toplamEl    = document.getElementById("toplamFiyat");

barkodInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const barkod = barkodInput.value.trim();
    if (barkod) {
      urunAra(barkod);
      barkodInput.value = "";
    }
  }
});

async function urunAra(barkod) {
  try {
    const res  = await fetch(`/api/urun/${encodeURIComponent(barkod)}`);
    const data = await res.json();

    if (data.hata) {
      urunBilgi.className = "urun-bilgi hata-bg";
      urunBilgi.textContent = `Ürün bulunamadı: ${barkod}`;
    } else {
      urunBilgi.className = "urun-bilgi";
      urunBilgi.innerHTML = `<strong>${data.ad}</strong> — ${data.fiyat.toFixed(2)} ₺ &nbsp;|&nbsp; Stok: ${data.stok}`;
      sepeteEkle(data);
    }
  } catch {
    urunBilgi.className = "urun-bilgi hata-bg";
    urunBilgi.textContent = "Bağlantı hatası.";
  }
}

function sepeteEkle(urun) {
  if (sepet[urun.id]) {
    sepet[urun.id].adet++;
  } else {
    sepet[urun.id] = { ...urun, adet: 1 };
  }
  sepetGuncelle();
}

function adetDegistir(id, delta) {
  if (!sepet[id]) return;
  sepet[id].adet += delta;
  if (sepet[id].adet <= 0) delete sepet[id];
  sepetGuncelle();
}

function sepettenCikar(id) {
  delete sepet[id];
  sepetGuncelle();
}

function sepetGuncelle() {
  const ids = Object.keys(sepet);
  if (ids.length === 0) {
    sepetBody.innerHTML = '<tr id="bosSebet"><td colspan="5" class="bos-mesaj">Sepet boş</td></tr>';
    toplamEl.textContent = "0,00 ₺";
    return;
  }

  let html = "";
  let toplam = 0;
  for (const id of ids) {
    const item = sepet[id];
    const araToplam = item.fiyat * item.adet;
    toplam += araToplam;
    html += `
      <tr>
        <td>${item.ad}</td>
        <td>
          <div class="adet-kontrol">
            <button class="adet-btn" onclick="adetDegistir(${id}, -1)">−</button>
            <span>${item.adet}</span>
            <button class="adet-btn" onclick="adetDegistir(${id}, 1)">+</button>
          </div>
        </td>
        <td>${item.fiyat.toFixed(2)} ₺</td>
        <td>${araToplam.toFixed(2)} ₺</td>
        <td><button class="adet-btn" onclick="sepettenCikar(${id})">✕</button></td>
      </tr>`;
  }

  sepetBody.innerHTML = html;
  toplamEl.textContent = toplam.toFixed(2).replace(".", ",") + " ₺";
}

function sepetTemizle() {
  for (const key in sepet) delete sepet[key];
  sepetGuncelle();
  urunBilgi.className = "urun-bilgi gizli";
  barkodInput.focus();
}

function odemeYap() {
  if (Object.keys(sepet).length === 0) return;
  const toplam = Object.values(sepet).reduce((s, i) => s + i.fiyat * i.adet, 0);
  document.getElementById("modalToplam").textContent = toplam.toFixed(2).replace(".", ",") + " ₺";
  document.getElementById("alinanPara").value = "";
  document.getElementById("paraUstu").textContent = "-";
  document.getElementById("odemeModal").classList.remove("gizli");
  document.getElementById("alinanPara").focus();
}

function modalKapat() {
  document.getElementById("odemeModal").classList.add("gizli");
  barkodInput.focus();
}

function paraHesapla() {
  const toplam  = Object.values(sepet).reduce((s, i) => s + i.fiyat * i.adet, 0);
  const alinan  = parseFloat(document.getElementById("alinanPara").value) || 0;
  const ustu    = alinan - toplam;
  document.getElementById("paraUstu").textContent =
    ustu >= 0 ? ustu.toFixed(2).replace(".", ",") + " ₺" : "-";
}

async function odemeOnayla() {
  const payload = {
    sepet: Object.values(sepet).map((i) => ({
      id: i.id,
      ad: i.ad,
      fiyat: i.fiyat,
      adet: i.adet,
    })),
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
      alert(`Satış tamamlandı!\nToplam: ${data.toplam.toFixed(2)} ₺`);
      sepetTemizle();
    } else {
      alert("Hata: " + data.hata);
    }
  } catch {
    alert("Bağlantı hatası.");
  }
}

// Modal dışına tıklayınca kapat
document.getElementById("odemeModal").addEventListener("click", (e) => {
  if (e.target === document.getElementById("odemeModal")) modalKapat();
});
