# Setup sekali klik di Windows

Letakkan `Setup.exe` di folder yang sama dengan `manage.py`, bersama seluruh
kode proyek dan requirements. Klik dua kali installer tersebut.

Yang dilakukan installer:
1. Memastikan Python 64-bit versi 3.10-3.14 tersedia.
2. Membuat `.venv` bila belum ada, lalu memasang dependensi dari internet.
3. Membuat `.env` dan secret key acak unik secara otomatis.
4. Untuk konfigurasi baru, meminta alamat, port, nama database, username, dan
   password database. Password diketik tersembunyi, bukan disimpan di program.
   Pilih tidak untuk menyiapkan website tanpa koneksi analitik dulu.
5. Memeriksa Django dan membuat tabel akun pada SQLite lokal.
6. Menawarkan pembuatan akun admin. Password akun dimasukkan oleh pengguna.

Jika `.env` atau `.venv` sudah ada, installer mempertahankannya. Secret key asli
terus digunakan; konfigurasi yang belum ada dilengkapi. Database warehouse
MariaDB tidak dimigrasi, diimpor, dikosongkan, atau diubah oleh installer.

Setelah selesai, klik `Jalankan Website.bat` dan buka http://localhost:8000/.
Tutup server yang sudah memakai port 8000 sebelum membuka launcher lagi.

## Tentang kerahasiaan

`Setup.exe` bukan file teks sehingga tidak mudah dibaca seperti `.bat` atau
`.py`, tetapi bukan enkripsi dan tetap bisa dianalisis. Tidak ada password
atau secret key bersama di dalam executable. `.env` tetap file teks lokal
karena aplikasi harus membaca kredensialnya. Pengguna yang menguasai komputer
bisa mengaksesnya; jangan mengunggah `.env` ke GitHub atau membagikannya.

Installer ini hanya membantu persiapan, bukan menyembunyikan seluruh kode
website. Python tetap perlu terpasang; executable hanya membungkus launcher.

## Membuat ulang executable

Kode sumber installer ada di `tools/bootstrap.py` dan tidak berisi kredensial.
Dari terminal proyek:

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --onefile --console --clean --name Setup --distpath . --workpath build/setup --specpath build tools/bootstrap.py
```

Gunakan `Setup.bat` sebagai alternatif jika menjalankan dari kode sumber.
Untuk distribusi GitHub, sumber installer dapat dilacak di repository;
`Setup.exe` dapat dibagikan melalui GitHub Releases bersama arsip kode proyek.
Jangan sertakan `.env`, `.venv`, atau database akun saat membagikan proyek.
