# 🌍 Nation Builder - Telegram Bot Game

Game simulasi pemerintahan negara yang bisa dimainkan di grup dan private chat Telegram.

## 🎮 Fitur

### 🏛️ Bangun & Kelola Negara
- Pilih ideologi: Demokrasi, Monarki, Komunis, Junta Militer, Teokrasi
- Kelola sumber daya: uang, makanan, material, minyak
- Bangun infrastruktur: pabrik, pertanian, tambang, sumur minyak
- Kumpulkan pendapatan secara berkala

### 💰 Ekonomi
- Sistem pajak yang mempengaruhi kebahagiaan rakyat
- Bangun fasilitas produksi
- Riset teknologi
- GDP & inflasi dinamis

### ⚔️ Militer
- Rekrut tentara, beli tank, jet, kapal, rudal
- Upgrade pertahanan & teknologi militer
- Riset senjata nuklir (membutuhkan tech level tinggi)
- Sistem moral tentara

### 🗳️ Politik Dalam Negeri
- 8 kebijakan yang bisa diterapkan
- Sistem pemilu (untuk negara demokrasi)
- Ganti bentuk pemerintahan (risiko pemberontakan!)
- Kelola korupsi, kebebasan, stabilitas

### 🤝 Diplomasi
- Buat & gabung aliansi
- Kirim bantuan ke negara lain
- Jatuhkan sanksi ekonomi
- Sistem reputasi internasional

### 💥 Perang
- Deklarasi perang ke negara lain
- Sistem pertempuran ronde (Best of 5)
- Rampasan perang & reparasi
- Luncurkan senjata nuklir!
- Opsi menyerah

### 📰 Event Random
- 18 jenis event: bencana alam, krisis, bonus
- Otomatis terjadi berkala
- Diumumkan ke semua grup

### 👑 Super Admin
- Kelola semua negara (edit resource, hapus)
- Stop/mulai perang
- Trigger event manual
- Beri resource ke pemain
- Setting game (aktif/nonaktif, frekuensi event)
- Broadcast pesan ke semua
- Export data & Reset game

---

## 🚀 Cara Deploy ke Railway

### Langkah 1: Buat Bot Telegram
1. Buka [@BotFather](https://t.me/BotFather) di Telegram
2. Kirim `/newbot`
3. Ikuti instruksi, beri nama bot
4. **Simpan TOKEN** yang diberikan (contoh: `7123456789:AAF...`)
5. Dapatkan **User ID** kamu dari [@userinfobot](https://t.me/userinfobot)

### Langkah 2: Upload ke GitHub
1. Buat repository baru di GitHub
2. Upload **semua file** dari project ini ke repository

Struktur file yang harus ada:
```
nation-game/
├── bot.py
├── requirements.txt
├── Procfile
├── runtime.txt
├── nixpacks.toml
├── .gitignore
├── data/
│   └── .gitkeep
├── models/
│   ├── __init__.py
│   └── database.py
├── handlers/
│   ├── __init__.py
│   ├── start.py
│   ├── nation.py
│   ├── economy.py
│   ├── military.py
│   ├── politics.py
│   ├── diplomacy.py
│   ├── war.py
│   ├── events.py
│   ├── admin.py
│   └── group.py
└── utils/
    ├── __init__.py
    └── helpers.py
```

### Langkah 3: Deploy di Railway
1. Buka [railway.app](https://railway.app) dan login dengan GitHub
2. Klik **"New Project"**
3. Pilih **"Deploy from GitHub repo"**
4. Pilih repository yang sudah kamu buat
5. Railway akan otomatis detect dan mulai build

### Langkah 4: Tambahkan Variables di Railway
Buka tab **"Variables"** di Railway dan tambahkan:

| Variable | Nilai | Keterangan |
|----------|-------|------------|
| `BOT_TOKEN` | `7123456789:AAF...` | Token dari BotFather |
| `SUPER_ADMIN_ID` | `123456789` | User ID Telegram kamu |
| `WEBHOOK_URL` | `https://nama-project.up.railway.app` | URL dari Railway (lihat di Settings → Domains) |
| `PORT` | `8080` | Port untuk webhook |

### Langkah 5: Generate Domain
1. Di Railway, buka tab **"Settings"**
2. Scroll ke **"Networking"** → **"Generate Domain"**
3. Copy URL yang muncul (contoh: `https://nation-game-production.up.railway.app`)
4. Paste URL ini sebagai nilai `WEBHOOK_URL` di Variables

### Langkah 6: Redeploy
Setelah semua variable ditambahkan, Railway akan otomatis redeploy. Bot seharusnya sudah berjalan!

---

## 📋 Perintah Bot

### Private Chat
| Perintah | Fungsi |
|----------|--------|
| `/start` | Mulai game / Daftar negara |
| `/help` | Panduan bermain |
| `/negara` | Lihat info negara |
| `/ekonomi` | Panel ekonomi |
| `/militer` | Panel militer |
| `/politik` | Panel politik |
| `/diplomasi` | Panel diplomasi |
| `/perang` | Panel perang |
| `/event` | Lihat event terkini |
| `/ranking` | Ranking negara |
| `/admin` | Panel super admin |

### Group Chat
| Perintah | Fungsi |
|----------|--------|
| `/start` | Daftarkan grup |
| `/ranking` | Ranking dunia |
| `/wars` | Perang aktif |
| `/news` | Berita terkini |

---

## ⚠️ Catatan Penting

- **Database** menggunakan TinyDB (file JSON). Data akan reset jika Railway re-deploy dari awal. Untuk database permanen, pertimbangkan upgrade ke PostgreSQL.
- **Event random** terjadi otomatis setiap 1 jam (default). Bisa diubah dari panel admin.
- **Webhook URL** harus sama persis dengan domain Railway (termasuk `https://`).
- Jika bot tidak merespons, cek **Logs** di Railway untuk melihat error.
