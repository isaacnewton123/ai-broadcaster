# Bot Broadcaster (Sosmed Hub)

Selamat datang di arsitektur **Bot Broadcaster**! Ini adalah *microservice* khusus yang bertugas sebagai Pusat Distribusi (Publisher) untuk ekosistem Nyarikerja.online.

Berbeda dengan bot scraper yang mengotori tangan mencari data, bot ini didesain secara elegan dengan arsitektur **Immutable & Consumer Tracking**. Artinya, bot ini **HARAM** hukumnya mengubah, mengedit, apalagi menghapus data dari database utama scraper.

## 🏗 Arsitektur Sistem

Arsitektur bot ini menganut prinsip *Decoupling* (Pemisahan Tugas):
1. **Zero Interference (100% Read-Only):** Bot hanya diberikan hak membaca (`Read`) pada koleksi utama `jobs`.
2. **Consumer Tracking (Buku Catatan Terpisah):** Setelah bot memposting sebuah loker, bot tidak akan menyisipkan tanda *is_posted* di koleksi `jobs`. Sebaliknya, bot akan menuliskan *slug* loker tersebut ke dalam koleksi miliknya sendiri yang bernama `broadcast_history`.
3. **Queue & Throttle (Anti-Spam):** Dilengkapi dengan sistem antrean cerdas untuk membatasi kecepatan posting (1 pesan per 15 detik) jika terjadi *burst* / penumpukan loker. Jika sedang kosong, loker akan diposting seketika tanpa jeda.

## 🔄 Workflow Alur Kerja

Berikut adalah siklus hidup bagaimana sebuah loker terdistribusi dari MongoDB hingga ke genggaman *followers* di Telegram:

1. **TRIGGER (Bot Scraper Bekerja)**
   - `bot-bukajobs` atau `bot-disnakerja` selesai mengekstrak loker dan menyimpannya di koleksi `jobs`.
   - Proses ini berjalan di *background*, dan bot scraper sama sekali tidak menyadari keberadaan bot broadcaster ini.

2. **POLLING (Bot Broadcaster Siaga)**
   - Bot ini berjalan 24/7 dengan `while True` loop (tanpa Cronjob).
   - Setiap 5 menit, bot menelusuri koleksi `jobs` dan melakukan pengecekan silang (*cross-check*): *"Berikan saya semua loker di koleksi `jobs` yang nama/slug-nya BELUM TERCATAT di koleksi `broadcast_history` saya!"*
   - Semua loker yang lolos filter ini akan dimasukkan ke dalam **Antrean Posting (Queue)** memori bot.

3. **PROCESSING (AI Rewrite, Render Visual, & Pengiriman)**
   - Bot Broadcaster mengambil 1 loker teratas dari Antrean.
   - **AI Universal Caption:** Teks loker mentah dari database akan dikirim ke Gemini AI (`ai_social_rewriter.py`). Gemini akan menyulap teks kaku tersebut menjadi satu *Caption Universal* bergaya sosmed kekinian (Singkat, Padat, Emoji, Gaji disorot, dan Call-to-Action). Caption ini didesain agar kompatibel 100% di Telegram, Instagram, dan Facebook tanpa perlu di-rewrite ulang!
   - **Poster Instan:** Menggunakan script `poster_telegram.py`, bot akan "melukis" Poster Loker Elegan beresolusi `1080x1350`. Poster ini dirender murni secara instan di dalam memori (`BytesIO`) tanpa pernah disimpan ke harddisk atau R2, sehingga memori server 100% hemat.
   - Bot mengirimkan gambar poster tersebut beserta *Caption AI Universal* ke Channel Telegram Publik Anda (menggunakan HTTP Telegram Bot API dari @BotFather).

4. **RECORDING (Pencatatan Sejarah)**
   - Detik setelah pesan terkirim dengan sukses ke Telegram, bot menyimpan 1 baris dokumen kecil ke dalam koleksi `broadcast_history` miliknya di MongoDB.
   - Contoh dokumen yang disimpan: `{ "slug": "lowongan-kerja-pt-telkomsel-jakarta", "posted_at": "2026-06-03T16:00:00Z" }`.
   - Ini memastikan loker ini tidak akan pernah terkirim dua kali.

5. **THROTTLING (Jeda Aman)**
   - Bot tertidur secara paksa selama 15 detik.
   - Jika antrean masih ada, proses akan berulang ke Langkah 3. Jika antrean sudah habis, bot kembali ke Langkah 2.

## 📁 Struktur File

