import os
import customtkinter as ctk
import subprocess
import ctypes
import requests
import tempfile
import shutil
import json
import threading
from pathlib import Path
import sys
import base64
import logging
from itertools import cycle

dotnet_index_url = "https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/releases-index.json"
versions = ["5", "6", "7", "8", "9", "10"]

silent_var = None
runtime_display_frame = None
runtime_labels = {}
progress = None
status_label = None
animation_label = None
loading_images = []
loading_index = 0
scale = 1.0
window = None
bottom_frame = None

logging.basicConfig(filename="runtime_installer.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_error(message):
    logging.error(message)

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def load_base64_file(path):
    with open(resource_path(path), "r", encoding="utf-8") as f:
        return f.read()

winrar_base64 = load_base64_file("winrar_base64.txt")
forticlient_base64 = load_base64_file("forticlient_base64.txt")
vnc_base64 = load_base64_file("vnc_base64.txt")      # <-- TightVNC
office_base64 = load_base64_file("office_base64.txt")  # <-- Microsoft Office

def get_scale():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        pass
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    screen_width = user32.GetSystemMetrics(0)
    if screen_width >= 7680:
        return 1.5
    elif screen_width >= 3840:
        return 1.3
    elif screen_width >= 2560:
        return 1.1
    else:
        return 0.6

def get_installed_versions():
    installed = {"x64": [], "x86": []}
    paths = {
        "x64": r"C:\\Program Files\\dotnet\\shared\\Microsoft.NETCore.App",
        "x86": r"C:\\Program Files (x86)\\dotnet\\shared\\Microsoft.NETCore.App"
    }
    for arch, path in paths.items():
        if os.path.exists(path):
            installed[arch] = os.listdir(path)
    return installed

def fetch_latest_runtime(version, arch):
    try:
        index = requests.get(dotnet_index_url, verify=False).json()
        version_info = next((v for v in index["releases-index"] if v["channel-version"].startswith(version)), None)
        if not version_info:
            raise Exception(f"{version} için metadata bulunamadı.")
        release_url = version_info["releases.json"]
        response = requests.get(release_url, verify=False)
        if response.status_code != 200 or not response.text.strip().startswith("{"):
            raise Exception(f"{version} için geçerli JSON alınamadı.")
        releases = response.json()
        latest = releases["releases"][0]
        runtime_version = latest["runtime"]["version"]
        for f in latest["runtime"]["files"]:
            if f["rid"] == f"win-{arch}" and f["name"].endswith(".exe"):
                return runtime_version, f["url"]
        raise Exception("İndirilebilir exe bulunamadı.")
    except Exception as e:
        log_error(f"fetch_latest_runtime hatası: {e}")
        raise Exception(f"Sürüm alınamadı: {e}")

def refresh_runtimes():
    global runtime_labels
    installed = get_installed_versions()
    for arch in ["x64", "x86"]:
        for widget in runtime_display_frame[arch].winfo_children():
            widget.destroy()
        runtime_labels[arch] = []
        ctk.CTkLabel(runtime_display_frame[arch], text=f"[{arch}]", font=("Segoe UI", int(12 * scale), "italic"), text_color="#00d4ff", anchor="w", justify="left").pack(anchor="w")
        for ver in installed[arch]:
            ver_clean = ver.rstrip(".0") if ver.endswith(".0") else ver
            lbl = ctk.CTkLabel(runtime_display_frame[arch], text=f"•  {ver_clean}", text_color="#00ff88", font=("Courier New", int(10.5 * scale)), anchor="w", justify="left")
            lbl.pack(anchor="w", padx=5)
            runtime_labels[arch].append(lbl)

def threaded_install(version, arch):
    threading.Thread(target=download_and_install, args=(version, arch), daemon=True).start()

spinner_cycle = cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])

def update_animation():
    global animation_label
    try:
        animation_label.configure(text=next(spinner_cycle))
        window.after(100, update_animation)
    except Exception as e:
        log_error(f"Animasyon güncelleme hatası: {e}")

