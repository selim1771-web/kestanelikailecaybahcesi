import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cay_bahcesi.db')

try:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Eksik olan host_url sütununu tabloya ekliyoruz
    c.execute("ALTER TABLE settings ADD COLUMN host_url TEXT DEFAULT 'http://localhost:8000'")
    conn.commit()
    print("Başarılı: 'host_url' sütunu veritabanına eklendi!")
except sqlite3.OperationalError as e:
    print(f"Uyarı: {e} (Sütun zaten var olabilir veya başka bir sorun var)")
finally:
    conn.close()