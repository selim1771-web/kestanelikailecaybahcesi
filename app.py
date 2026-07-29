from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, send_file
import os
import re
from io import BytesIO
import qrcode
from datetime import datetime, timedelta
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = 'cay_bahcesi_secret_key_2024'
app.config['JSON_AS_ASCII'] = False

SIFRE_DOSYA = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sifreler.md')

def sifreleri_kaydet():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT username, password, role, ad_soyad FROM users")
    users = c.fetchall()
    conn.close()
    with open(SIFRE_DOSYA, 'w', encoding='utf-8') as f:
        f.write("# Cay Bahcesi PRO - Kullanici Sifreleri\n")
        f.write("**Son Guncelleme:** {}\n\n".format(datetime.now().strftime('%d.%m.%Y %H:%M')))
        f.write("| Kullanici Adi | Sifre | Rol | Ad Soyad |\n")
        f.write("|---|---|---|---|\n")
        for u in users:
            f.write("| {} | {} | {} | {} |\n".format(u['username'], u['password'], u['role'], u['ad_soyad']))
        f.write("\n> **Not:** Bu dosya sifre unutulmamasi icin otomatik olusturulur.\n")

def get_host_url():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT host_url FROM settings WHERE id=1")
    row = c.fetchone()
    conn.close()
    return row['host_url'] if row and row['host_url'] else request.host_url.rstrip('/')


def get_public_menu_url():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT public_menu_url FROM settings WHERE id=1")
    row = c.fetchone()
    conn.close()
    if row and row["public_menu_url"]:
        return row["public_menu_url"]
    return "https://kestanelikcaybahcem.onrender.com/dis/menu"

def rows_to_dicts(rows):
    return [dict(row) for row in rows]

SPECIAL_PHRASES_EN = {
    "siyah çay": "black tea",
    "yeşil çay": "green tea",
    "demleme çay": "brewed tea",
    "sütlü kahve": "milk coffee",
    "filtre kahve": "filter coffee",
    "serpme kahvaltı": "mixed breakfast",
    "kahvaltı tabağı": "breakfast plate",
    "çay bahçesi": "tea garden",
}

SPECIAL_PHRASES_AR = {
    "siyah çay": "شاي أسود",
    "yeşil çay": "شاي أخضر",
    "demleme çay": "شاي مُخمَّر",
    "sütlü kahve": "قهوة بالحليب",
    "filtre kahve": "قهوة فلتر",
    "serpme kahvaltı": "فطور متنوع",
    "kahvaltı tabağı": "صحن فطور",
    "çay bahçesi": "حديقة شاي",
}


# ---------------------------------------------------------------------------
#  Çok dilli menü + dış sipariş yardımcıları
# ---------------------------------------------------------------------------
TR_EN_PHRASES = [
    ("serpme kahvaltı", "mixed breakfast"),
    ("kahvaltı tabağı", "breakfast plate"),
    ("kahvaltı", "breakfast"),
    ("paket servis", "takeaway"),
    ("soğuk içecek", "cold drink"),
    ("sıcak içecek", "hot drink"),
    ("ev yapımı", "homemade"),
    ("özel", "special"),
    ("karışık", "mixed"),
    ("günün", "daily"),
    ("içerisinde", "contains"),
    ("içinde", "contains"),
    ("yanında", "with"),
    ("servis edilir", "served"),
    ("özel soslu", "with special sauce"),
    ("ızgara", "grilled"),
    ("fırın", "oven-baked"),
]

TR_AR_PHRASES = [
    ("serpme kahvaltı", "فطور متنوع"),
    ("kahvaltı tabağı", "صحن فطور"),
    ("kahvaltı", "فطور"),
    ("paket servis", "طلب خارجي"),
    ("soğuk içecek", "مشروب بارد"),
    ("sıcak içecek", "مشروب ساخن"),
    ("ev yapımı", "محلي الصنع"),
    ("özel", "خاص"),
    ("karışık", "مشكل"),
    ("günün", "اليومي"),
    ("içerisinde", "يحتوي على"),
    ("içinde", "يحتوي على"),
    ("yanında", "مع"),
    ("servis edilir", "يُقدَّم"),
    ("özel soslu", "مع صلصة خاصة"),
    ("ızgara", "مشوي"),
    ("fırın", "مخبوز"),
]

TR_EN_WORDS = {
    "çay": "tea",
    "kahve": "coffee",
    "su": "water",
    "soda": "soda",
    "ayran": "ayran",
    "limonata": "lemonade",
    "poğaça": "pastry",
    "simit": "sesame bagel",
    "sandviç": "sandwich",
    "pizza": "pizza",
    "burger": "burger",
    "hamburger": "hamburger",
    "patates": "potato",
    "pilav": "rice",
    "çorba": "soup",
    "köfte": "meatball",
    "tavuk": "chicken",
    "et": "meat",
    "balık": "fish",
    "peynir": "cheese",
    "zeytin": "olive",
    "yumurta": "egg",
    "reçel": "jam",
    "bal": "honey",
    "domates": "tomato",
    "salatalık": "cucumber",
    "sucuk": "sucuk",
    "sosis": "sausage",
    "kaşar": "kasar cheese",
    "mantar": "mushroom",
    "acı": "spicy",
    "tatlı": "sweet",
}

TR_AR_WORDS = {
    "çay": "شاي",
    "kahve": "قهوة",
    "su": "ماء",
    "soda": "مياه غازية",
    "ayran": "عيران",
    "limonata": "ليموناضة",
    "poğaça": "فطيرة",
    "simit": "خبز سمسم",
    "sandviç": "ساندويتش",
    "pizza": "بيتزا",
    "burger": "برغر",
    "hamburger": "هامبرغر",
    "patates": "بطاطا",
    "pilav": "أرز",
    "çorba": "شوربة",
    "köfte": "كفتة",
    "tavuk": "دجاج",
    "et": "لحم",
    "balık": "سمك",
    "peynir": "جبن",
    "zeytin": "زيتون",
    "yumurta": "بيض",
    "reçel": "مربى",
    "bal": "عسل",
    "domates": "طماطم",
    "salatalık": "خيار",
    "sucuk": "سجق",
    "sosis": "نقانق",
    "kaşar": "جبن كاشار",
    "mantar": "فطر",
    "acı": "حار",
    "tatlı": "حلو",
}

def _normalize_spaces(text):
    return re.sub(r"\s+", " ", (text or "")).strip()

def _phrase_map(text, pairs):
    out = text
    for src, dst in pairs:
        out = re.sub(re.escape(src), dst, out, flags=re.IGNORECASE)
    return out

def _word_map(text, words):
    out = text
    for src in sorted(words.keys(), key=len, reverse=True):
        out = re.sub(r"\b" + re.escape(src) + r"\b", words[src], out, flags=re.IGNORECASE)
    return out


def auto_translate_menu_text(tr_text):
    src = _normalize_spaces(tr_text)
    if not src:
        return "", ""

    low = src.lower()
    if low in SPECIAL_PHRASES_EN:
        return SPECIAL_PHRASES_EN[low], SPECIAL_PHRASES_AR.get(low, src)

    en = _phrase_map(src, TR_EN_PHRASES)
    en = _word_map(en, TR_EN_WORDS)
    ar = _phrase_map(src, TR_AR_PHRASES)
    ar = _word_map(ar, TR_AR_WORDS)
    return en, ar


def ensure_menu_translations():
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("SELECT id, ad, COALESCE(ad_en, '') AS ad_en, COALESCE(ad_ar, '') AS ad_ar FROM kategoriler")
        for row in c.fetchall():
            ad_en, ad_ar = auto_translate_menu_text(row["ad"])
            if not row["ad_en"] or not row["ad_ar"]:
                c.execute("UPDATE kategoriler SET ad_en=?, ad_ar=? WHERE id=?", (ad_en or row["ad"], ad_ar or row["ad"], row["id"]))
    except Exception:
        pass
    try:
        c.execute("""
            SELECT id, ad, COALESCE(aciklama, '') AS aciklama,
                   COALESCE(ad_en, '') AS ad_en, COALESCE(ad_ar, '') AS ad_ar,
                   COALESCE(aciklama_en, '') AS aciklama_en, COALESCE(aciklama_ar, '') AS aciklama_ar
            FROM urunler
        """)
        for row in c.fetchall():
            ad_en, ad_ar = auto_translate_menu_text(row["ad"])
            aciklama_en, aciklama_ar = auto_translate_menu_text(row["aciklama"])
            if (not row["ad_en"]) or (not row["ad_ar"]) or (not row["aciklama_en"]) or (not row["aciklama_ar"]):
                c.execute("""
                    UPDATE urunler
                    SET ad_en=?, ad_ar=?, aciklama_en=?, aciklama_ar=?
                    WHERE id=?
                """, (
                    ad_en or row["ad"],
                    ad_ar or row["ad"],
                    aciklama_en or row["aciklama"],
                    aciklama_ar or row["aciklama"],
                    row["id"]
                ))
    except Exception:
        pass
    conn.commit()
    conn.close()


