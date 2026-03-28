# 🐱 Retro Scraper - Instagram Data Extractor

Aplikasi Flask + Selenium untuk melakukan scraping Feed dan Reels Instagram (Gambar, Teks/Caption, dan Audio/Video).

[![Saweria](https://img.shields.io/badge/Saweria-Support%20Me-yellow?style=for-the-badge&logo=coffee)](https://saweria.co/dzikrizk24)
## 🚀 Menjalankan Secara Lokal (Direkomendasikan)
Karena Instagram memiliki keamanan yang ketat, aplikasi ini mengandalkan **Login Manual** melalui browser Chrome yang muncul di layar komputer Anda. Oleh karena itu, menjalankan aplikasi ini di komputer lokal sangat direkomendasikan.

1. Buka terminal/CMD.
2. Jalankan `pip install -r requirements.txt`.
3. Jalankan `python app.py`.
4. Buka `http://localhost:5000` di browser Anda.

---

## ☁️ Tutorial Hosting ke Render (Production)

Aplikasi ini dapat di-host di platform Render menggunakan **Docker** karena kita membutuhkan instalasi Google Chrome secara internal.

> **⚠️ PERHATIAN PENTING SEBELUM DEPLOY:**
> Jika Anda melakukan hosting di cloud server (seperti Render), browser Chrome akan berjalan di latar belakang (Headless Mode) tanpa GUI. **Anda tidak akan bisa melihat jendela Chrome untuk melakukan login manual**. Instagram kemungkinan besar akan membatasi atau memblokir akses scraping anonim.

### Langkah-langkah Deployment:

1. Buat repositori baru di akun **GitHub** Anda.
2. Push (unggah) semua file project ini ke repositori GitHub tersebut.
3. Buat akun dan login ke Render.com.
4. Klik tombol **New +** di pojok kanan atas, lalu pilih **Web Service**.
5. Hubungkan akun GitHub Anda dan pilih repositori yang baru saja dibuat.
6. Pada bagian pengaturan deployment:
   - **Name**: `instagram-scraper-retro` (atau bebas)
   - **Region**: Bebas (pilih yang terdekat, misal: Singapore)
   - **Branch**: `main` (atau `master`)
   - **Runtime**: Pilih **Docker** (Sangat Penting! Render akan membaca file `Dockerfile`).
   - **Instance Type**: Pilih `Free` (gratis) atau tingkatan berbayar jika butuh memori lebih besar.
7. Klik **Create Web Service**.
8. Render akan mulai mem-build Docker image (ini akan memakan waktu beberapa menit karena mengunduh Chrome).
9. Setelah status berubah menjadi *Live*, Anda bisa mengakses aplikasi lewat URL yang diberikan Render (misal: `https://nama-aplikasi.onrender.com`).

### Catatan Production:
- Timeout Gunicorn diset ke `600` detik agar proses scraping yang lama tidak diputus paksa oleh server.
- Pada paket Free Render, semua file hasil download yang disimpan di folder `scraped_data` akan hilang jika server restart (karena sistem file ephemereal). Segera *download ZIP* setelah proses scraping selesai.