def download_and_install(version, arch):
    global status_label
    try:
        status_label.configure(text=f"Sürüm kontrol ediliyor...")
        window.update()
        runtime_version, url = fetch_latest_runtime(version + ".0", arch)
        status_label.configure(text=f".NET {version} ({arch}) indiriliyor...")
        temp_dir = tempfile.mkdtemp()
        filename = os.path.join(temp_dir, f"{runtime_version}-{arch}.exe")
        r = requests.get(url, stream=True, verify=False)
        content_length = int(r.headers.get("Content-Length", 0))
        if r.status_code != 200 or content_length < 10_000_000:
            raise Exception("Geçersiz veya eksik dosya indirildi.")
        downloaded = 0
        chunk_size = 8192
        progress.set(0)
        progress.pack(pady=(5, 10))
        update_animation()
        window.update()
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = (downloaded / content_length)
                    progress.set(min(percent, 1.0))
                    status_label.configure(text=f".NET {version} ({arch}) indiriliyor... %{int(percent * 100)}")
                    window.update()
        status_label.configure(text="Kurulum başlatılıyor...")
        window.update()
        silent = silent_var.get()
        if silent:
            subprocess.run([filename, "/install", "/quiet", "/norestart"])
        else:
            subprocess.run([filename])
        status_label.configure(text=f".NET {version} ({arch}) kurulumu tamamlandı.")
        refresh_runtimes()
    except Exception as e:
        status_label.configure(text=f"Hata: {str(e)}")
        log_error(f"Kurulum hatası ({version} {arch}): {e}")
    finally:
        progress.pack_forget()
        window.update()
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                log_error(f"Temp klasörü silinemedi: {e}")

def install_embedded_program(name, base64_data, filetype="exe"):
    try:
        status_label.configure(text=f"{name} yükleniyor...")
        window.update()
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, f"{name}.{filetype}")
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(base64_data.encode()))
        silent = silent_var.get()
        if filetype == "msi":
            cmd = ["msiexec", "/i", file_path]
            if silent:
                cmd += ["/quiet", "/norestart"]
            subprocess.run(cmd)
        else:
            if silent:
                subprocess.run([file_path, "/S"])
            else:
                subprocess.run([file_path])
        status_label.configure(text=f"{name} kurulumu tamamlandı.")
    except Exception as e:
        status_label.configure(text=f"Hata: {str(e)}")
        log_error(f"{name} kurulumu hatası: {e}")
    finally:
        window.update()
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            log_error(f"{name} temp klasörü silinemedi: {e}")

cpp_silent_params = {
    "2005": ["/q", "/norestart"],
    "2008": ["/q", "/norestart"],
    "2010": ["/q", "/norestart"],
    "2012": ["/quiet", "/norestart"],
    "2013": ["/quiet", "/norestart"],
    "2015-2022": ["/quiet", "/norestart"],
}

def get_cpp_params(title, silent):
    version = title.split(" ")[0]
    if "2015-2022" in title:
        version = "2015-2022"
    if not silent:
        return []
    return cpp_silent_params.get(version, ["/quiet", "/norestart"])

def install_online_program(name, url, extra_params=None):
    try:
        status_label.configure(text=f"{name} indiriliyor...")
        window.update()
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, f"{name}.exe")
        r = requests.get(url, stream=True, verify=False)
        if r.status_code != 200:
            raise Exception("Dosya indirilemedi.")
        with open(file_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)
        silent = silent_var.get()
        cmd = [file_path]
        if extra_params is not None:
            if silent:
                cmd += extra_params
        elif silent:
            cmd += ["/quiet", "/norestart"]
        subprocess.run(cmd)
        status_label.configure(text=f"{name} kurulumu tamamlandı.")
    except Exception as e:
        status_label.configure(text=f"Hata: {str(e)}")
        log_error(f"{name} online kurulum hatası: {e}")
    finally:
        window.update()
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            log_error(f"{name} temp klasörü silinemedi: {e}")

