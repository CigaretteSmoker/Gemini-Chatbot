
***

# Multi-Model AI Chat Client with Google Gen AI SDK

Sebuah aplikasi desktop berbasis **Tkinter** yang dirancang sebagai antarmuka obrolan (*chat client*) dengan integrasi **Google Gen AI SDK**. Aplikasi ini mengadopsi prinsip *Clean Architecture* dan *Domain-Driven Design (DDD)* serta mendukung berbagai fitur tingkat lanjut seperti pencarian web (*Google Search Grounding*), eksekusi kode terisolasi (*sandbox*), serta pengelolaan berkas proyek secara efisien.

---

## ✦ Fitur Utama

1. **Pemilihan Model Dinamis (*On-the-fly Model Switching*)**
   Mendukung pengalihan model secara langsung selama sesi obrolan tanpa kehilangan riwayat konteks percakapan yang sedang berjalan. Model yang tersedia meliputi:
   * **Gemini 3.5 (Flash)**
   * **Gemini 3.0 (Pro)**
   * **Gemini 2.5 (Flash)**
   * **Gemma 4 31B IT**

2. **Google Search Grounding & Rujukan Sumber**
   Model secara aktif melakukan pencarian internet apabila diperlukan dan aplikasi akan menyajikan daftar judul beserta URL tautan eksternal yang valid sebagai bahan rujukan di bawah pesan respons.

3. **Python Sandbox Code Execution**
   Mengeksekusi baris kode pemrograman Python di lingkungan sandbox terisolasi milik Google. Hasil eksekusi (*stdout*/*stderr*) serta kode yang dieksekusi akan ditunjukkan secara terstruktur di dalam log obrolan.

4. **Project Bundler (Folder Attachment)**
   Memetakan struktur direktori proyek lokal dan menggabungkan konten berkas teks/kode menjadi satu berkas konteks teks sebelum diunggah ke LLM. Fitur ini dirancang untuk memudahkan analisis kode berskala proyek (*codebase*).

5. **Clipboard Image Grabber**
   Mendukung penempelan (*paste*) gambar langsung dari clipboard sistem operasi (menggunakan pintasan tombol `Ctrl + V` pada kolom input teks) tanpa harus menyimpan berkas secara manual terlebih dahulu.

6. **Manajemen Riwayat Lokal (Auto-Save & Manual)**
   Menyimpan obrolan secara berkala ke berkas `gemini_chat_history.json` secara otomatis dan menyediakan opsi pencadangan manual dalam format `.json` atau `.txt`.

7. **Antarmuka Tema Gelap (*Dark Mode*)**
   Tata letak UI dirancang menyerupai tema gelap aplikasi web Gemini, lengkap dengan komponen scrollbar khusus dan penyesuaian estetika combobox.

---

## 📁 Struktur Proyek (Clean Architecture)

Arsitektur aplikasi dibagi menjadi 3 lapisan (*layers*) utama untuk memastikan kepatuhan terhadap standar penulisan kode yang rapi (*Clean Code*):

* **Domain Layer**: Berisi logika bisnis utama dan murni seperti `ProjectBundler` yang tidak bergantung pada framework atau eksternal API.
* **Infrastructure Layer**: Berisi gateway eksternal untuk interaksi dengan sistem operasi (`ClipboardService`) dan Google API (`GeminiService`).
* **Presentation Layer**: Mengatur jalannya alur aplikasi desktop, interaksi pengguna, serta elemen UI (`GeminiModernGUI`).

---

## 🛠️ Persyaratan Sistem

* **Python 3.10** ke atas.
* Koneksi internet aktif.
* Kunci API (*API Key*) dari [Google AI Studio](https://aistudio.google.com/).

---

## 🚀 Cara Instalasi & Penggunaan

### 1. Kloning Repositori
```bash
git clone https://github.com/username/nama-repositori.git
cd nama-repositori
```

### 2. Pasang Dependensi
Pasang pustaka yang diperlukan menggunakan pip:
```bash
pip install google-genai pillow
```

### 3. Konfigurasi API Key (Opsional)
Anda dapat menyimpan API Key langsung di dalam *environment variable* sistem operasi agar otomatis terisi saat aplikasi dibuka:

* **Linux/macOS:**
  ```bash
  export GEMINI_API_KEY="kunci_api_anda_disini"
  ```
* **Windows (Command Prompt):**
  ```cmd
  set GEMINI_API_KEY=kunci_api_anda_disini
  ```
* **Windows (PowerShell):**
  ```powershell
  $env:GEMINI_API_KEY="kunci_api_anda_disini"
  ```

### 4. Jalankan Aplikasi
Jalankan berkas utama Python:
```bash
python ai_studio_code.py
```

---

## 📝 Catatan Penggunaan

* **Format Pengiriman Pesan**: Tombol `Enter` digunakan untuk langsung mengirimkan pesan ke AI. Apabila ingin membuat baris baru pada kolom input, gunakan pintasan `Shift + Enter`.
* **Saringan Ekstensi Folder Bundler**: Layanan `ProjectBundler` secara bawaan mengabaikan direktori tertentu seperti `.git`, `node_modules`, `__pycache__`, `.venv` dan berkas biner non-teks untuk menghemat kuota token konteks masukan.

---

## ⚖️ Lisensi
Proyek ini dilisensikan di bawah [MIT License](LICENSE). Anda bebas memodifikasi, mendistribusikan, dan menggunakan kode ini sesuai dengan ketentuan lisensi.