def _build_dis_qr_bytes():
    target = get_public_menu_url()
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(target)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()



def ensure_satis_hareketleri_table():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS satis_hareketleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kanal TEXT NOT NULL,
            kaynak_turu TEXT NOT NULL,
            kaynak_id INTEGER NOT NULL,
            tutar REAL NOT NULL,
            odeme_tipi TEXT DEFAULT 'nakit',
            aciklama TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=? AND aktif=1", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['ad_soyad'] = user['ad_soyad']
            return redirect(url_for('dashboard'))
        flash('Kullanici adi veya sifre hatali!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as toplam FROM masalar")
    toplam_masa = c.fetchone()['toplam']
    c.execute("SELECT COUNT(*) as dolu FROM masalar WHERE durum='dolu'")
    dolu_masa = c.fetchone()['dolu']
    c.execute("SELECT COUNT(*) as bekleyen FROM siparisler WHERE durum='bekliyor'")
    bekleyen = c.fetchone()['bekleyen']
    c.execute("SELECT COUNT(*) as hazir FROM siparisler WHERE durum='hazir'")
    hazir = c.fetchone()['hazir']
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute("SELECT COALESCE(SUM(tutar), 0) as gunluk FROM kasa WHERE date(created_at)=? AND tip='gelir'", (today,))
    gunluk_gelir = c.fetchone()['gunluk']
    c.execute("SELECT COALESCE(SUM(tutar), 0) as gunluk FROM kasa WHERE date(created_at)=? AND tip='gider'", (today,))
    gunluk_gider = c.fetchone()['gunluk']
    c.execute("SELECT COALESCE(SUM(toplam_borc), 0) as toplam FROM veresiye")
    toplam_borc = c.fetchone()['toplam']
    c.execute("SELECT COUNT(*) as kritik FROM urunler WHERE stok <= kritik_stok AND aktif=1")
    kritik_stok = c.fetchone()['kritik']
    c.execute("SELECT * FROM settings WHERE id=1")
    settings = c.fetchone()
    # Yeni bildirimler (garson cagirma / hesap isteme)
    c.execute("SELECT COUNT(*) as sayi FROM musteri_bildirimler WHERE durum='bekliyor'")
    yeni_bildirim = c.fetchone()['sayi']
    conn.close()
    return render_template('dashboard.html', toplam_masa=toplam_masa, dolu_masa=dolu_masa,
                           bekleyen=bekleyen, hazir=hazir, gunluk_gelir=gunluk_gelir,
                           gunluk_gider=gunluk_gider, toplam_borc=toplam_borc,
                           kritik_stok=kritik_stok, settings=settings, now=datetime.now(),
                           yeni_bildirim=yeni_bildirim)

# ========== SİPARİŞ AL (Mevcut masaya ekleme desteği) ==========
@app.route('/siparis')
def siparis():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM katlar WHERE aktif=1 ORDER BY sira")
    katlar = rows_to_dicts(c.fetchall())
    c.execute("SELECT m.*, k.kat_adi FROM masalar m JOIN katlar k ON m.kat_id=k.id ORDER BY k.sira, m.masa_no")
    masalar = rows_to_dicts(c.fetchall())
    c.execute("SELECT * FROM kategoriler WHERE aktif=1 ORDER BY ad")
    kategoriler = rows_to_dicts(c.fetchall())
    c.execute("SELECT u.*, k.ad as kategori_ad, k.renk FROM urunler u JOIN kategoriler k ON u.kategori_id=k.id WHERE u.aktif=1 AND k.aktif=1")
    urunler = rows_to_dicts(c.fetchall())
    conn.close()
    return render_template('siparis_multi.html', katlar=katlar, masalar=masalar, kategoriler=kategoriler, urunler=urunler)

@app.route('/api/siparis/ekle', methods=['POST'])

def siparis_ekle():
    data = request.get_json()
    masa_id = data.get('masa_id')
    urunler = data.get('urunler', [])
    notlar = data.get('notlar', '')
    conn = get_db()
    c = conn.cursor()
    # Masa dolu değilse dolu yap
    c.execute("UPDATE masalar SET durum='dolu' WHERE id=? AND durum='bos'", (masa_id,))
    for item in urunler:
        c.execute("SELECT fiyat, stok FROM urunler WHERE id=?", (item['urun_id'],))
        urun = c.fetchone()
        if urun and urun['stok'] >= item['adet']:
            c.execute("INSERT INTO siparisler (masa_id, garson_id, urun_id, adet, fiyat, durum, notlar, siparis_kaynak) VALUES (?, ?, ?, ?, ?, 'bekliyor', ?, 'garson')",
                     (masa_id, session['user_id'], item['urun_id'], item['adet'], urun['fiyat'], notlar))
            c.execute("UPDATE urunler SET stok = stok - ? WHERE id=?", (item['adet'], item['urun_id']))
            c.execute("INSERT INTO stok_hareket (urun_id, adet, tip, aciklama) VALUES (?, ?, 'cikis', ?)",
                     (item['urun_id'], item['adet'], "Masa siparis"))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ========== MASALAR (Ödeme + Aktarma + Fiş) ==========
@app.route('/masalar')
def masalar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM katlar WHERE aktif=1 ORDER BY sira")
    katlar = c.fetchall()
    c.execute("SELECT m.*, k.kat_adi, (SELECT COALESCE(SUM(s.fiyat * s.adet), 0) FROM siparisler s WHERE s.masa_id=m.id AND s.odeme_tipi='') as toplam_tutar FROM masalar m JOIN katlar k ON m.kat_id=k.id ORDER BY k.sira, m.masa_no")
    masalar = c.fetchall()
    host = get_host_url()
    conn.close()
    return render_template('masalar.html', katlar=katlar, masalar=masalar, host_url=host)

@app.route('/api/masa/<int:masa_id>/detay')
def masa_detay(masa_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT s.*, u.ad as urun_ad, us.ad_soyad as garson_adi FROM siparisler s JOIN urunler u ON s.urun_id=u.id JOIN users us ON s.garson_id=us.id WHERE s.masa_id=? AND s.odeme_tipi='' ORDER BY s.created_at", (masa_id,))
    siparisler = [dict(s) for s in c.fetchall()]
    c.execute("SELECT m.*, k.kat_adi FROM masalar m JOIN katlar k ON m.kat_id=k.id WHERE m.id=?", (masa_id,))
    masa = dict(c.fetchone())
    c.execute("SELECT * FROM masalar WHERE durum='bos' AND id!=? ORDER BY masa_no", (masa_id,))
    bos_masalar = [dict(m) for m in c.fetchall()]
    conn.close()
    return jsonify({'siparisler': siparisler, 'masa': masa, 'bos_masalar': bos_masalar})

@app.route('/api/masa/<int:masa_id>/odeme', methods=['POST'])
def masa_odeme(masa_id):
    data = request.get_json() or {}
    odeme_tipi = data.get('odeme_tipi', 'nakit')
    veresiye_id = data.get('veresiye_id')

    ensure_satis_hareketleri_table()

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(fiyat * adet), 0) as toplam FROM siparisler WHERE masa_id=? AND odeme_tipi=''", (masa_id,))
    toplam = c.fetchone()['toplam']

    if odeme_tipi == 'veresiye' and veresiye_id:
        c.execute("UPDATE veresiye SET toplam_borc = toplam_borc + ? WHERE id=?", (toplam, veresiye_id))
        c.execute(
            "INSERT INTO veresiye_hareket (veresiye_id, tutar, tip, aciklama) VALUES (?, ?, 'borc', ?)",
            (veresiye_id, toplam, 'Masa odemesi')
        )

    c.execute("UPDATE siparisler SET odeme_tipi=? WHERE masa_id=? AND odeme_tipi=''", (odeme_tipi, masa_id))
    c.execute("UPDATE masalar SET durum='bos' WHERE id=?", (masa_id,))

    if toplam > 0:
        c.execute(
            "INSERT INTO kasa (tip, tutar, aciklama, odeme_tipi, garson_id) VALUES (?, ?, ?, ?, ?)",
            ('gelir', toplam, f'Masa {masa_id} odeme', odeme_tipi, session['user_id'])
        )
        c.execute(
            """
            INSERT INTO satis_hareketleri (kanal, kaynak_turu, kaynak_id, tutar, odeme_tipi, aciklama)
            VALUES ('ic', 'masa', ?, ?, ?, ?)
            """,
            (masa_id, toplam, odeme_tipi, f'Masa {masa_id} odeme')
        )
        if odeme_tipi == 'nakit':
            c.execute(
                """
                INSERT INTO emanet_tahsilatlar (kaynak_turu, kaynak_id, tutar, odeme_tipi, durum, aciklama, teslim_eden)
                VALUES ('masa', ?, ?, 'nakit', 'beklemede', ?, ?)
                """,
                (masa_id, toplam, f'Masa {masa_id} nakit tahsilat', session.get('username', ''))
            )

    conn.commit()
    conn.close()
    return jsonify({'success': True, 'toplam': toplam})

@app.route('/api/masa/aktar', methods=['POST'])
def masa_aktar():
    data = request.get_json()
    eski_masa_id = data.get('eski_masa_id')
    yeni_masa_id = data.get('yeni_masa_id')
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE siparisler SET masa_id=? WHERE masa_id=? AND odeme_tipi=''", (yeni_masa_id, eski_masa_id))
    c.execute("UPDATE masalar SET durum='bos' WHERE id=?", (eski_masa_id,))
    c.execute("UPDATE masalar SET durum='dolu' WHERE id=?", (yeni_masa_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ========== MUTFAK (Bekleyen siparişler) ==========
@app.route('/mutfak')
def mutfak():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    # Masa bazlı gruplama - en yeni siparişler üstte
    c.execute("""
        SELECT s.masa_id, m.masa_no, k.kat_adi, MAX(s.created_at) as son_siparis,
               GROUP_CONCAT(s.id) as siparis_ids,
               COUNT(*) as urun_sayisi,
               SUM(s.fiyat * s.adet) as toplam_tutar
        FROM siparisler s
        JOIN masalar m ON s.masa_id=m.id
        JOIN katlar k ON m.kat_id=k.id
        WHERE s.durum IN ('bekliyor', 'hazirlaniyor')
        GROUP BY s.masa_id
        ORDER BY son_siparis DESC
    """)
    masa_gruplari = [dict(row) for row in c.fetchall()]

    # Her masa için detaylı ürün listesi
    for mg in masa_gruplari:
        c.execute("""
            SELECT s.*, u.ad as urun_ad, us.ad_soyad as garson_adi, s.musteri_not
            FROM siparisler s
            JOIN urunler u ON s.urun_id=u.id
            LEFT JOIN users us ON s.garson_id=us.id
            WHERE s.masa_id=? AND s.durum IN ('bekliyor', 'hazirlaniyor')
            ORDER BY s.created_at
        """, (mg['masa_id'],))
        mg['urunler'] = [dict(row) for row in c.fetchall()]

    conn.close()
    return render_template('mutfak.html', masa_gruplari=masa_gruplari)

@app.route('/api/mutfak/bildirim')
def mutfak_bildirim():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as sayi FROM siparisler WHERE durum='bekliyor'")
    bekleyen = c.fetchone()['sayi']
    conn.close()
    return jsonify({'bekleyen': bekleyen, 'yeni_siparis': bekleyen > 0})

@app.route('/api/siparis/<int:siparis_id>/durum', methods=['POST'])
def siparis_durum(siparis_id):
    data = request.get_json()
    durum = data.get('durum')
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE siparisler SET durum=?, updated_at=datetime('now') WHERE id=?", (durum, siparis_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/masa/<int:masa_id>/siparis/durum', methods=['POST'])
def masa_siparis_durum(masa_id):
    data = request.get_json()
    durum = data.get('durum')
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE siparisler SET durum=?, updated_at=datetime('now') WHERE masa_id=? AND durum IN ('bekliyor', 'hazirlaniyor')", (durum, masa_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ========== KASA (Tarih aralığı) ==========
@app.route('/kasa')
def kasa():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    baslangic = request.args.get('baslangic', datetime.now().strftime('%Y-%m-%d'))
    bitis = request.args.get('bitis', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT k.*, u.ad_soyad as garson_adi FROM kasa k LEFT JOIN users u ON k.garson_id=u.id WHERE date(k.created_at) BETWEEN ? AND ? ORDER BY k.created_at DESC", (baslangic, bitis))
    hareketler = c.fetchall()
    c.execute("SELECT COALESCE(SUM(tutar), 0) as toplam FROM kasa WHERE tip='gelir' AND date(created_at) BETWEEN ? AND ?", (baslangic, bitis))
    toplam_gelir = c.fetchone()['toplam']
    c.execute("SELECT COALESCE(SUM(tutar), 0) as toplam FROM kasa WHERE tip='gider' AND date(created_at) BETWEEN ? AND ?", (baslangic, bitis))
    toplam_gider = c.fetchone()['toplam']
    c.execute("SELECT COALESCE(SUM(tutar), 0) as toplam FROM kasa WHERE tip='gelir' AND odeme_tipi='nakit' AND date(created_at) BETWEEN ? AND ?", (baslangic, bitis))
    nakit_gelir = c.fetchone()['toplam']
    c.execute("SELECT COALESCE(SUM(tutar), 0) as toplam FROM kasa WHERE tip='gelir' AND odeme_tipi='kredi' AND date(created_at) BETWEEN ? AND ?", (baslangic, bitis))
    kredi_gelir = c.fetchone()['toplam']
    c.execute("SELECT COALESCE(SUM(tutar), 0) as toplam FROM kasa WHERE tip='gelir' AND odeme_tipi='veresiye' AND date(created_at) BETWEEN ? AND ?", (baslangic, bitis))
    veresiye_gelir = c.fetchone()['toplam']
    conn.close()
    return render_template('kasa.html', hareketler=hareketler, toplam_gelir=toplam_gelir,
                           toplam_gider=toplam_gider, nakit_gelir=nakit_gelir,
                           kredi_gelir=kredi_gelir, veresiye_gelir=veresiye_gelir,
                           baslangic=baslangic, bitis=bitis)

@app.route('/api/kasa/ekle', methods=['POST'])
def kasa_ekle():
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Yetkisiz'})
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO kasa (tip, tutar, aciklama, odeme_tipi, garson_id) VALUES (?, ?, ?, ?, ?)",
             (data['tip'], data['tutar'], data['aciklama'], data.get('odeme_tipi', 'nakit'), session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ========== MENÜ ==========
@app.route('/menu')
def menu():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM kategoriler WHERE aktif=1 ORDER BY ad")
    kategoriler = rows_to_dicts(c.fetchall())
    c.execute("SELECT u.*, k.ad as kategori_ad, k.renk FROM urunler u JOIN kategoriler k ON u.kategori_id=k.id WHERE u.aktif=1 AND k.aktif=1 ORDER BY k.ad, u.ad")
    urunler = rows_to_dicts(c.fetchall())
    conn.close()
    return render_template('menu.html', kategoriler=kategoriler, urunler=urunler)

@app.route('/api/kategori/ekle', methods=['POST'])
def kategori_ekle():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json() or {}
    ad = _normalize_spaces(data.get('ad', ''))
    if not ad:
        return jsonify({'success': False, 'error': 'Kategori adı boş olamaz'})
    ad_en, ad_ar = auto_translate_menu_text(ad)
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO kategoriler (ad, ad_en, ad_ar, renk, aktif) VALUES (?, ?, ?, ?, 1)",
              (ad, ad_en or ad, ad_ar or ad, data.get('renk', '#4CAF50')))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'ad_en': ad_en or ad, 'ad_ar': ad_ar or ad})

@app.route('/api/kategori/<int:id>/sil', methods=['POST'])
def kategori_sil(id):
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE kategoriler SET aktif=0 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/urun/ekle', methods=['POST'])
def urun_ekle():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json() or {}
    ad = _normalize_spaces(data.get('ad', ''))
    aciklama = _normalize_spaces(data.get('aciklama', ''))
    if not ad:
        return jsonify({'success': False, 'error': 'Ürün adı boş olamaz'})
    ad_en, ad_ar = auto_translate_menu_text(ad)
    aciklama_en, aciklama_ar = auto_translate_menu_text(aciklama)
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO urunler (kategori_id, ad, ad_en, ad_ar, fiyat, stok, kritik_stok, aktif, aciklama, aciklama_en, aciklama_ar, gorsel) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            data['kategori_id'], ad, ad_en or ad, ad_ar or ad,
            float(data.get('fiyat', 0)), int(data.get('stok', 0)), int(data.get('kritik_stok', 5)),
            int(data.get('aktif', 1)), aciklama, aciklama_en or aciklama, aciklama_ar or aciklama,
            data.get('gorsel', '')
        )
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'ad_en': ad_en or ad, 'ad_ar': ad_ar or ad})

