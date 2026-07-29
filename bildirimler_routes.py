from flask import render_template, jsonify, session, redirect, url_for
from datetime import datetime
from database import get_db

@app.route('/bildirimler')
def bildirimler_paneli():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT b.*, m.masa_no, k.kat_adi
        FROM musteri_bildirimler b
        JOIN masalar m ON b.masa_id = m.id
        JOIN katlar k ON m.kat_id = k.id
        WHERE b.durum = 'bekliyor'
        ORDER BY b.created_at DESC
    """)
    bildirimler = [dict(row) for row in c.fetchall()]

    c.execute("SELECT COUNT(*) AS bekleyen FROM musteri_bildirimler WHERE durum='bekliyor'")
    bekleyen = c.fetchone()['bekleyen']

    conn.close()
    return render_template(
        'bildirimler.html',
        bildirimler=bildirimler,
        bekleyen=bekleyen,
        now=datetime.now()
    )

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
