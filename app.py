import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_kasir_pos'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'database.db')
SCHEMA = os.path.join(BASE_DIR, 'schema.sql')

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  
    return conn

def init_db():
    conn = get_db_connection()
    with open(SCHEMA, mode='r', encoding='utf-8') as f:
        conn.executescript(f.read())
    conn.close()

@app.route('/')
def index():
    conn = get_db_connection()
    produk_list = conn.execute('SELECT * FROM produk').fetchall()
    conn.close()

    keranjang = session.get('keranjang', {})

    total_harga = 0
    for item in keranjang.values():
        total_harga += item['harga'] * item['qty']

    return render_template(
        'index.html', 
        produk_list=produk_list, 
        keranjang=keranjang, 
        total_harga=total_harga
    )

@app.route('/keranjang/<int:produk_id>', methods=['POST'])
def tambah_keranjang(produk_id):
    conn = get_db_connection()
    produk = conn.execute('SELECT * FROM produk WHERE id = ?', (produk_id,)).fetchone()
    conn.close()

    if produk:
        raw_qty = request.form.get('qty')
        try:
            input_qty = int(raw_qty) if raw_qty else 1
            if input_qty < 1:
                input_qty = 1
        except ValueError:
            input_qty = 1

        if 'keranjang' not in session:
            session['keranjang'] = {}

        keranjang = session['keranjang']
        p_id = str(produk_id)

        # 2. Hitung jumlah qty baru
        if p_id in keranjang:
            qty_sekarang = keranjang[p_id]['qty']
            qty_baru = qty_sekarang + input_qty
            
            # Batasi agar tidak melebih stok
            if qty_baru > produk['stok']:
                keranjang[p_id]['qty'] = produk['stok']
            else:
                keranjang[p_id]['qty'] = qty_baru
        else:
            # Jika produk baru ditambahkan ke keranjang
            initial_qty = min(input_qty, produk['stok'])
            keranjang[p_id] = {
                'id': produk['id'],
                'nama': produk['nama'],
                'harga': produk['harga'],
                'qty': initial_qty,
                'stok': produk['stok']
            }

        session['keranjang'] = keranjang
        session.modified = True 

    return redirect(url_for('index'))
@app.route('/hapus_keranjang/<int:produk_id>', methods=['POST'])
def hapus_keranjang(produk_id):
    keranjang = session.get('keranjang', {})
    p_id = str(produk_id)

    if p_id in keranjang:
        del keranjang[p_id]
        session['keranjang'] = keranjang
        session.modified = True

    return redirect(url_for('index'))

@app.route('/clear_keranjang', methods=['POST', 'GET'])
def clear_keranjang():
    session.pop('keranjang', None)
    return redirect(url_for('index'))

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'GET':
        return redirect(url_for('index'))

    keranjang = session.get('keranjang', {})
    if not keranjang:
        return redirect(url_for('index'))

    total_harga = sum(item['harga'] * item['qty'] for item in keranjang.values())
    try:
        bayar = int(request.form.get('bayar', 0))
    except (TypeError, ValueError):
        session['error'] = 'Nominal pembayaran harus berupa angka!'
        return redirect(url_for('index'))

    if bayar < total_harga:
        session['error'] = 'Uang pembayaran tidak mencukupi!'
        return redirect(url_for('index'))

    kembalian = bayar - total_harga

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        'INSERT INTO transaksi (total_harga, bayar, kembalian) VALUES (?, ?, ?)',
        (total_harga, bayar, kembalian)
    )

    trx_id = cursor.lastrowid

    for item in keranjang.values():
        cursor.execute(
            'INSERT INTO detail_transaksi (transaksi_id, produk_id, jumlah, harga_satuan, subtotal) VALUES (?, ?, ?, ?, ?)',
            (trx_id, item['id'], item['qty'], item['harga'], item['harga'] * item['qty'])
        )

    # Update stok
    for item in keranjang.values():
        cursor.execute(
            'UPDATE produk SET stok = stok - ? WHERE id = ?',
            (item['qty'], item['id'])
        )

    conn.commit()
    conn.close()

    session.pop('keranjang', None)
    session['sukses'] = f'Transaksi Berhasil! Kembalian: Rp {kembalian:,}'

    return redirect(url_for('struk', transaksi_id=trx_id))

@app.route('/riwayat')
def riwayat():
    conn = get_db_connection()
    transaksi_list = conn.execute('SELECT * FROM transaksi order by tanggal desc').fetchall()
    conn.close()

    return render_template('riwayat.html', transaksi_list=transaksi_list)

@app.route('/produk')
def produk():
    conn = get_db_connection()
    produk_list = conn.execute('SELECT * FROM produk ORDER BY nama').fetchall()
    conn.close()
    return render_template('produk.html', produk=produk_list)

@app.route('/produk/tambah', methods=['POST'])
def tambah_produk():
    nama = request.form.get('nama_produk', '').strip()
    try:
        harga = int(request.form.get('harga', 0))
        stok = int(request.form.get('stok', 0))
    except (TypeError, ValueError):
        session['error'] = 'Harga dan stok harus berupa angka!'
        return redirect(url_for('produk'))

    if not nama or harga < 0 or stok < 0:
        session['error'] = 'Nama, harga, dan stok harus diisi dengan benar!'
        return redirect(url_for('produk'))

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO produk (nama, harga, stok) VALUES (?, ?, ?)',
        (nama, harga, stok)
    )
    conn.commit()
    conn.close()
    return redirect(url_for('produk'))

@app.route('/produk/hapus/<int:id>')
def hapus_produk(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM produk WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('produk'))

@app.route('/edit_produk/<int:produk_id>', methods=['POST'])
def edit_produk(produk_id):
    nama = request.form.get('nama', '').strip()
    try:
        harga = int(request.form.get('harga', 0))
        stok = int(request.form.get('stok', 0))
    except (TypeError, ValueError):
        session['error'] = 'Harga dan stok harus berupa angka!'
        return redirect(url_for('produk'))

    if not nama or harga < 0 or stok < 0:
        session['error'] = 'Nama, harga, dan stok harus diisi dengan benar!'
        return redirect(url_for('produk'))

    conn = get_db_connection()
    conn.execute(
        'UPDATE produk SET nama = ?, harga = ?, stok = ? WHERE id = ?',
        (nama, harga, stok, produk_id),
    )
    conn.commit()
    conn.close()

    session['sukses'] = 'Produk berhasil diperbarui.'
    return redirect(url_for('produk'))
   

@app.route('/struk/<int:transaksi_id>')
def struk(transaksi_id):
    conn = get_db_connection()
    transaksi = conn.execute('SELECT * FROM transaksi WHERE id = ?', (transaksi_id,)).fetchone()
    detail = conn.execute(
        '''SELECT detail_transaksi.*, produk.nama AS nama_produk
           FROM detail_transaksi
           JOIN produk ON produk.id = detail_transaksi.produk_id
           WHERE transaksi_id = ?''',
        (transaksi_id,)
    ).fetchall()
    conn.close()

    if not transaksi:
        return redirect(url_for('riwayat'))

    return render_template('struk.html', trx=transaksi, detail=detail)



if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
        print("[✓] Database SQLite berhasil dibuat!")

    app.run(debug=True)