@app.route('/api/urun/<int:id>/guncelle', methods=['POST'])
def urun_guncelle(id):
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json() or {}
    ad = _normalize_spaces(data.get('ad', ''))
    aciklama = _normalize_spaces(data.get('aciklama', ''))
    ad_en, ad_ar = auto_translate_menu_text(ad)
    aciklama_en, aciklama_ar = auto_translate_menu_text(aciklama)
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE urunler SET kategori_id=?, ad=?, ad_en=?, ad_ar=?, fiyat=?, stok=?, kritik_stok=?, aktif=?, aciklama=?, aciklama_en=?, aciklama_ar=?, gorsel=? WHERE id=?",
        (
            data['kategori_id'], ad, ad_en or ad, ad_ar or ad,
            float(data.get('fiyat', 0)), int(data.get('stok', 0)), int(data.get('kritik_stok', 5)),
            int(data.get('aktif', 1)), aciklama, aciklama_en or aciklama, aciklama_ar or aciklama,
            data.get('gorsel', ''), id
        )
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/urun/<int:id>/sil', methods=['POST'])
def urun_sil(id):
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE urunler SET aktif=0 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ========== STOK ==========

# ========== STOK ==========
@app.route('/stok')
def stok():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT u.*, k.ad as kategori_ad FROM urunler u JOIN kategoriler k ON u.kategori_id=k.id WHERE u.aktif=1")
    urunler = rows_to_dicts(c.fetchall())
    c.execute("SELECT h.*, u.ad as urun_ad FROM stok_hareket h JOIN urunler u ON h.urun_id=u.id ORDER BY h.created_at DESC LIMIT 50")
    hareketler = rows_to_dicts(c.fetchall())
    conn.close()
    return render_template('stok.html', urunler=urunler, hareketler=hareketler)