```
bot-broadcaster/
├── main.py                      # Orchestrator utama (polling + queue + throttle + health server)
├── config.py                    # Konfigurasi terpusat (.env loader + konstanta bertipe)
├── logger.py                    # Logging terpusat ke stdout
├── database.py                  # Koneksi MongoDB Atlas + query jobs + record history
├── ai_social_rewriter.py        # Gemini AI universal caption generator
├── telegram_publisher.py        # HTTP Bot API sender (foto + caption)
│
├── poster_common.py             # Shared utilities (warna, font, ikon, background)
├── poster_telegram.py           # Poster Telegram Channel (1080x1350) ✅ AKTIF
├── poster_instagram.py          # Poster IG Feed (1080x1080) 🔒 TODO
├── poster_facebook.py           # Poster FB/OG Web (1200x630) 🔒 TODO
├── generate_image_for_post.py   # File asli (legacy, backup referensi)
│
├── seed_history.py              # Script seeding data lawas (1x seumur hidup)
├── requirements.txt             # Dependensi Python
├── .env                         # Environment variables (JANGAN di-commit!)
├── .env.example                 # Template environment variables
├── fonts/                       # Font Inter (Google Fonts Variable)
└── assets/                      # Aset gambar pendukung
```

### Prinsip: 1 File = 1 Tugas

| File | Tanggung Jawab Tunggal |
|---|---|
| `config.py` | Baca `.env`, validasi, export konstanta |
| `logger.py` | Logging ke stdout |
| `database.py` | Koneksi MongoDB + query + record |
| `ai_social_rewriter.py` | Gemini AI → caption sosmed |
| `telegram_publisher.py` | Kirim foto/teks via Bot API |
| `poster_common.py` | Shared: warna, font, ikon, background |
| `poster_telegram.py` | Render poster Telegram (1080x1350) |
| `poster_instagram.py` | 🔒 TODO: Render poster IG (1080x1080) |
| `poster_facebook.py` | 🔒 TODO: Render poster FB (1200x630) |
| `seed_history.py` | Seeding data lawas |
| `main.py` | Orchestrator utama |

## 🚀 Persiapan Deployment

### 1. Isi file `.env`
File `.env` sudah disiapkan. Anda hanya perlu mengisi:
- `TELEGRAM_BOT_TOKEN` → Dapatkan dari @BotFather
- `TELEGRAM_PUBLISH_CHANNEL` → Username channel Anda (misal: `@nyarikerja_online`)

### 2. Install dependensi
```bash
pip install -r requirements.txt
```

### 3. Jalankan Seeding (WAJIB sebelum deployment pertama!)

> [!WARNING]
> **JANGAN LANGSUNG MENYALAKAN BOT BROADCASTER UNTUK PERTAMA KALINYA!**

Karena di dalam database Anda sudah ada ratusan data loker lawas, menyalakan bot ini secara mendadak akan membuat bot menganggap ratusan loker tersebut sebagai "Loker Baru yang Belum Terkirim". Akibatnya, bot akan melakukan *spam* ratusan loker kedaluwarsa ke Channel Anda.

```bash
python seed_history.py
```

Script ini hanya dijalankan **SATU KALI** seumur hidup.

### 4. Jalankan Bot
```bash
python main.py
```

### 5. Deploy ke Render.com
| Setting | Value |
|---|---|
| **Start Command** | `python main.py` |
| **Build Command** | `pip install -r requirements.txt` |
| **Health Check Path** | `/ping` |

## ⚙️ Environment Variables

| Variabel | Deskripsi | Sumber |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Token dari @BotFather | [BotFather](https://t.me/BotFather) |
| `TELEGRAM_PUBLISH_CHANNEL` | Username/ID Channel Publik | Telegram |
| `GEMINI_API_KEY` | API Key Gemini AI | [Google AI Studio](https://aistudio.google.com/apikey) |
| `MONGODB_URI` | Connection string MongoDB Atlas | MongoDB Atlas Dashboard |
| `MONGODB_DB_NAME` | Nama database (default: `nyarikerja_db`) | Opsional |
| `MONGODB_JOBS_COLLECTION` | Nama koleksi loker (default: `jobs`) | Opsional |
| `MONGODB_HISTORY_COLLECTION` | Nama koleksi history (default: `broadcast_history`) | Opsional |
| `POLL_INTERVAL_SECONDS` | Interval polling (default: `300`) | Opsional |
| `THROTTLE_DELAY_SECONDS` | Jeda antar posting (default: `15`) | Opsional |
| `PORT` | Port health server (default: `10000`) | Opsional |

> **Catatan Teknis:** Karena kita menggunakan Bot Resmi dari BotFather, kita **TIDAK PERLU** lagi repot mendaftar `TELEGRAM_API_ID` atau `API_HASH`. Kita bisa langsung mengirim pesan dan gambar secara instan menggunakan standard *HTTP Bot API* dari Telegram!
