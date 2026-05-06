from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from functools import wraps
from database import get_db, init_db
from datetime import date
import csv
import io
import openpyxl

app = Flask(__name__)
app.secret_key = "bakkal-gizli-anahtar-2024"

SIFRE = "bakkal2024"


def giris_gerekli(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("giris_yapildi"):
            return redirect(url_for("giris", sonraki=request.path))
        return f(*args, **kwargs)
    return decorated


@app.before_request
def setup():
    init_db()


# ---------- Giriş / Çıkış ----------
@app.route("/giris", methods=["GET", "POST"])
def giris():
    if session.get("giris_yapildi"):
        return redirect(url_for("satis"))

    hata = None
    if request.method == "POST":
        if request.form["sifre"] == SIFRE:
            session["giris_yapildi"] = True
            sonraki = request.args.get("sonraki") or url_for("satis")
            return redirect(sonraki)
        hata = "Şifre yanlış, tekrar deneyin."

    return render_template("giris.html", hata=hata)


@app.route("/cikis")
def cikis():
    session.clear()
    return redirect(url_for("giris"))


# ---------- Ana Sayfa ----------
@app.route("/")
@giris_gerekli
def index():
    return redirect(url_for("satis"))


# ---------- Satış Ekranı ----------
@app.route("/satis")
@giris_gerekli
def satis():
    return render_template("satis.html")


@app.route("/api/urun/<barkod>")
@giris_gerekli
def urun_bul(barkod):
    db = get_db()
    urun = db.execute("SELECT * FROM urunler WHERE barkod = ?", (barkod,)).fetchone()
    db.close()
    if urun:
        return jsonify(dict(urun))
    return jsonify({"hata": "Ürün bulunamadı"}), 404


@app.route("/api/satis", methods=["POST"])
@giris_gerekli
def satis_kaydet():
    data = request.json
    sepet = data.get("sepet", [])
    if not sepet:
        return jsonify({"hata": "Sepet boş"}), 400

    db = get_db()
    try:
        toplam = sum(item["fiyat"] * item["adet"] for item in sepet)
        bugun = date.today().isoformat()
        cur = db.execute(
            "INSERT INTO satislar (tarih, toplam) VALUES (?, ?)", (bugun, toplam)
        )
        satis_id = cur.lastrowid

        for item in sepet:
            urun = db.execute("SELECT stok FROM urunler WHERE id = ?", (item["id"],)).fetchone()
            if not urun or urun["stok"] < item["adet"]:
                db.rollback()
                return jsonify({"hata": f"{item['ad']} için yeterli stok yok"}), 400

            db.execute(
                "INSERT INTO satis_kalemleri (satis_id, urun_id, adet, birim_fiyat) VALUES (?, ?, ?, ?)",
                (satis_id, item["id"], item["adet"], item["fiyat"]),
            )
            db.execute(
                "UPDATE urunler SET stok = stok - ? WHERE id = ?",
                (item["adet"], item["id"]),
            )

        db.commit()
        return jsonify({"basari": True, "satis_id": satis_id, "toplam": toplam})
    except Exception as e:
        db.rollback()
        return jsonify({"hata": str(e)}), 500
    finally:
        db.close()


# ---------- Stok Yönetimi ----------
@app.route("/stok")
@giris_gerekli
def stok():
    db = get_db()
    urunler = db.execute("SELECT * FROM urunler ORDER BY ad").fetchall()
    db.close()
    return render_template("stok.html", urunler=urunler)


@app.route("/stok/guncelle/<int:urun_id>", methods=["POST"])
@giris_gerekli
def stok_guncelle(urun_id):
    miktar = int(request.form["miktar"])
    db = get_db()
    db.execute("UPDATE urunler SET stok = stok + ? WHERE id = ?", (miktar, urun_id))
    db.commit()
    db.close()
    flash("Stok güncellendi.", "basari")
    return redirect(url_for("stok"))


# ---------- Ürün Yönetimi ----------
@app.route("/urunler")
@giris_gerekli
def urunler():
    db = get_db()
    urun_listesi = db.execute("SELECT * FROM urunler ORDER BY ad").fetchall()
    db.close()
    return render_template("urunler.html", urunler=urun_listesi)


@app.route("/urun/ekle", methods=["GET", "POST"])
@giris_gerekli
def urun_ekle():
    if request.method == "POST":
        barkod = request.form["barkod"].strip()
        ad = request.form["ad"].strip()
        fiyat = float(request.form["fiyat"])
        stok = int(request.form["stok"])
        min_stok = int(request.form["min_stok"])
        kategori = request.form["kategori"].strip()

        db = get_db()
        try:
            db.execute(
                "INSERT INTO urunler (barkod, ad, fiyat, stok, min_stok, kategori) VALUES (?, ?, ?, ?, ?, ?)",
                (barkod, ad, fiyat, stok, min_stok, kategori),
            )
            db.commit()
            flash("Ürün eklendi.", "basari")
            return redirect(url_for("urunler"))
        except Exception:
            flash("Bu barkod zaten kayıtlı.", "hata")
        finally:
            db.close()

    return render_template("urun_form.html", urun=None)


@app.route("/urun/duzenle/<int:urun_id>", methods=["GET", "POST"])
@giris_gerekli
def urun_duzenle(urun_id):
    db = get_db()
    urun = db.execute("SELECT * FROM urunler WHERE id = ?", (urun_id,)).fetchone()

    if request.method == "POST":
        barkod = request.form["barkod"].strip()
        ad = request.form["ad"].strip()
        fiyat = float(request.form["fiyat"])
        stok = int(request.form["stok"])
        min_stok = int(request.form["min_stok"])
        kategori = request.form["kategori"].strip()

        db.execute(
            "UPDATE urunler SET barkod=?, ad=?, fiyat=?, stok=?, min_stok=?, kategori=? WHERE id=?",
            (barkod, ad, fiyat, stok, min_stok, kategori, urun_id),
        )
        db.commit()
        db.close()
        flash("Ürün güncellendi.", "basari")
        return redirect(url_for("urunler"))

    db.close()
    return render_template("urun_form.html", urun=urun)


@app.route("/urun/sil/<int:urun_id>", methods=["POST"])
@giris_gerekli
def urun_sil(urun_id):
    db = get_db()
    db.execute("DELETE FROM urunler WHERE id = ?", (urun_id,))
    db.commit()
    db.close()
    flash("Ürün silindi.", "basari")
    return redirect(url_for("urunler"))


# ---------- Toplu Yükleme ----------
@app.route("/urunler/yukle", methods=["GET", "POST"])
@giris_gerekli
def toplu_yukle():
    if request.method == "POST":
        dosya = request.files.get("dosya")
        if not dosya or dosya.filename == "":
            flash("Dosya seçilmedi.", "hata")
            return redirect(url_for("toplu_yukle"))

        satirlar = []
        ad = dosya.filename.lower()

        try:
            if ad.endswith(".xlsx") or ad.endswith(".xls"):
                wb = openpyxl.load_workbook(dosya, data_only=True)
                ws = wb.active
                for row in ws.iter_rows(min_row=2, values_only=True):
                    if row[0] is not None:
                        satirlar.append(row)
            elif ad.endswith(".csv"):
                icerik = dosya.read().decode("utf-8-sig")
                reader = csv.reader(io.StringIO(icerik))
                next(reader, None)
                for row in reader:
                    if row and row[0].strip():
                        satirlar.append(row)
            else:
                flash("Sadece .xlsx veya .csv dosyası kabul edilir.", "hata")
                return redirect(url_for("toplu_yukle"))
        except Exception as e:
            flash(f"Dosya okunamadı: {e}", "hata")
            return redirect(url_for("toplu_yukle"))

        eklendi = guncellendi = hatali = 0
        db = get_db()
        for i, row in enumerate(satirlar, start=2):
            try:
                barkod   = str(row[0]).strip()
                urun_ad  = str(row[1]).strip()
                fiyat    = float(str(row[2]).replace(",", "."))
                stok     = int(float(str(row[3]))) if len(row) > 3 and row[3] not in (None, "") else 0
                min_stok = int(float(str(row[4]))) if len(row) > 4 and row[4] not in (None, "") else 5
                kategori = str(row[5]).strip() if len(row) > 5 and row[5] else ""

                mevcut = db.execute("SELECT id FROM urunler WHERE barkod = ?", (barkod,)).fetchone()
                if mevcut:
                    db.execute(
                        "UPDATE urunler SET ad=?, fiyat=?, stok=?, min_stok=?, kategori=? WHERE barkod=?",
                        (urun_ad, fiyat, stok, min_stok, kategori, barkod),
                    )
                    guncellendi += 1
                else:
                    db.execute(
                        "INSERT INTO urunler (barkod, ad, fiyat, stok, min_stok, kategori) VALUES (?,?,?,?,?,?)",
                        (barkod, urun_ad, fiyat, stok, min_stok, kategori),
                    )
                    eklendi += 1
            except Exception:
                hatali += 1

        db.commit()
        db.close()

        flash(f"{eklendi} ürün eklendi, {guncellendi} ürün güncellendi, {hatali} satır atlandı.", "basari")
        return redirect(url_for("urunler"))

    return render_template("toplu_yukle.html")


# ---------- Raporlar ----------
@app.route("/rapor")
@giris_gerekli
def rapor():
    db = get_db()
    bugun = date.today().isoformat()

    bas_tarih = request.args.get("bas", bugun)
    bitis_tarih = request.args.get("bitis", bugun)
    kategori_filtre = request.args.get("kategori", "")

    gunluk = db.execute(
        "SELECT COUNT(*) as adet, COALESCE(SUM(toplam),0) as toplam FROM satislar WHERE tarih = ?",
        (bugun,),
    ).fetchone()

    filtre_query = """
        SELECT s.id, s.tarih, s.toplam, s.olusturma
        FROM satislar s
        WHERE s.tarih BETWEEN ? AND ?
    """
    params = [bas_tarih, bitis_tarih]

    if kategori_filtre:
        filtre_query += """
            AND EXISTS (
                SELECT 1 FROM satis_kalemleri sk
                JOIN urunler u ON u.id = sk.urun_id
                WHERE sk.satis_id = s.id AND u.kategori = ?
            )
        """
        params.append(kategori_filtre)

    filtre_query += " ORDER BY s.id DESC LIMIT 100"
    filtreli_satislar = db.execute(filtre_query, params).fetchall()

    filtre_ozet = db.execute(
        "SELECT COUNT(*) as adet, COALESCE(SUM(toplam),0) as toplam FROM satislar WHERE tarih BETWEEN ? AND ?",
        (bas_tarih, bitis_tarih),
    ).fetchone()

    kategoriler = db.execute(
        "SELECT DISTINCT kategori FROM urunler WHERE kategori != '' ORDER BY kategori"
    ).fetchall()

    dusuk_stok = db.execute(
        "SELECT * FROM urunler WHERE stok <= min_stok ORDER BY stok ASC"
    ).fetchall()

    db.close()
    return render_template(
        "rapor.html",
        gunluk=gunluk,
        filtreli_satislar=filtreli_satislar,
        filtre_ozet=filtre_ozet,
        dusuk_stok=dusuk_stok,
        bugun=bugun,
        bas_tarih=bas_tarih,
        bitis_tarih=bitis_tarih,
        kategori_filtre=kategori_filtre,
        kategoriler=kategoriler,
    )


@app.route("/rapor/satis/<int:satis_id>")
@giris_gerekli
def satis_detay(satis_id):
    db = get_db()
    satis = db.execute("SELECT * FROM satislar WHERE id = ?", (satis_id,)).fetchone()
    kalemler = db.execute(
        """SELECT sk.adet, sk.birim_fiyat, u.ad, u.barkod
           FROM satis_kalemleri sk
           JOIN urunler u ON u.id = sk.urun_id
           WHERE sk.satis_id = ?""",
        (satis_id,),
    ).fetchall()
    db.close()
    return render_template("satis_detay.html", satis=satis, kalemler=kalemler)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