@app.route('/api/stok/guncelle', methods=['POST'])

def stok_guncelle():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE urunler SET stok = stok + ? WHERE id=?", (data['adet'], data['urun_id']))
    c.execute("INSERT INTO stok_hareket (urun_id, adet, tip, aciklama) VALUES (?, ?, 'giris', ?)",
             (data['urun_id'], data['adet'], data.get('aciklama', 'Stok girisi')))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ========== GARSONLAR ==========
@app.route('/garsonlar')
def garsonlar():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role='garson' ORDER BY ad_soyad")
    garsonlar = c.fetchall()
    c.execute("SELECT max_garson FROM settings WHERE id=1")
    max_garson = c.fetchone()['max_garson']
    conn.close()
    return render_template('garsonlar.html', garsonlar=garsonlar, max_garson=max_garson)

@app.route('/api/garson/ekle', methods=['POST'])
def garson_ekle():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as sayi FROM users WHERE role='garson' AND aktif=1")
    sayi = c.fetchone()['sayi']
    c.execute("SELECT max_garson FROM settings WHERE id=1")
    max_g = c.fetchone()['max_garson']
    if sayi >= max_g:
        conn.close()
        return jsonify({'success': False, 'error': 'Maksimum garson sayisina ulasildi!'})
    c.execute("INSERT INTO users (username, password, role, ad_soyad, telefon) VALUES (?, ?, 'garson', ?, ?)",
             (data['username'], data['password'], data['ad_soyad'], data.get('telefon', '')))
    conn.commit()
    conn.close()
    sifreleri_kaydet()
    return jsonify({'success': True})

@app.route('/api/garson/<int:id>/sil', methods=['POST'])
def garson_sil(id):
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET aktif=0 WHERE id=?", (id,))
    conn.commit()
    conn.close()
    sifreleri_kaydet()
    return jsonify({'success': True})

# ========== VERESİYE ==========
@app.route('/veresiye')
def veresiye():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT v.*, (SELECT COALESCE(SUM(tutar), 0) FROM veresiye_hareket WHERE veresiye_id=v.id AND tip='borc') as toplam_borc, (SELECT COALESCE(SUM(tutar), 0) FROM veresiye_hareket WHERE veresiye_id=v.id AND tip='tahsilat') as toplam_tahsilat FROM veresiye v ORDER BY v.ad_soyad")
    musteriler = c.fetchall()
    conn.close()
    return render_template('veresiye.html', musteriler=musteriler)

@app.route('/api/veresiye/liste')
def veresiye_liste():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, ad_soyad, telefon FROM veresiye ORDER BY ad_soyad")
    musteriler = [dict(m) for m in c.fetchall()]
    conn.close()
    return jsonify({'musteriler': musteriler})

@app.route('/api/veresiye/ekle', methods=['POST'])
def veresiye_ekle():
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO veresiye (ad_soyad, telefon) VALUES (?, ?)", (data['ad_soyad'], data.get('telefon', '')))
    vid = c.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': vid})

@app.route('/api/veresiye/<int:id>/tahsilat', methods=['POST'])
def veresiye_tahsilat(id):
    data = request.get_json()
    tutar = float(data.get('tutar', 0))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COALESCE(SUM(tutar), 0) FROM veresiye_hareket WHERE veresiye_id=? AND tip='borc'", (id,))
    toplam_borc = c.fetchone()[0]
    c.execute("SELECT COALESCE(SUM(tutar), 0) FROM veresiye_hareket WHERE veresiye_id=? AND tip='tahsilat'", (id,))
    toplam_tahsilat = c.fetchone()[0]
    kalan = toplam_borc - toplam_tahsilat
    if tutar > kalan:
        conn.close()
        return jsonify({'success': False, 'error': 'Tahsilat tutari borctan fazla! Kalan borc: {:.2f}'.format(kalan)})
    c.execute("INSERT INTO veresiye_hareket (veresiye_id, tutar, tip, aciklama) VALUES (?, ?, 'tahsilat', ?)",
             (id, tutar, data.get('aciklama', 'Tahsilat')))
    c.execute("INSERT INTO kasa (tip, tutar, aciklama, odeme_tipi, garson_id) VALUES (?, ?, ?, 'nakit', ?)",
             ('gelir', tutar, "Veresiye tahsilat - ID:{}".format(id), session['user_id']))
    c.execute("""
        INSERT INTO emanet_tahsilatlar (kaynak_turu, kaynak_id, tutar, odeme_tipi, durum, aciklama, teslim_eden)
        VALUES ('veresiye', ?, ?, 'nakit', 'beklemede', ?, ?)
    """, (id, tutar, f"Veresiye tahsilat ID:{id}", session.get('username', '')))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/veresiye/<int:id>/hareketler')
