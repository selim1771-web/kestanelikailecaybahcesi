import sqlite3
import os

# Kullanıcıdan IP adresini al
ip_adresi = input("Lütfen cmd ekranında bulduğunuz IPv4 adresini yazın (Örn: 192.168.1.45): ")
yeni_url = f"http://{ip_adresi.strip()}:8000"

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cay_bahcesi.db')
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Ayarlardaki URL'yi güncelle
c.execute("UPDATE settings SET host_url = ? WHERE id = 1", (yeni_url,))
conn.commit()
conn.close()

print(f"Başarılı! QR kodlarınız artık bu adrese yönlendirecek: {yeni_url}")