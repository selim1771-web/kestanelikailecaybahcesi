import os
import sqlite3
import secrets

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cay_bahcesi.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn, table_name: str, column_name: str, column_def: str):
    c = conn.cursor()
    c.execute(f"PRAGMA table_info({table_name})")
    existing = {row[1] for row in c.fetchall()}
    if column_name not in existing:
        c.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY,
            isletme_adi TEXT DEFAULT 'Çay Bahçesi',
            vergi_dairesi TEXT DEFAULT '',
            vergi_no TEXT DEFAULT '',
            telefon TEXT DEFAULT '',
            adres TEXT DEFAULT '',
            iyi_niyet TEXT DEFAULT 'Afiyet olsun, tekrar bekleriz!',
            max_garson INTEGER DEFAULT 10,
            max_kat INTEGER DEFAULT 20,
            host_url TEXT DEFAULT 'http://localhost:8000',
            public_menu_url TEXT DEFAULT 'https://kestanelikcaybahcem.onrender.com/dis/menu'
        )
    """)
    c.execute("INSERT OR IGNORE INTO settings (id) VALUES (1)")

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'garson',
            ad_soyad TEXT DEFAULT '',
            telefon TEXT DEFAULT '',
            aktif INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("INSERT OR IGNORE INTO users (id, username, password, role, ad_soyad) VALUES (1, 'admin', 'admin123', 'admin', 'Yönetici')")

    c.execute("""
        CREATE TABLE IF NOT EXISTS katlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kat_adi TEXT NOT NULL,
            sira INTEGER DEFAULT 0,
            aktif INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS masalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kat_id INTEGER,
            masa_no TEXT NOT NULL,
            durum TEXT DEFAULT 'bos',
            qr_uuid TEXT UNIQUE DEFAULT (lower(hex(randomblob(16)))),
            FOREIGN KEY (kat_id) REFERENCES katlar(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS kategoriler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT NOT NULL,
            renk TEXT DEFAULT '#4CAF50',
            aktif INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS urunler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kategori_id INTEGER,
            ad TEXT NOT NULL,
            ad_en TEXT DEFAULT '',
            ad_ar TEXT DEFAULT '',
            fiyat REAL NOT NULL,
            stok INTEGER DEFAULT 0,
            kritik_stok INTEGER DEFAULT 5,
            aktif INTEGER DEFAULT 1,
            aciklama TEXT DEFAULT '',
            aciklama_en TEXT DEFAULT '',
            aciklama_ar TEXT DEFAULT '',
            gorsel TEXT DEFAULT '',
            FOREIGN KEY (kategori_id) REFERENCES kategoriler(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS siparisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            masa_id INTEGER,
            garson_id INTEGER,
            urun_id INTEGER,
            adet INTEGER DEFAULT 1,
            fiyat REAL,
            durum TEXT DEFAULT 'bekliyor',
            odeme_tipi TEXT DEFAULT '',
            notlar TEXT DEFAULT '',
            siparis_kaynak TEXT DEFAULT 'garson',
            musteri_not TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (masa_id) REFERENCES masalar(id),
            FOREIGN KEY (garson_id) REFERENCES users(id),
            FOREIGN KEY (urun_id) REFERENCES urunler(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS veresiye (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT NOT NULL,
            telefon TEXT,
            toplam_borc REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS veresiye_hareket (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veresiye_id INTEGER,
            tutar REAL,
            tip TEXT DEFAULT 'borc',
            aciklama TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (veresiye_id) REFERENCES veresiye(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS kasa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tip TEXT NOT NULL,
            tutar REAL NOT NULL,
            aciklama TEXT,
            odeme_tipi TEXT DEFAULT 'nakit',
            garson_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (garson_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS stok_hareket (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            urun_id INTEGER,
            adet INTEGER,
            tip TEXT,
            aciklama TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (urun_id) REFERENCES urunler(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS kasa_defteri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih DATE DEFAULT CURRENT_DATE,
            aciklama TEXT NOT NULL,
            gelir REAL DEFAULT 0,
            gider REAL DEFAULT 0,
            odeme_tipi TEXT DEFAULT 'nakit',
            kategori TEXT DEFAULT 'diger',
            belge_no TEXT,
            garson_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (garson_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS veresiye_defteri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            veresiye_id INTEGER,
            tarih DATE DEFAULT CURRENT_DATE,
            aciklama TEXT,
            borc REAL DEFAULT 0,
            tahsilat REAL DEFAULT 0,
            bakiye REAL DEFAULT 0,
            urun_detay TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (veresiye_id) REFERENCES veresiye(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tedarikciler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            firma_adi TEXT NOT NULL,
            yetkili TEXT,
            telefon TEXT,
            vergi_dairesi TEXT,
            vergi_no TEXT,
            adres TEXT,
            bakiye REAL DEFAULT 0,
            aktif INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tedarikci_hareket (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tedarikci_id INTEGER,
            tarih DATE DEFAULT CURRENT_DATE,
            aciklama TEXT,
            borc REAL DEFAULT 0,
            odeme REAL DEFAULT 0,
            bakiye REAL DEFAULT 0,
            belge_no TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tedarikci_id) REFERENCES tedarikciler(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS gunluk_devir (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih DATE UNIQUE,
            acilis_bakiye REAL DEFAULT 0,
            kapanis_bakiye REAL DEFAULT 0,
            toplam_gelir REAL DEFAULT 0,
            toplam_gider REAL DEFAULT 0,
            durum TEXT DEFAULT 'acik',
            kapanis_saati TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS musteri_bildirimler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            masa_id INTEGER NOT NULL,
            tip TEXT NOT NULL DEFAULT 'garson',
            durum TEXT DEFAULT 'bekliyor',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (masa_id) REFERENCES masalar(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS dis_siparisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_ad_soyad TEXT NOT NULL,
            telefon TEXT NOT NULL,
            teslim_adres TEXT NOT NULL,
            odeme_tipi TEXT DEFAULT 'nakit',
            notlar TEXT DEFAULT '',
            toplam_tutar REAL DEFAULT 0,
            nakit_verilen REAL DEFAULT 0,
            para_ustu REAL DEFAULT 0,
            durum TEXT DEFAULT 'bekliyor',
            tahsilat_durumu TEXT DEFAULT 'beklemede',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS dis_siparis_urunler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dis_siparis_id INTEGER NOT NULL,
            urun_id INTEGER NOT NULL,
            adet INTEGER DEFAULT 1,
            fiyat REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dis_siparis_id) REFERENCES dis_siparisler(id),
            FOREIGN KEY (urun_id) REFERENCES urunler(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS emanet_tahsilatlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kaynak_turu TEXT NOT NULL,
            kaynak_id INTEGER NOT NULL,
            tutar REAL DEFAULT 0,
            odeme_tipi TEXT DEFAULT 'nakit',
            durum TEXT DEFAULT 'beklemede',
            aciklama TEXT DEFAULT '',
            teslim_eden TEXT DEFAULT '',
            teslim_alan TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Backward-compatible columns
    _ensure_column(conn, "settings", "public_menu_url", "TEXT DEFAULT 'https://kestanelikcaybahcem.onrender.com/dis/menu'")
    _ensure_column(conn, "kategoriler", "aktif", "INTEGER DEFAULT 1")
    _ensure_column(conn, "kategoriler", "ad_en", "TEXT DEFAULT ''")
    _ensure_column(conn, "kategoriler", "ad_ar", "TEXT DEFAULT ''")
    _ensure_column(conn, "urunler", "ad_en", "TEXT DEFAULT ''")
    _ensure_column(conn, "urunler", "ad_ar", "TEXT DEFAULT ''")
    _ensure_column(conn, "urunler", "aciklama_en", "TEXT DEFAULT ''")
    _ensure_column(conn, "urunler", "aciklama_ar", "TEXT DEFAULT ''")

    c.execute("SELECT COUNT(*) FROM katlar")
    if c.fetchone()[0] == 0:
        katlar = ['Bahçe', 'Teras', '1. Kat', '2. Kat']
        for i, kat in enumerate(katlar):
            c.execute("INSERT INTO katlar (kat_adi, sira) VALUES (?, ?)", (kat, i))
            kat_id = c.lastrowid
            for m in range(1, 11):
                c.execute("INSERT INTO masalar (kat_id, masa_no) VALUES (?, ?)", (kat_id, f"{kat} - Masa {m}"))

    c.execute("SELECT COUNT(*) FROM kategoriler")
    if c.fetchone()[0] == 0:
        for ad, renk in [('Çay', '#8B4513'), ('Kahve', '#6F4E37'), ('Tatlı', '#FF6B6B'), ('Yiyecek', '#4ECDC4'), ('Soğuk İçecek', '#45B7D1')]:
            c.execute("INSERT INTO kategoriler (ad, renk, aktif) VALUES (?, ?, 1)", (ad, renk))

    c.execute("SELECT id FROM masalar WHERE qr_uuid IS NULL OR qr_uuid = ''")
    for row in c.fetchall():
        c.execute("UPDATE masalar SET qr_uuid=? WHERE id=?", (secrets.token_hex(16), row["id"]))

    conn.commit()
    conn.close()


if __name__ == '__main__':
    init_db()
    print("Veritabanı hazır! QR Menü sistemi entegre edildi.")