def veresiye_hareketler(id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM veresiye_hareket WHERE veresiye_id=? ORDER BY created_at DESC", (id,))
    hareketler = [dict(h) for h in c.fetchall()]
    conn.close()
    return jsonify({'hareketler': hareketler})

# ========== RAPORLAR ==========
@app.route('/raporlar')
def raporlar():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))

    ensure_satis_hareketleri_table()

    baslangic = request.args.get('baslangic', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    bitis = request.args.get('bitis', datetime.now().strftime('%Y-%m-%d'))
    garson_id = request.args.get('garson_id', '')
    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE role='garson' AND aktif=1 ORDER BY ad_soyad")
    garsonlar = c.fetchall()

    # İç / dış satış özetleri
    c.execute("""
        SELECT
            date(created_at) as gun,
            SUM(tutar) as toplam,
            SUM(CASE WHEN kanal='ic' THEN tutar ELSE 0 END) as ic_toplam,
            SUM(CASE WHEN kanal='dis' THEN tutar ELSE 0 END) as dis_toplam,
            COUNT(*) as adet
        FROM satis_hareketleri
        WHERE date(created_at) BETWEEN ? AND ?
        GROUP BY date(created_at)
        ORDER BY gun
    """, (baslangic, bitis))
    gunluk_satis = c.fetchall()

    c.execute("SELECT COALESCE(SUM(tutar), 0) as toplam FROM satis_hareketleri WHERE kanal='ic' AND date(created_at) BETWEEN ? AND ?", (baslangic, bitis))
    toplam_ic_satis = c.fetchone()['toplam']

    c.execute("SELECT COALESCE(SUM(tutar), 0) as toplam FROM satis_hareketleri WHERE kanal='dis' AND date(created_at) BETWEEN ? AND ?", (baslangic, bitis))
    toplam_dis_satis = c.fetchone()['toplam']

    toplam_satis = float(toplam_ic_satis) + float(toplam_dis_satis)

    # Kasa özeti (genel nakit akışı)
    c.execute("SELECT COALESCE(SUM(tutar), 0) as toplam FROM kasa WHERE tip='gelir' AND date(created_at) BETWEEN ? AND ?", (baslangic, bitis))
    toplam_gelir = c.fetchone()['toplam']
    c.execute("SELECT COALESCE(SUM(tutar), 0) as toplam FROM kasa WHERE tip='gider' AND date(created_at) BETWEEN ? AND ?", (baslangic, bitis))
    toplam_gider = c.fetchone()['toplam']

    # İç + dış en çok satan ürünler
    c.execute("""
        SELECT ad, SUM(adet) as adet, SUM(toplam) as toplam
        FROM (
            SELECT u.ad as ad, s.adet as adet, (s.fiyat * s.adet) as toplam
            FROM siparisler s
            JOIN urunler u ON s.urun_id=u.id
            WHERE date(s.created_at) BETWEEN ? AND ? AND s.odeme_tipi!=''

            UNION ALL

            SELECT u.ad as ad, ds.adet as adet, (ds.fiyat * ds.adet) as toplam
            FROM dis_siparis_urunler ds
            JOIN urunler u ON ds.urun_id=u.id
            JOIN dis_siparisler d ON ds.dis_siparis_id=d.id
            WHERE date(d.created_at) BETWEEN ? AND ?
        ) x
        GROUP BY ad
        ORDER BY adet DESC
        LIMIT 10
    """, (baslangic, bitis, baslangic, bitis))
    populer_urunler = c.fetchall()

    query = "SELECT u.ad_soyad, COUNT(*) as siparis_sayisi, SUM(s.fiyat * s.adet) as toplam_satis, AVG(s.fiyat * s.adet) as ortalama FROM siparisler s JOIN users u ON s.garson_id=u.id WHERE date(s.created_at) BETWEEN ? AND ? AND s.odeme_tipi!=''"
    params = [baslangic, bitis]
    if garson_id:
        query += " AND s.garson_id=?"
        params.append(garson_id)
    query += " GROUP BY s.garson_id ORDER BY toplam_satis DESC"
    c.execute(query, params)
    garson_performans = c.fetchall()

    query2 = "SELECT s.id, date(s.created_at) as tarih, m.masa_no, u.ad_soyad as garson_adi, SUM(s.fiyat * s.adet) as tutar, s.odeme_tipi FROM siparisler s JOIN masalar m ON s.masa_id=m.id JOIN users u ON s.garson_id=u.id WHERE date(s.created_at) BETWEEN ? AND ? AND s.odeme_tipi!=''"
    params2 = [baslangic, bitis]
    if garson_id:
        query2 += " AND s.garson_id=?"
        params2.append(garson_id)
    query2 += " GROUP BY s.masa_id, date(s.created_at) ORDER BY s.created_at DESC"
    c.execute(query2, params2)
    detayli_siparis = c.fetchall()

    # Dış sipariş detayları da ayrı kalsın
    c.execute("""
        SELECT d.id, date(d.created_at) as tarih, d.musteri_ad_soyad, d.telefon, d.teslim_adres,
               d.odeme_tipi, d.toplam_tutar, d.durum, d.tahsilat_durumu
        FROM dis_siparisler d
        WHERE date(d.created_at) BETWEEN ? AND ?
        ORDER BY d.created_at DESC
    """, (baslangic, bitis))
    dis_detayli_siparis = c.fetchall()

    conn.close()
    return render_template(
        'raporlar.html',
        gunluk_satis=gunluk_satis,
        populer_urunler=populer_urunler,
        garson_performans=garson_performans,
        detayli_siparis=detayli_siparis,
        dis_detayli_siparis=dis_detayli_siparis,
        garsonlar=garsonlar,
        baslangic=baslangic,
        bitis=bitis,
        garson_id=garson_id,
        toplam_gelir=toplam_gelir,
        toplam_gider=toplam_gider,
        toplam_ic_satis=toplam_ic_satis,
        toplam_dis_satis=toplam_dis_satis,
        toplam_satis=toplam_satis
    )

# ========== AYARLAR ==========
@app.route('/ayarlar')
def ayarlar():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM settings WHERE id=1")
    settings = c.fetchone()
    c.execute("SELECT * FROM katlar WHERE aktif=1 ORDER BY sira")
    katlar = c.fetchall()
    c.execute("SELECT * FROM users WHERE role='admin'")
    adminler = c.fetchall()
    conn.close()
    return render_template('ayarlar.html', settings=settings, katlar=katlar, adminler=adminler)

@app.route('/api/ayarlar/guncelle', methods=['POST'])
def ayarlar_guncelle():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json() or {}
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "UPDATE settings SET isletme_adi=?, vergi_dairesi=?, vergi_no=?, telefon=?, adres=?, iyi_niyet=?, max_garson=?, host_url=?, public_menu_url=? WHERE id=1",
        (
            data.get('isletme_adi', ''),
            data.get('vergi_dairesi', ''),
            data.get('vergi_no', ''),
            data.get('telefon', ''),
            data.get('adres', ''),
            data.get('iyi_niyet', ''),
            int(data.get('max_garson', 10)),
            data.get('host_url', 'http://localhost:8000'),
            data.get('public_menu_url', get_public_menu_url()),
        )
    )
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/kat/ekle', methods=['POST'])
def kat_ekle():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as sayi FROM katlar WHERE aktif=1")
    sayi = c.fetchone()['sayi']
    c.execute("SELECT max_kat FROM settings WHERE id=1")
    max_k = c.fetchone()['max_kat']
    if sayi >= max_k:
        conn.close()
        return jsonify({'success': False, 'error': 'Maksimum {} kat eklenebilir!'.format(max_k)})
    c.execute("SELECT MAX(sira) FROM katlar")
    max_sira = c.fetchone()[0] or 0
    c.execute("INSERT INTO katlar (kat_adi, sira) VALUES (?, ?)", (data['kat_adi'], max_sira + 1))
    kat_id = c.lastrowid
    for i in range(1, data.get('masa_sayisi', 5) + 1):
        c.execute("INSERT INTO masalar (kat_id, masa_no) VALUES (?, ?)", (kat_id, "{} - Masa {}".format(data['kat_adi'], i)))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/kat/<int:id>/sil', methods=['POST'])