def gui_main():
    global silent_var, runtime_display_frame, progress, window, status_label, animation_label, loading_images, scale, bottom_frame
    scale = get_scale()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    window = ctk.CTk()
    window.title("Yorglass")  # Burada başlık değiştirildi
    try:
        window.iconbitmap("yorglass.ico")  # PNG'yi .ico'ya dönüştürüp klasörüne ekle! TAMAM EKLEDİM :)
    except Exception as e:
        pass  # Simgede hata olursa program yine de çalışsın
    window.geometry("950x650")
    window.minsize(800, 500)
    window.resizable(True, True)
    notebook = ctk.CTkTabview(window)
    notebook.pack(padx=10, pady=(5,0), fill="both", expand=True)

    homepage_tab = notebook.add("🏠 Anasayfa")
    runtime_tab = notebook.add("⚙️ .NET Runtime")
    cpp_tab = notebook.add("📦 C++ Runtime")
    programs_tab = notebook.add("🧰 Programlar")

    ctk.CTkLabel(homepage_tab, text="Hoş geldiniz!", font=("Segoe UI", int(22 * scale), "bold"), text_color="#00d4ff").pack(pady=20)
    ctk.CTkLabel(homepage_tab, text="Bu araç ile .NET Runtime, Visual C++ Runtime ve popüler bazı yazılımları kolayca yükleyebilirsiniz.", wraplength=800, justify="center", font=("Segoe UI", int(14 * scale))).pack(pady=10)

    ctk.CTkLabel(runtime_tab, text="Kurulu Sürümler:", font=("Segoe UI", int(16 * scale), "bold"), text_color="#00ffff").pack(pady=(10, 0))
    container_outer = ctk.CTkFrame(runtime_tab, fg_color="#222222", corner_radius=8)
    container_outer.pack(pady=5)
    container = ctk.CTkFrame(container_outer, fg_color="transparent")
    container.pack(padx=10, pady=10)
    runtime_display_frame = {
        "x64": ctk.CTkFrame(container, fg_color="transparent"),
        "x86": ctk.CTkFrame(container, fg_color="transparent")
    }
    runtime_display_frame["x64"].pack(side="left", padx=20)
    runtime_display_frame["x86"].pack(side="right", padx=20)
    ctk.CTkButton(runtime_tab, text="Kurulu Sürümleri Yenile", command=refresh_runtimes).pack(pady=5)
    refresh_runtimes()
    ctk.CTkLabel(runtime_tab, text="Kurmak istediğiniz sürüm ve mimariyi seçin:", font=("Segoe UI", int(13 * scale))).pack(pady=5)
    grid_frame = ctk.CTkFrame(runtime_tab, fg_color="transparent")
    grid_frame.pack()
    for i, version in enumerate(versions):
        for j, arch in enumerate(["x64", "x86"]):
            btn = ctk.CTkButton(grid_frame, text=f".NET {version} {arch} Kur", width=int(800 * 0.4), corner_radius=10,
                                hover_color="#4c82e0", border_width=1, border_color="#0066ff",
                                font=("Segoe UI", int(10 * scale)),
                                command=lambda v=version, a=arch: threaded_install(v, a))
            btn.grid(row=i, column=j, padx=int(8 * scale), pady=int(4 * scale), sticky="ew")
    grid_frame.grid_columnconfigure(0, weight=1, uniform="group1")
    grid_frame.grid_columnconfigure(1, weight=1, uniform="group1")

    ctk.CTkLabel(cpp_tab, text="Visual C++ Redistributable Kurulumu", font=("Segoe UI", int(18 * scale), "bold"), text_color="#ffd700").pack(pady=12)
    ctk.CTkLabel(cpp_tab, text="Aşağıdaki Visual C++ paketlerinden istediğinizi yüklemek için ilgili butona tıklayın.", font=("Segoe UI", int(13 * scale))).pack(pady=(0, 8))
    cpp_versions = [
        ("2005 (x86)", "https://download.microsoft.com/download/8/b/4/8b42259f-5d70-43f4-ac2e-4b208fd8d66a/vcredist_x86.EXE"),
        ("2005 (x64)", "https://download.microsoft.com/download/8/b/4/8b42259f-5d70-43f4-ac2e-4b208fd8d66a/vcredist_x64.EXE"),
        ("2008 (x86)", "https://download.microsoft.com/download/5/D/8/5D8C65CB-C849-4025-8E95-C3966CAFD8AE/vcredist_x86.exe"),
        ("2008 (x64)", "https://download.microsoft.com/download/5/D/8/5D8C65CB-C849-4025-8E95-C3966CAFD8AE/vcredist_x64.exe"),
        ("2010 (x86)", "https://download.microsoft.com/download/1/6/5/165255E7-1014-4D0A-B094-B6A430A6BFFC/vcredist_x86.exe"),
        ("2010 (x64)", "https://download.microsoft.com/download/1/6/5/165255E7-1014-4D0A-B094-B6A430A6BFFC/vcredist_x64.exe"),
        ("2012 (x86)", "https://download.microsoft.com/download/1/6/B/16B06F60-3B20-4FF2-B699-5E9B7962F9AE/VSU_4/vcredist_x86.exe"),
        ("2012 (x64)", "https://download.microsoft.com/download/1/6/B/16B06F60-3B20-4FF2-B699-5E9B7962F9AE/VSU_4/vcredist_x64.exe"),
        ("2013 (x86)", "https://aka.ms/highdpimfc2013x86enu"),
        ("2013 (x64)", "https://aka.ms/highdpimfc2013x64enu"),
        ("2015-2022 (x86)", "https://aka.ms/vs/17/release/vc_redist.x86.exe"),
        ("2015-2022 (x64)", "https://aka.ms/vs/17/release/vc_redist.x64.exe"),
    ]
    cpp_grid = ctk.CTkFrame(cpp_tab, fg_color="transparent")
    cpp_grid.pack(pady=5)
    for idx, (title, url) in enumerate(cpp_versions):
        btn = ctk.CTkButton(
            cpp_grid,
            text=f"VC++ {title} Kur",
            width=int(340 * scale),
            corner_radius=8,
            hover_color="#ffbd59",
            border_width=1,
            border_color="#d9a406",
            font=("Segoe UI", int(10 * scale)),
            command=lambda n=title, u=url: threading.Thread(
                target=install_online_program,
                args=(f"VC++ {n}", u, get_cpp_params(n, silent_var.get())),
                daemon=True
            ).start()
        )
        btn.grid(row=idx // 2, column=idx % 2, padx=8, pady=5, sticky="ew")
    cpp_grid.grid_columnconfigure(0, weight=1, uniform="cppgroup")
    cpp_grid.grid_columnconfigure(1, weight=1, uniform="cppgroup")

    ctk.CTkLabel(programs_tab, text="Popüler Yazılımlar:", font=("Segoe UI", int(17 * scale), "bold")).pack(pady=10)
    programs = [
        ("WinRAR", lambda: threading.Thread(target=install_embedded_program, args=("WinRAR", winrar_base64, "exe"), daemon=True).start()),
        ("FortiClientVPN", lambda: threading.Thread(target=install_embedded_program, args=("FortiClientVPN", forticlient_base64, "exe"), daemon=True).start()),
        ("Google Chrome", lambda: threading.Thread(target=install_online_program, args=("Google Chrome", "https://dl.google.com/chrome/install/latest/chrome_installer.exe", None), daemon=True).start()),
        ("TightVNC", lambda: threading.Thread(target=install_embedded_program, args=("TightVNC", vnc_base64, "msi"), daemon=True).start()),
        ("Microsoft Office", lambda: threading.Thread(target=install_embedded_program, args=("Office", office_base64, "exe"), daemon=True).start()),
    ]
    grid = ctk.CTkFrame(programs_tab, fg_color="transparent")
    grid.pack(pady=10)
    for i, (name, action) in enumerate(programs):
        card = ctk.CTkFrame(grid, fg_color="#1f1f1f", corner_radius=12)
        card.grid(row=i//2, column=i%2, padx=14, pady=10, sticky="nsew")
        ctk.CTkLabel(card, text=f"{name}", font=("Segoe UI", int(13 * scale), "bold"), text_color="#00d4ff").pack(pady=(12, 4))
        ctk.CTkButton(card, text="Kur", width=120, height=32, command=action).pack(pady=(0, 14))
    grid.grid_columnconfigure(0, weight=1)
    grid.grid_columnconfigure(1, weight=1)

    bottom_frame = ctk.CTkFrame(window, height=60, fg_color="#1f1f1f")
    bottom_frame.pack(fill="x")
    silent_var = ctk.BooleanVar(value=True)
    ctk.CTkCheckBox(bottom_frame, text="Sessiz Kurulum (Silent Install)", variable=silent_var, font=("Segoe UI", int(11 * scale))).pack(side="left", padx=12, pady=10)
    status_label = ctk.CTkLabel(bottom_frame, text="", text_color="#00ffff", font=("Segoe UI", int(12 * scale)))
    status_label.pack(side="left", padx=12)
    progress = ctk.CTkProgressBar(bottom_frame, width=240)
    progress.set(0)
    progress.pack(side="right", padx=12)
    animation_label = ctk.CTkLabel(bottom_frame, text="")
    animation_label.pack(side="right", padx=12)
    window.mainloop()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    if is_admin():
        gui_main()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
