"""Installer lokal Windows. Tidak berisi kredensial database."""
import getpass
import json
from pathlib import Path
import shutil
import subprocess
import sys

# Dieksekusi dengan Python .venv setelah dependensi terpasang.
ENV_CODE = r"""
import json,secrets,sys
from pathlib import Path
from dotenv import dotenv_values,set_key
root=Path(sys.argv[1])
path=root/'.env'
new=json.loads(sys.stdin.read() or '{}')
existing=dotenv_values(path) if path.exists() else {}
defaults={'ANALYTICS_ENABLED':'0','ANALYTICS_DB_HOST':'127.0.0.1',
          'ANALYTICS_DB_PORT':'3306','ANALYTICS_DB_NAME':'iak_dw',
          'ANALYTICS_DB_USER':'dashboard_reader','ANALYTICS_DB_PASSWORD':''}
if not path.exists():
    path.write_text('# Konfigurasi lokal. Jangan unggah file ini ke GitHub.\n',encoding='utf-8')
for key,value in {**defaults,**new}.items():
    if key not in existing or existing[key] is None:
        set_key(str(path),key,str(value),quote_mode='always')
key=existing.get('DJANGO_SECRET_KEY')
if not key or key=='replace-with-your-own-long-random-secret-key':
    set_key(str(path),'DJANGO_SECRET_KEY',secrets.token_urlsafe(64),quote_mode='always')
print('File .env siap. Nilai rahasia tidak ditampilkan.')
"""


def project_root():
    if getattr(sys,'frozen',False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def valid_python(command):
    try:
        result=subprocess.run([*command,'-c','import sys; print(sys.version_info.major,sys.version_info.minor)'],capture_output=True,text=True,timeout=15)
        major,minor=map(int,result.stdout.strip().split())
        return result.returncode==0 and major==3 and 10<=minor<=14
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return False


def find_python(root):
    local=root/'.venv/Scripts/python.exe'
    candidates=[]
    if local.exists(): candidates.append([str(local)])
    if not getattr(sys,'frozen',False): candidates.append([sys.executable])
    if shutil.which('py'): candidates.append(['py','-3'])
    for name in ['python','python3']:
        executable=shutil.which(name)
        if executable: candidates.append([executable])
    for command in candidates:
        if valid_python(command): return command
    raise RuntimeError('Python 3.10-3.14 belum ditemukan. Pasang Python 64-bit dari python.org, aktifkan Add Python to PATH, lalu jalankan setup kembali.')


def ask(label,default=''):
    value=input(f'{label}'+(f' [{default}]' if default else '')+': ').strip()
    return value or default


def new_database_config():
    if ask('Hubungkan ke MySQL/MariaDB sekarang? y/n','y').casefold() not in {'y','ya'}:
        return {}
    host=ask('Host database','127.0.0.1')
    while True:
        port=ask('Port database','3306')
        if port.isdigit() and 1<=int(port)<=65535: break
        print('Port harus angka 1-65535.')
    name=ask('Nama database','iak_dw')
    user=ask('Username database','dashboard_reader')
    password=getpass.getpass('Password database (tidak ditampilkan): ')
    return {'ANALYTICS_ENABLED':'1','ANALYTICS_DB_HOST':host,'ANALYTICS_DB_PORT':port,
            'ANALYTICS_DB_NAME':name,'ANALYTICS_DB_USER':user,'ANALYTICS_DB_PASSWORD':password}


def run(command,root,**kwargs):
    subprocess.run(command,cwd=root,check=True,**kwargs)


def install(root):
    required=['manage.py','requirements-analytics.txt','requirements.txt','config/settings.py']
    if not all((root/name).is_file() for name in required):
        raise RuntimeError('Letakkan Setup.exe bersama manage.py dan seluruh folder proyek. Jangan menjalankannya sebagai file tunggal di folder lain.')
    print('\nSETUP ASURANSI ANALYTICS\n')
    print('Setup membuat .venv, mengunduh dependensi, menyiapkan .env, dan membuat tabel login SQLite.')
    print('Data warehouse tidak diimpor atau diubah. Koneksi internet diperlukan untuk dependensi.')
    input('Tekan Enter untuk mulai, atau tutup jendela untuk batal... ')
    python=find_python(root)
    venv=root/'.venv'
    venv_python=venv/'Scripts/python.exe'
    if venv.exists():
        if not venv_python.is_file() or not valid_python([str(venv_python)]):
            raise RuntimeError('Folder .venv sudah ada tetapi tidak valid. Pindahkan folder itu terlebih dahulu, lalu ulangi setup. Setup tidak menghapusnya otomatis.')
        print('\n[1/4] Memakai virtual environment yang sudah ada.')
    else:
        print('\n[1/4] Membuat virtual environment...')
        run([*python,'-m','venv',str(venv)],root)
    print('\n[2/4] Memasang dependensi proyek...')
    run([str(venv_python),'-m','pip','install','-r','requirements-analytics.txt'],root)
    print('\n[3/4] Menyiapkan .env dan secret key...')
    if (root/'.env').exists():
        print('Konfigurasi .env yang ada dipertahankan; hanya kolom yang belum ada akan dilengkapi.')
        config={}
    else:
        config=new_database_config()
    run([str(venv_python),'-c',ENV_CODE,str(root)],root,input=json.dumps(config),text=True)
    config.clear()
    print('\n[4/4] Memeriksa Django dan menyiapkan database akun...')
    run([str(venv_python),'manage.py','check'],root)
    run([str(venv_python),'manage.py','migrate','--database=default'],root)
    print('\nSETUP SELESAI. Secret key tidak perlu diketik manual.')
    if ask('Buat akun admin sekarang? y/n','n').casefold() in {'y','ya'}:
        run([str(venv_python),'manage.py','createsuperuser'],root)
    print('Untuk membuka website, klik dua kali Jalankan Website.bat.')
    print('Konfigurasi database ada di .env. Simpan file tersebut secara pribadi.')


def main():
    # Restore normal DLL lookup before launching an external Python on Windows.
    # https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html
    if getattr(sys,'frozen',False) and sys.platform=='win32':
        import ctypes
        import os
        ctypes.windll.kernel32.SetDllDirectoryW(None)
        bundle=str(Path(sys._MEIPASS).resolve()).casefold()
        os.environ['PATH']=os.pathsep.join(part for part in os.environ.get('PATH','').split(os.pathsep) if not str(Path(part or '.').resolve()).casefold().startswith(bundle))
    root=project_root()
    if '--check-launcher' in sys.argv:
        python=find_python(root)
        print(json.dumps({'launcher_ok':True,'frozen':bool(getattr(sys,'frozen',False)),
                          'project_ok':(root/'manage.py').is_file(),'python_ok':bool(python)}))
        return 0
    try:
        install(root)
    except (KeyboardInterrupt,EOFError):
        print('\nSetup dibatalkan. File yang sudah ada tidak dihapus.')
        return 1
    except (OSError,RuntimeError,subprocess.CalledProcessError) as error:
        if isinstance(error,subprocess.CalledProcessError):
            print('\nSalah satu tahap setup gagal. Lihat pesan proses di atas dan jalankan setup kembali.')
        else:
            print(f'\nSetup belum selesai: {error}')
        return 1
    finally:
        try: input('\nTekan Enter untuk menutup... ')
        except (EOFError,KeyboardInterrupt): pass
    return 0


if __name__=='__main__':
    raise SystemExit(main())