def kat_sil(id):
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE katlar SET aktif=0 WHERE id=?", (id,))
    c.execute("UPDATE masalar SET durum='pasif' WHERE kat_id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/sifre/degistir', methods=['POST'])
def sifre_degistir():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET password=? WHERE id=?", (data['yeni_sifre'], data['user_id']))
    conn.commit()
    conn.close()
    sifreleri_kaydet()
    return jsonify({'success': True})

# ========== FİŞ (DÜZELTİLMİŞ - now değişkeni eklendi) ==========
@app.route('/fis/<int:masa_id>')
def fis(masa_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM settings WHERE id=1")
    settings = dict(c.fetchone())
    c.execute("SELECT s.*, u.ad as urun_ad, us.ad_soyad as garson_adi FROM siparisler s JOIN urunler u ON s.urun_id=u.id JOIN users us ON s.garson_id=us.id WHERE s.masa_id=? AND s.odeme_tipi='' ORDER BY s.created_at", (masa_id,))
    siparisler = [dict(s) for s in c.fetchall()]
    c.execute("SELECT m.*, k.kat_adi FROM masalar m JOIN katlar k ON m.kat_id=k.id WHERE m.id=?", (masa_id,))
    masa = dict(c.fetchone())
    toplam = sum(s['fiyat'] * s['adet'] for s in siparisler)
    conn.close()
    return render_template('fis.html', settings=settings, siparisler=siparisler, masa=masa, toplam=toplam, now=datetime.now())

# ========== KASA DEFTERI (Muhasebe) ==========
@app.route('/kasa_defteri')
def kasa_defteri():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    baslangic = request.args.get('baslangic', datetime.now().strftime('%Y-%m-%d'))
    bitis = request.args.get('bitis', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT k.*, u.ad_soyad as garson_adi FROM kasa_defteri k LEFT JOIN users u ON k.garson_id=u.id WHERE k.tarih BETWEEN ? AND ? ORDER BY k.tarih DESC, k.id DESC", (baslangic, bitis))
    hareketler = c.fetchall()
    c.execute("SELECT COALESCE(SUM(gelir), 0) as toplam_gelir, COALESCE(SUM(gider), 0) as toplam_gider FROM kasa_defteri WHERE tarih BETWEEN ? AND ?", (baslangic, bitis))
    ozet = c.fetchone()
    # Gunluk devir
    c.execute("SELECT * FROM gunluk_devir WHERE tarih BETWEEN ? AND ? ORDER BY tarih DESC", (baslangic, bitis))
    devirler = c.fetchall()
    conn.close()
    return render_template('kasa_defteri.html', hareketler=hareketler, ozet=ozet, devirler=devirler,
                           baslangic=baslangic, bitis=bitis)

@app.route('/api/kasa_defteri/ekle', methods=['POST'])
def kasa_defteri_ekle():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO kasa_defteri (tarih, aciklama, gelir, gider, odeme_tipi, kategori, belge_no, garson_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
             (data.get('tarih', datetime.now().strftime('%Y-%m-%d')), data['aciklama'],
              data.get('gelir', 0), data.get('gider', 0), data.get('odeme_tipi', 'nakit'),
              data.get('kategori', 'diger'), data.get('belge_no', ''), session['user_id']))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/gunluk_devir/kapat', methods=['POST'])
def gunluk_devir_kapat():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json()
    tarih = data.get('tarih', datetime.now().strftime('%Y-%m-%d'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) AS sayi FROM emanet_tahsilatlar WHERE durum='beklemede'")
    bekleyen_emanet = c.fetchone()['sayi']
    if bekleyen_emanet > 0:
        conn.close()
        return jsonify({'success': False, 'error': 'Merkeze teslim edilmemiş tahsilatlar var! Kasa kapanışı yapılamaz.'})
    c.execute("SELECT COALESCE(SUM(gelir), 0), COALESCE(SUM(gider), 0) FROM kasa_defteri WHERE tarih=?", (tarih,))
    gelir, gider = c.fetchone()
    kapanis = gelir - gider
    c.execute("INSERT OR REPLACE INTO gunluk_devir (tarih, kapanis_bakiye, toplam_gelir, toplam_gider, durum, kapanis_saati) VALUES (?, ?, ?, ?, 'kapali', ?)",
             (tarih, kapanis, gelir, gider, datetime.now().strftime('%H:%M')))
    # Ertesi gun acilis bakiyesi
    ertesi = (datetime.strptime(tarih, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
    c.execute("INSERT OR IGNORE INTO gunluk_devir (tarih, acilis_bakiye, durum) VALUES (?, ?, 'acik')", (ertesi, kapanis))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'kapanis_bakiye': kapanis})

# ========== VERESIYE DEFTERI (Detayli) ==========
@app.route('/veresiye_defteri')
def veresiye_defteri():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT v.*, (SELECT COALESCE(SUM(borc), 0) FROM veresiye_defteri WHERE veresiye_id=v.id) as toplam_borc, (SELECT COALESCE(SUM(tahsilat), 0) FROM veresiye_defteri WHERE veresiye_id=v.id) as toplam_tahsilat FROM veresiye v ORDER BY v.ad_soyad")
    musteriler = c.fetchall()
    conn.close()
    return render_template('veresiye_defteri.html', musteriler=musteriler)

@app.route('/veresiye_detay/<int:veresiye_id>')
def veresiye_detay(veresiye_id):
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM veresiye WHERE id=?", (veresiye_id,))
    musteri = c.fetchone()
    c.execute("SELECT * FROM veresiye_defteri WHERE veresiye_id=? ORDER BY tarih DESC, id DESC", (veresiye_id,))
    hareketler = c.fetchall()
    c.execute("SELECT COALESCE(SUM(borc), 0) as toplam_borc, COALESCE(SUM(tahsilat), 0) as toplam_tahsilat FROM veresiye_defteri WHERE veresiye_id=?", (veresiye_id,))
    ozet = c.fetchone()
    conn.close()
    return render_template('veresiye_detay.html', musteri=musteri, hareketler=hareketler, ozet=ozet)

# ========== TEDARIKCI/CARI HESAPLAR ==========
@app.route('/tedarikciler')
def tedarikciler():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT t.*, (SELECT COALESCE(SUM(borc), 0) FROM tedarikci_hareket WHERE tedarikci_id=t.id) as toplam_borc, (SELECT COALESCE(SUM(odeme), 0) FROM tedarikci_hareket WHERE tedarikci_id=t.id) as toplam_odeme FROM tedarikciler t WHERE t.aktif=1 ORDER BY t.firma_adi")
    tedarikciler = c.fetchall()
    conn.close()
    return render_template('tedarikciler.html', tedarikciler=tedarikciler)

@app.route('/tedarikci_detay/<int:tedarikci_id>')
def tedarikci_detay(tedarikci_id):
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tedarikciler WHERE id=?", (tedarikci_id,))
    tedarikci = c.fetchone()
    c.execute("SELECT * FROM tedarikci_hareket WHERE tedarikci_id=? ORDER BY tarih DESC, id DESC", (tedarikci_id,))
    hareketler = c.fetchall()
    c.execute("SELECT COALESCE(SUM(borc), 0) as toplam_borc, COALESCE(SUM(odeme), 0) as toplam_odeme FROM tedarikci_hareket WHERE tedarikci_id=?", (tedarikci_id,))
    ozet = c.fetchone()
    conn.close()
    return render_template('tedarikci_detay.html', tedarikci=tedarikci, hareketler=hareketler, ozet=ozet, bugun=datetime.now().strftime('%Y-%m-%d'))

@app.route('/api/tedarikci/ekle', methods=['POST'])
def tedarikci_ekle():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO tedarikciler (firma_adi, yetkili, telefon, vergi_dairesi, vergi_no, adres) VALUES (?, ?, ?, ?, ?, ?)",
             (data['firma_adi'], data.get('yetkili', ''), data.get('telefon', ''), data.get('vergi_dairesi', ''), data.get('vergi_no', ''), data.get('adres', '')))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/tedarikci_hareket/ekle', methods=['POST'])
def tedarikci_hareket_ekle():
    if session.get('role') != 'admin':
        return jsonify({'success': False})
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO tedarikci_hareket (tedarikci_id, tarih, aciklama, borc, odeme, belge_no) VALUES (?, ?, ?, ?, ?, ?)",
             (data['tedarikci_id'], data.get('tarih', datetime.now().strftime('%Y-%m-%d')), data['aciklama'],
              data.get('borc', 0), data.get('odeme', 0), data.get('belge_no', '')))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# =============================================================================
#  QR MENU & MUSTERI SIPARIS SISTEMI v2.0 - YENI OZELLIKLER
# =============================================================================

@app.route('/m/<uuid>')
def musteri_menu_redirect(uuid):
    """Kisa URL: /m/<uuid> -> musteri menusu"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM masalar WHERE qr_uuid=?", (uuid,))
    row = c.fetchone()
    conn.close()
    if not row:
        return render_template('404.html'), 404
    return redirect(url_for('musteri_menu', masa_id=row['id']))

@app.route('/musteri/menu/<int:masa_id>')
def musteri_menu(masa_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT m.*, k.kat_adi FROM masalar m JOIN katlar k ON m.kat_id=k.id WHERE m.id=?", (masa_id,))
    masa = c.fetchone()
    if not masa:
        conn.close()
        return render_template('404.html'), 404
    c.execute("SELECT * FROM settings WHERE id=1")
    settings = c.fetchone()
    c.execute("SELECT * FROM kategoriler WHERE aktif=1 ORDER BY ad")
    kategoriler = rows_to_dicts(c.fetchall())
    c.execute("""
        SELECT u.*, k.ad as kategori_ad, k.renk 
        FROM urunler u 
        JOIN kategoriler k ON u.kategori_id=k.id 
        WHERE u.aktif=1 AND k.aktif=1
        ORDER BY k.ad, u.ad
    """)
    urunler = rows_to_dicts(c.fetchall())
    conn.close()
    return render_template('musteri/menu_multi.html', masa=masa, settings=settings,
                           kategoriler=kategoriler, urunler=urunler, now=datetime.now())

@app.route('/musteri/durum/<int:masa_id>')
def musteri_durum(masa_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT m.*, k.kat_adi FROM masalar m JOIN katlar k ON m.kat_id=k.id WHERE m.id=?", (masa_id,))
    masa = c.fetchone()
    if not masa:
        conn.close()
        return render_template('404.html'), 404
    c.execute("SELECT * FROM settings WHERE id=1")
    settings = c.fetchone()
    c.execute("""
        SELECT s.*, u.ad as urun_ad, u.gorsel 
        FROM siparisler s 
        JOIN urunler u ON s.urun_id=u.id 
        WHERE s.masa_id=? AND s.odeme_tipi='' 
        ORDER BY s.created_at DESC
    """, (masa_id,))
    siparisler = rows_to_dicts(c.fetchall())
    conn.close()
    return render_template('musteri/durum_multi.html', masa=masa, settings=settings, siparisler=siparisler)

@app.route('/api/musteri/siparis', methods=['POST'])
def api_musteri_siparis():
    """Musteri telefonundan siparis ekleme"""
    data = request.get_json()
    masa_id = data.get('masa_id')
    urunler = data.get('urunler', [])
    notlar = data.get('notlar', '')
    if not masa_id or not urunler:
        return jsonify({'success': False, 'error': 'Eksik bilgi'})

    conn = get_db()
    c = conn.cursor()
    # Masa kontrol
    c.execute("SELECT durum FROM masalar WHERE id=?", (masa_id,))
    masa = c.fetchone()
    if not masa:
        conn.close()
        return jsonify({'success': False, 'error': 'Masa bulunamadi'})

    # Masa dolu degilse dolu yap
    c.execute("UPDATE masalar SET durum='dolu' WHERE id=? AND durum='bos'", (masa_id,))

    eklenen = 0
    for item in urunler:
        c.execute("SELECT fiyat, stok FROM urunler WHERE id=?", (item['urun_id'],))
        urun = c.fetchone()
        if urun and urun['stok'] >= item['adet']:
            c.execute("""
                INSERT INTO siparisler 
                (masa_id, garson_id, urun_id, adet, fiyat, durum, notlar, siparis_kaynak, musteri_not) 
                VALUES (?, NULL, ?, ?, ?, 'bekliyor', ?, 'musteri', ?)
            """, (masa_id, item['urun_id'], item['adet'], urun['fiyat'], notlar, notlar))
            c.execute("UPDATE urunler SET stok = stok - ? WHERE id=?", (item['adet'], item['urun_id']))
            c.execute("INSERT INTO stok_hareket (urun_id, adet, tip, aciklama) VALUES (?, ?, 'cikis', ?)",
                     (item['urun_id'], item['adet'], "QR Masa {} siparis".format(masa_id)))
            eklenen += 1
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'eklenen': eklenen})

@app.route('/api/musteri/garson-cagir/<uuid>', methods=['POST'])
def api_musteri_garson_cagir(uuid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM masalar WHERE qr_uuid=?", (uuid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Masa bulunamadi'})
    masa_id = row['id']
    c.execute("INSERT INTO musteri_bildirimler (masa_id, tip, durum) VALUES (?, 'garson', 'bekliyor')", (masa_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'mesaj': 'Garson cagrildi!'})

@app.route('/api/musteri/hesap-iste/<uuid>', methods=['POST'])
def api_musteri_hesap_iste(uuid):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id FROM masalar WHERE qr_uuid=?", (uuid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'error': 'Masa bulunamadi'})
    masa_id = row['id']
    c.execute("INSERT INTO musteri_bildirimler (masa_id, tip, durum) VALUES (?, 'hesap', 'bekliyor')", (masa_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'mesaj': 'Hesap istendi!'})

@app.route('/api/bildirimler')
def api_bildirimler():
    """Admin/Garson paneli icin musteri bildirimleri"""
    if 'user_id' not in session:
        return jsonify({'success': False})
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT b.*, m.masa_no, k.kat_adi 
        FROM musteri_bildirimler b 
        JOIN masalar m ON b.masa_id=m.id 
        JOIN katlar k ON m.kat_id=k.id 
        WHERE b.durum='bekliyor' 
        ORDER BY b.created_at DESC
    """)
    bildirimler = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'bildirimler': bildirimler})

