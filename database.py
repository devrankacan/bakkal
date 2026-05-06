import sqlite3
from datetime import date

DB = "bakkal.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS urunler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT UNIQUE NOT NULL,
            ad TEXT NOT NULL,
            fiyat REAL NOT NULL,
            stok INTEGER NOT NULL DEFAULT 0,
            min_stok INTEGER NOT NULL DEFAULT 5,
            kategori TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS satislar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            toplam REAL NOT NULL,
            olusturma TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS satis_kalemleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            satis_id INTEGER NOT NULL,
            urun_id INTEGER NOT NULL,
            adet INTEGER NOT NULL,
            birim_fiyat REAL NOT NULL,
            FOREIGN KEY (satis_id) REFERENCES satislar(id),
            FOREIGN KEY (urun_id) REFERENCES urunler(id)
        );
    """)
    conn.commit()
    conn.close()
