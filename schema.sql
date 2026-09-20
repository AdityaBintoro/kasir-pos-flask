DROP TABLE IF EXISTS produk;
DROP TABLE IF EXISTS transaksi;
DROP TABLE IF EXISTS detail_transaksi;

CREATE TABLE produk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    harga INTEGER NOT NULL,
    stok INTEGER NOT NULL
);

CREATE TABLE transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_harga INTEGER NOT NULL,
    bayar INTEGER NOT NULL,
    kembalian INTEGER NOT NULL
);
CREATE TABLE detail_transaksi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaksi_id INTEGER NOT NULL,
    produk_id INTEGER NOT NULL,
    jumlah INTEGER NOT NULL,
    harga_satuan INTEGER NOT NULL,
    subtotal INTEGER NOT NULL,
    FOREIGN KEY (transaksi_id) REFERENCES transaksi (id) ON DELETE CASCADE,
    FOREIGN KEY (produk_id) REFERENCES produk (id)
);


-- Data contoh untuk pengujian awal
INSERT INTO produk (nama, harga, stok) VALUES 
('Kopi Hitam', 10000, 20),
('Es Teh Manis', 5000, 50),
('Roti Bakar', 15000, 15);