@app.route('/api/bildirim/<int:id>/tamamla', methods=['POST'])
def api_bildirim_tamamla(id):
    if 'user_id' not in session:
        return jsonify({'success': False})
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE musteri_bildirimler SET durum='tamamlandi', updated_at=datetime('now') WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/bildirimler')
def bildirimler_paneli():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT b.*, m.masa_no, k.kat_adi
        FROM musteri_bildirimler b
        JOIN masalar m ON b.masa_id=m.id
        JOIN katlar k ON m.kat_id=k.id
        WHERE b.durum='bekliyor'
        ORDER BY b.created_at DESC
    """)
    bildirimler = [dict(row) for row in c.fetchall()]
    c.execute("SELECT COUNT(*) as bekleyen FROM musteri_bildirimler WHERE durum='bekliyor'")
    bekleyen = c.fetchone()['bekleyen']
    conn.close()
    return render_template('bildirimler.html', bildirimler=bildirimler, bekleyen=bekleyen, now=datetime.now())


@app.route('/api/bildirimler/tumunu_tamamla', methods=['POST'])
def api_bildirimler_tumunu_tamamla():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Yetkisiz'})

    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE musteri_bildirimler
        SET durum='tamamlandi', updated_at=datetime('now')
        WHERE durum='bekliyor'
    """)
    tamamlanan = c.rowcount
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'tamamlanan': tamamlanan})

@app.route('/api/masa/<int:masa_id>/qr-bilgi')
def api_masa_qr_bilgi(masa_id):
    if 'user_id' not in session:
        return jsonify({'success': False})
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT qr_uuid, masa_no FROM masalar WHERE id=?", (masa_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return jsonify({'success': False})
    host = get_host_url()
    url = "{}/m/{}".format(host, row['qr_uuid'])
    return jsonify({'success': True, 'uuid': row['qr_uuid'], 'url': url, 'masa_no': row['masa_no']})

@app.route('/qr-yazdir')
def qr_yazdir():
    """Tum masalarin QR kodlarini yazdirma sayfasi"""
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT m.*, k.kat_adi FROM masalar m JOIN katlar k ON m.kat_id=k.id WHERE m.durum!='pasif' ORDER BY k.sira, m.masa_no")
    masalar = c.fetchall()
    c.execute("SELECT * FROM settings WHERE id=1")
    settings = c.fetchone()
    conn.close()
    host = get_host_url()
    return render_template('qr_yazdir.html', masalar=masalar, settings=settings, host_url=host)

# =============================================================================
#  DIŞ SİPARİŞ / PAKET SERVİS / KURYE SİSTEMİ
# =============================================================================

DIS_PUBLIC_MENU_URL = "https://kestanelikcaybahcem.onrender.com/dis/menu"

@app.route('/dis/menu')
def dis_menu():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM settings WHERE id=1")
    settings = c.fetchone()
    c.execute("SELECT * FROM kategoriler WHERE aktif=1 ORDER BY ad")
    kategoriler = rows_to_dicts(c.fetchall())
    c.execute("""
        SELECT u.*,
               k.ad as kategori_ad,
               COALESCE(k.ad_en, k.ad) as kategori_ad_en,
               COALESCE(k.ad_ar, k.ad) as kategori_ad_ar,
               k.renk
        FROM urunler u
        JOIN kategoriler k ON u.kategori_id=k.id
        WHERE u.aktif=1 AND k.aktif=1
        ORDER BY k.ad, u.ad
    """)
    urunler = rows_to_dicts(c.fetchall())
    conn.close()
    return render_template('dis_menu.html', settings=settings, kategoriler=kategoriler, urunler=urunler, public_menu_url=get_public_menu_url(), now=datetime.now())

@app.route('/dis/durum/<int:siparis_id>')
def dis_durum(siparis_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM dis_siparisler WHERE id=?", (siparis_id,))
    siparis = c.fetchone()
    if not siparis:
        conn.close()
        return render_template('404.html'), 404
    c.execute("""
        SELECT ds.*, u.ad as urun_ad, COALESCE(u.ad_en, u.ad) as urun_ad_en, COALESCE(u.ad_ar, u.ad) as urun_ad_ar
        FROM dis_siparis_urunler ds
        JOIN urunler u ON ds.urun_id = u.id
        WHERE ds.dis_siparis_id=?
        ORDER BY ds.id
    """, (siparis_id,))
    urunler = rows_to_dicts(c.fetchall())
    conn.close()
    return render_template('dis_durum.html', siparis=siparis, urunler=urunler, now=datetime.now())

@app.route('/api/dis/siparis', methods=['POST'])
def api_dis_siparis():
    data = request.get_json() or {}
    musteri_ad = _normalize_spaces(data.get('ad_soyad', ''))
    telefon = _normalize_spaces(data.get('telefon', ''))
    adres = _normalize_spaces(data.get('adres', ''))
    odeme_tipi = data.get('odeme_tipi', 'nakit')
    notlar = data.get('notlar', '')
    nakit_verilen = float(data.get('nakit_verilen') or 0)
    urunler = data.get('urunler', [])

    if not musteri_ad or not telefon or not adres or not urunler:
        return jsonify({'success': False, 'error': 'Eksik bilgi var.'}), 400

    ensure_satis_hareketleri_table()

    conn = get_db()
    c = conn.cursor()

    toplam = 0.0
    stok_hatasi = []

    # Önce stok ve toplam kontrolü
    for item in urunler:
        urun_id = int(item.get('urun_id', 0))
        adet = int(item.get('adet', 0))
        if urun_id <= 0 or adet <= 0:
            continue

        c.execute("SELECT fiyat, stok, ad FROM urunler WHERE id=? AND aktif=1", (urun_id,))
        urun = c.fetchone()
        if not urun:
            continue

        if urun['stok'] < adet:
            stok_hatasi.append(urun['ad'])
            continue

        toplam += float(urun['fiyat']) * adet

    if stok_hatasi:
        conn.close()
        return jsonify({'success': False, 'error': 'Stok yetersiz: ' + ', '.join(stok_hatasi)}), 400

    para_ustu = max(0.0, nakit_verilen - toplam) if odeme_tipi == 'nakit' else 0.0
    tahsilat_durumu = 'beklemede'

    c.execute("""
        INSERT INTO dis_siparisler
        (musteri_ad_soyad, telefon, teslim_adres, odeme_tipi, notlar, toplam_tutar, nakit_verilen, para_ustu, durum, tahsilat_durumu)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'bekliyor', ?)
    """, (musteri_ad, telefon, adres, odeme_tipi, notlar, toplam, nakit_verilen, para_ustu, tahsilat_durumu))
    dis_siparis_id = c.lastrowid

    # Ürünleri kaydet, stok düş, stok hareketi yaz
    for item in urunler:
        urun_id = int(item.get('urun_id', 0))
        adet = int(item.get('adet', 0))
        if urun_id <= 0 or adet <= 0:
            continue

        c.execute("SELECT fiyat, stok, ad FROM urunler WHERE id=? AND aktif=1", (urun_id,))
        urun = c.fetchone()
        if not urun or urun['stok'] < adet:
            continue

        c.execute(
            "INSERT INTO dis_siparis_urunler (dis_siparis_id, urun_id, adet, fiyat) VALUES (?, ?, ?, ?)",
            (dis_siparis_id, urun_id, adet, float(urun['fiyat']))
        )

        c.execute("UPDATE urunler SET stok = stok - ? WHERE id=?", (adet, urun_id))
        c.execute(
            "INSERT INTO stok_hareket (urun_id, adet, tip, aciklama) VALUES (?, ?, 'cikis', ?)",
            (urun_id, adet, f'Dış sipariş #{dis_siparis_id}')
        )

    # Dış satış defterine ve kasa'ya yaz
    c.execute("""
        INSERT INTO satis_hareketleri (kanal, kaynak_turu, kaynak_id, tutar, odeme_tipi, aciklama)
        VALUES ('dis', 'dis', ?, ?, ?, ?)
    """, (dis_siparis_id, toplam, odeme_tipi, f'Dış sipariş #{dis_siparis_id}'))

    c.execute(
        "INSERT INTO kasa (tip, tutar, aciklama, odeme_tipi, garson_id) VALUES (?, ?, ?, ?, ?)",
        ('gelir', toplam, f'Dış sipariş #{dis_siparis_id}', odeme_tipi, session.get('user_id'))
    )

    if odeme_tipi == 'nakit':
        c.execute("""
            INSERT INTO emanet_tahsilatlar (kaynak_turu, kaynak_id, tutar, odeme_tipi, durum, aciklama, teslim_eden)
            VALUES ('dis', ?, ?, 'nakit', 'beklemede', ?, ?)
        """, (dis_siparis_id, toplam, f'Dış sipariş #{dis_siparis_id}', session.get('username', 'sistem')))

    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'siparis_id': dis_siparis_id,
        'toplam': toplam,
        'para_ustu': para_ustu
    })

@app.route('/dis/mutfak')
def dis_mutfak():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM dis_siparisler
        WHERE durum IN ('bekliyor','hazirlaniyor','hazir','kurye_teslim','teslim_edildi')
        ORDER BY created_at DESC
    """)
    siparisler = rows_to_dicts(c.fetchall())
    for s in siparisler:
        c.execute("""
            SELECT ds.*, u.ad as urun_ad, COALESCE(u.ad_en, u.ad) as urun_ad_en, COALESCE(u.ad_ar, u.ad) as urun_ad_ar
            FROM dis_siparis_urunler ds
            JOIN urunler u ON ds.urun_id=u.id
            WHERE ds.dis_siparis_id=?
            ORDER BY ds.id
        """, (s['id'],))
        s['urunler'] = rows_to_dicts(c.fetchall())
    conn.close()
    return render_template('dis_mutfak.html', siparisler=siparisler, now=datetime.now())

@app.route('/dis/kurye')
def dis_kurye():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM dis_siparisler
        WHERE durum IN ('kurye_teslim', 'teslim_edildi')
        ORDER BY updated_at DESC, created_at DESC
    """)
    siparisler = rows_to_dicts(c.fetchall())
    for s in siparisler:
        c.execute("""
            SELECT ds.*, u.ad as urun_ad
            FROM dis_siparis_urunler ds
            JOIN urunler u ON ds.urun_id=u.id
            WHERE ds.dis_siparis_id=?
            ORDER BY ds.id
        """, (s['id'],))
        s['urunler'] = rows_to_dicts(c.fetchall())
    conn.close()
    return render_template('dis_kurye.html', siparisler=siparisler, now=datetime.now())

@app.route('/api/dis/siparis/<int:siparis_id>/durum', methods=['POST'])
def api_dis_siparis_durum(siparis_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Yetkisiz'})
    data = request.get_json() or {}
    durum = data.get('durum')
    if durum not in ('bekliyor', 'hazirlaniyor', 'hazir', 'kurye_teslim', 'teslim_edildi'):
        return jsonify({'success': False, 'error': 'Geçersiz durum'})
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE dis_siparisler SET durum=?, updated_at=datetime('now') WHERE id=?", (durum, siparis_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/dis/siparis/<int:siparis_id>/teslim', methods=['POST'])
def api_dis_siparis_teslim(siparis_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Yetkisiz'})
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT odeme_tipi FROM dis_siparisler WHERE id=?", (siparis_id,))
    row = c.fetchone()
    odeme_tipi = row['odeme_tipi'] if row else 'nakit'
    if odeme_tipi == 'kart':
        c.execute("UPDATE dis_siparisler SET durum='teslim_edildi', tahsilat_durumu='odendi', updated_at=datetime('now') WHERE id=?", (siparis_id,))
    else:
        c.execute("UPDATE dis_siparisler SET durum='teslim_edildi', updated_at=datetime('now') WHERE id=?", (siparis_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/dis/siparis/<int:siparis_id>/merkeze-al', methods=['POST'])
def api_dis_siparis_merkeze_al(siparis_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Yetkisiz'})
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE emanet_tahsilatlar
        SET durum='merkezde', teslim_alan=?, updated_at=datetime('now')
        WHERE kaynak_turu='dis' AND kaynak_id=? AND durum='beklemede'
    """, (session.get('username', ''), siparis_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/tahsilatlar')
def tahsilatlar():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM emanet_tahsilatlar ORDER BY durum ASC, created_at DESC")
    tahsilatlar = [dict(row) for row in c.fetchall()]
    conn.close()
    return render_template('tahsilatlar.html', tahsilatlar=tahsilatlar, now=datetime.now())

@app.route('/api/tahsilat/<int:tahsilat_id>/merkeze-al', methods=['POST'])
def api_tahsilat_merkeze_al(tahsilat_id):
    if session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Yetkisiz'})
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE emanet_tahsilatlar SET durum='merkezde', teslim_alan=?, updated_at=datetime('now') WHERE id=?", (session.get('username', ''), tahsilat_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/qr/dis')
def qr_dis_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('qr_dis.html', public_menu_url=get_public_menu_url(), now=datetime.now())

@app.route('/qr/dis.png')
def qr_dis_png():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Yetkisiz'}), 403
    payload = _build_dis_qr_bytes()
    return send_file(BytesIO(payload), mimetype='image/png', download_name='dis_menu_qr.png')

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    import traceback
    return jsonify({'error': 'Sunucu hatasi', 'message': str(e), 'traceback': traceback.format_exc()}), 500

if __name__ == '__main__':
    init_db()
    ensure_menu_translations()
    ensure_satis_hareketleri_table()
    sifreleri_kaydet()
    print("=========================================")
    print("   CAY BAHCESI PRO v10.0 + QR MENU")
    print("   Restaurant POS Sistemi")
    print("=========================================")
    print()
    port = int(os.environ.get('PORT', 9000))
    print(f"Yerel erisim:  http://localhost:{port}")
    print(f"Ag erisimi:   http://0.0.0.0:{port}")
    print()
    print("Musteri QR Menu: /m/<uuid>")
    print("Ornek: http://localhost:8000/m/abc123...")
    print()
    print("Varsayilan giris:")
    print("  Kullanici: admin")
    print("  Sifre:     admin123")
    print()
    print("Sifreler: sifreler.md dosyasinda")
    print("=========================================")
    app.run(host='0.0.0.0', port=port, debug=False)
