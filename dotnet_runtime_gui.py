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
from PIL import Image
from datetime import datetime

# --- Tooltip (İpucu) Sınıfı ---
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self):
        if self.tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        self.tip_window = ctk.CTkToplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        
        label = ctk.CTkLabel(self.tip_window, text=self.text, justify='left',
                             fg_color="#1c1c1c", corner_radius=6,
                             text_color="white", padx=10, pady=5,
                             font=("Segoe UI", 12))
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

# --- Global Değişkenler ---
dotnet_index_url = "https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/releases-index.json"
versions = ["5", "6", "7", "8", "9", "10"]

silent_var = None
runtime_display_frame = None
runtime_labels = {}
progress = None
status_label = None
animation_label = None
scale = 1.0
window = None
log_textbox = None

logging.basicConfig(filename="runtime_installer.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def log_message(message, level="info"):
    if not log_textbox: return
    timestamp = datetime.now().strftime("%H:%M:%S")
    full_message = f"[{timestamp}] {message}\n"
    color_map = {"info": ("#00ffff", "INFO"), "success": ("#00ff88", "SUCCESS"), "error": ("#ff4d4d", "ERROR"), "warning": ("#ffd700", "WARN")}
    text_color, tag = color_map.get(level, ("white", "LOG"))
    log_textbox.tag_config(tag, foreground=text_color)
    log_textbox.configure(state="normal")
    log_textbox.insert("end", full_message, tag)
    log_textbox.configure(state="disabled")
    log_textbox.see("end")
    status_label.configure(text=message, text_color=text_color)
    if window: window.update_idletasks()

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
vnc_base64 = load_base64_file("vnc_base64.txt")
office_base64 = load_base64_file("office_base64.txt")

def get_scale():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except: pass
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    screen_width = user32.GetSystemMetrics(0)
    # DÜZELTME: Ölçeklendirme değeri biraz düşürüldü.
    return 1.2 if screen_width >= 3840 else 1.0 if screen_width >= 2560 else 0.6

def get_installed_versions():
    installed = {"x64": [], "x86": []}
    paths = {"x64": r"C:\\Program Files\\dotnet\\shared\\Microsoft.NETCore.App", "x86": r"C:\\Program Files (x86)\\dotnet\\shared\\Microsoft.NETCore.App"}
    for arch, path in paths.items():
        if os.path.exists(path):
            installed[arch] = os.listdir(path)
    return installed

def fetch_latest_runtime(version, arch):
    try:
        index = requests.get(dotnet_index_url, verify=False).json()
        version_info = next((v for v in index["releases-index"] if v["channel-version"].startswith(version)), None)
        if not version_info: raise Exception(f"{version} için metadata bulunamadı.")
        release_url = version_info["releases.json"]
        releases = requests.get(release_url, verify=False).json()
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
    log_message("Kurulu .NET sürümleri yenileniyor...")
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
    log_message("Yenileme tamamlandı.", "success")

def threaded_install(version, arch):
    threading.Thread(target=download_and_install, args=(version, arch), daemon=True).start()

spinner_cycle = cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])
is_animating = False

def update_animation():
    global animation_label, is_animating
    if not is_animating:
        animation_label.configure(text="")
        return
    try:
        animation_label.configure(text=next(spinner_cycle))
        window.after(100, update_animation)
    except: pass

def download_and_install(version, arch):
    global is_animating
    temp_dir = None
    try:
        is_animating = True
        update_animation()
        log_message(f".NET {version} ({arch}) için sürüm kontrol ediliyor...")
        runtime_version, url = fetch_latest_runtime(version + ".0", arch)
        log_message(f"En son sürüm bulundu: {runtime_version}")
        log_message(f".NET {version} ({arch}) indiriliyor...")
        temp_dir = tempfile.mkdtemp()
        filename = os.path.join(temp_dir, f"{runtime_version}-{arch}.exe")
        r = requests.get(url, stream=True, verify=False)
        content_length = int(r.headers.get("Content-Length", 0))
        if r.status_code != 200 or content_length < 10_000_000: raise Exception("Geçersiz veya eksik dosya indirildi.")
        downloaded = 0
        chunk_size = 8192
        progress.set(0)
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    percent = (downloaded / content_length)
                    progress.set(min(percent, 1.0))
                    status_label.configure(text=f".NET {version} ({arch}) indiriliyor... %{int(percent * 100)}")
                    window.update_idletasks()
        log_message("İndirme tamamlandı. Kurulum başlatılıyor...")
        silent = silent_var.get()
        if silent: subprocess.run([filename, "/install", "/quiet", "/norestart"])
        else: subprocess.run([filename])
        log_message(f".NET {version} ({arch}) kurulumu başarıyla tamamlandı.", "success")
        refresh_runtimes()
    except Exception as e:
        log_message(f"Hata: {str(e)}", "error")
        log_error(f"Kurulum hatası ({version} {arch}): {e}")
    finally:
        is_animating = False
        progress.set(0)
        if temp_dir and os.path.exists(temp_dir):
            try: shutil.rmtree(temp_dir)
            except Exception as e: log_error(f"Temp klasörü silinemedi: {e}")

def run_threaded_install(func, *args):
    threading.Thread(target=func, args=args, daemon=True).start()

def install_embedded_program(name, base64_data, filetype="exe"):
    temp_dir = None
    try:
        log_message(f"{name} kurulumu hazırlanıyor...")
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, f"{name}.{filetype}")
        with open(file_path, "wb") as f: f.write(base64.b64decode(base64_data.encode()))
        log_message(f"{name} kurulumu başlatılıyor...")
        silent = silent_var.get()
        if filetype == "msi":
            cmd = ["msiexec", "/i", file_path]
            if silent: cmd += ["/quiet", "/norestart"]
            subprocess.run(cmd)
        else:
            if silent: subprocess.run([file_path, "/S"])
            else: subprocess.run([file_path])
        log_message(f"{name} kurulumu tamamlandı.", "success")
    except Exception as e:
        log_message(f"Hata: {str(e)}", "error")
        log_error(f"{name} kurulumu hatası: {e}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try: shutil.rmtree(temp_dir)
            except Exception as e: log_error(f"{name} temp klasörü silinemedi: {e}")

cpp_silent_params = {"2005": ["/q"], "2008": ["/q"], "2010": ["/q"], "2012": ["/quiet", "/norestart"], "2013": ["/quiet", "/norestart"], "2015-2022": ["/quiet", "/norestart"]}

def get_cpp_params(title, silent):
    version = "2015-2022" if "2015-2022" in title else title.split(" ")[0]
    return cpp_silent_params.get(version, ["/quiet", "/norestart"]) if silent else []

def install_online_program(name, url, extra_params=None):
    temp_dir = None
    try:
        log_message(f"{name} indiriliyor...")
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, f"{name}.exe")
        r = requests.get(url, stream=True, verify=False)
        if r.status_code != 200: raise Exception("Dosya indirilemedi.")
        with open(file_path, "wb") as f: shutil.copyfileobj(r.raw, f)
        log_message(f"{name} indirme tamamlandı. Kurulum başlatılıyor...")
        silent = silent_var.get()
        cmd = [file_path]
        if extra_params is not None:
            if silent: cmd += extra_params
        elif silent: cmd += ["/quiet", "/norestart"]
        subprocess.run(cmd)
        log_message(f"{name} kurulumu tamamlandı.", "success")
    except Exception as e:
        log_message(f"Hata: {str(e)}", "error")
        log_error(f"{name} online kurulum hatası: {e}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try: shutil.rmtree(temp_dir)
            except Exception as e: log_error(f"{name} temp klasörü silinemedi: {e}")

def gui_main():
    global silent_var, runtime_display_frame, progress, window, status_label, animation_label, scale, log_textbox
    scale = get_scale()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    window = ctk.CTk()
    window.title("Yorglass Kurulum Yardımcısı")
    try:
        window.iconbitmap(resource_path("yorglass.ico"))
    except Exception as e: log_error(f"İkon yüklenemedi: {e}")
    window.geometry("950x700")
    window.minsize(800, 600)
    window.resizable(True, True)
    
    window.grid_rowconfigure(0, weight=1)
    window.grid_columnconfigure(0, weight=1)

    notebook = ctk.CTkTabview(window)
    notebook.grid(row=0, column=0, padx=10, pady=(5,0), sticky="nsew")

    # Sekmeleri oluştur
    homepage_tab = notebook.add("🏠 Anasayfa")
    runtime_tab = notebook.add("⚙️ .NET Runtime")
    cpp_tab = notebook.add("📦 C++ Runtime")
    programs_tab = notebook.add("🧰 Programlar")

    # --- DÜZELTME: Her sekme için kaydırılabilir çerçeve oluştur ---

    # --- Anasayfa Sekmesi ---
    home_scroll_frame = ctk.CTkScrollableFrame(homepage_tab, fg_color="transparent")
    home_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
    ctk.CTkLabel(home_scroll_frame, text="Hoş geldiniz!", font=("Segoe UI", int(22 * scale), "bold"), text_color="#00d4ff").pack(pady=20)
    ctk.CTkLabel(home_scroll_frame, text="Bu araç ile .NET Runtime, Visual C++ Runtime ve popüler bazı yazılımları kolayca yükleyebilirsiniz.", wraplength=700, justify="center", font=("Segoe UI", int(14 * scale))).pack(pady=10)
    
    # --- .NET Runtime Sekmesi ---
    runtime_scroll_frame = ctk.CTkScrollableFrame(runtime_tab, fg_color="transparent")
    runtime_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    ctk.CTkLabel(runtime_scroll_frame, text="Kurulu Sürümler:", font=("Segoe UI", int(16 * scale), "bold"), text_color="#00ffff").pack(pady=(10, 0))
    container_outer = ctk.CTkFrame(runtime_scroll_frame, fg_color="#222222", corner_radius=8)
    container_outer.pack(pady=5)
    container = ctk.CTkFrame(container_outer, fg_color="transparent")
    container.pack(padx=10, pady=10)
    runtime_display_frame = {"x64": ctk.CTkFrame(container, fg_color="transparent"), "x86": ctk.CTkFrame(container, fg_color="transparent")}
    runtime_display_frame["x64"].pack(side="left", padx=20); runtime_display_frame["x86"].pack(side="right", padx=20)
    refresh_btn = ctk.CTkButton(runtime_scroll_frame, text="Kurulu Sürümleri Yenile", command=refresh_runtimes)
    refresh_btn.pack(pady=5)
    Tooltip(refresh_btn, "Sistemde kurulu olan .NET sürümlerini yeniden tarar ve listeyi günceller.")
    
    ctk.CTkLabel(runtime_scroll_frame, text="Kurmak istediğiniz sürüm ve mimariyi seçin:", font=("Segoe UI", int(13 * scale))).pack(pady=(5,10))
    grid_frame = ctk.CTkFrame(runtime_scroll_frame, fg_color="transparent")
    grid_frame.pack(fill="x", expand=True)
    for i, version in enumerate(versions):
        for j, arch in enumerate(["x64", "x86"]):
            btn = ctk.CTkButton(grid_frame, text=f".NET {version} {arch} Kur", corner_radius=10, hover_color="#4c82e0", border_width=1, border_color="#0066ff", font=("Segoe UI", int(10 * scale)), command=lambda v=version, a=arch: threaded_install(v, a))
            btn.grid(row=i, column=j, padx=int(8 * scale), pady=int(4 * scale), sticky="ew")
    grid_frame.grid_columnconfigure(0, weight=1, uniform="group1"); grid_frame.grid_columnconfigure(1, weight=1, uniform="group1")

    # --- C++ Runtime Sekmesi ---
    cpp_scroll_frame = ctk.CTkScrollableFrame(cpp_tab, fg_color="transparent")
    cpp_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
    ctk.CTkLabel(cpp_scroll_frame, text="Visual C++ Redistributable Kurulumu", font=("Segoe UI", int(18 * scale), "bold"), text_color="#ffd700").pack(pady=12)
    ctk.CTkLabel(cpp_scroll_frame, text="Aşağıdaki Visual C++ paketlerinden istediğinizi yüklemek için ilgili butona tıklayın.", font=("Segoe UI", int(13 * scale))).pack(pady=(0, 8))
    
    cpp_versions = [
        ("2005 (x86)", "https://download.microsoft.com/download/8/b/4/8b42259f-5d70-43f4-ac2e-4b208fd8d66a/vcredist_x86.EXE", "32-bit uygulamalar için temel C++ kütüphanesi."),
        ("2005 (x64)", "https://download.microsoft.com/download/8/b/4/8b42259f-5d70-43f4-ac2e-4b208fd8d66a/vcredist_x64.EXE", "64-bit uygulamalar için temel C++ kütüphanesi."),
        ("2008 (x86)", "https://download.microsoft.com/download/5/D/8/5D8C65CB-C849-4025-8E95-C3966CAFD8AE/vcredist_x86.exe", "Visual Studio 2008 ile geliştirilen 32-bit programlar için."),
        ("2008 (x64)", "https://download.microsoft.com/download/5/D/8/5D8C65CB-C849-4025-8E95-C3966CAFD8AE/vcredist_x64.exe", "Visual Studio 2008 ile geliştirilen 64-bit programlar için."),
        ("2010 (x86)", "https://download.microsoft.com/download/1/6/5/165255E7-1014-4D0A-B094-B6A430A6BFFC/vcredist_x86.exe", "Visual Studio 2010 ile geliştirilen 32-bit programlar için."),
        ("2010 (x64)", "https://download.microsoft.com/download/1/6/5/165255E7-1014-4D0A-B094-B6A430A6BFFC/vcredist_x64.exe", "Visual Studio 2010 ile geliştirilen 64-bit programlar için."),
        ("2012 (x86)", "https://download.microsoft.com/download/1/6/B/16B06F60-3B20-4FF2-B699-5E9B7962F9AE/VSU_4/vcredist_x86.exe", "Visual Studio 2012 ile geliştirilen 32-bit programlar için."),
        ("2012 (x64)", "https://download.microsoft.com/download/1/6/B/16B06F60-3B20-4FF2-B699-5E9B7962F9AE/VSU_4/vcredist_x64.exe", "Visual Studio 2012 ile geliştirilen 64-bit programlar için."),
        ("2013 (x86)", "https://aka.ms/highdpimfc2013x86enu", "Visual Studio 2013 ile geliştirilen 32-bit programlar için."),
        ("2013 (x64)", "https://aka.ms/highdpimfc2013x64enu", "Visual Studio 2013 ile geliştirilen 64-bit programlar için."),
        ("2015-2022 (x86)", "https://aka.ms/vs/17/release/vc_redist.x86.exe", "2015-2022 sürümlerini içeren kümülatif paket (32-bit)."),
        ("2015-2022 (x64)", "https://aka.ms/vs/17/release/vc_redist.x64.exe", "2015-2022 sürümlerini içeren kümülatif paket (64-bit)."),
    ]
    cpp_grid = ctk.CTkFrame(cpp_scroll_frame, fg_color="transparent")
    cpp_grid.pack(pady=5, fill="x", expand=True)
    for idx, (title, url, tooltip_text) in enumerate(cpp_versions):
        btn = ctk.CTkButton(cpp_grid, text=f"VC++ {title} Kur", corner_radius=8, hover_color="#ffbd59", border_width=1, border_color="#d9a406", font=("Segoe UI", int(10 * scale)), command=lambda n=title, u=url: run_threaded_install(install_online_program, f"VC++ {n}", u, get_cpp_params(n, silent_var.get())))
        btn.grid(row=idx // 2, column=idx % 2, padx=8, pady=5, sticky="ew")
        Tooltip(btn, tooltip_text)
    cpp_grid.grid_columnconfigure(0, weight=1, uniform="cppgroup"); cpp_grid.grid_columnconfigure(1, weight=1, uniform="cppgroup")

    # --- Programlar Sekmesi ---
    programs_scroll_frame = ctk.CTkScrollableFrame(programs_tab, fg_color="transparent")
    programs_scroll_frame.pack(fill="both", expand=True, padx=10, pady=5)
    ctk.CTkLabel(programs_scroll_frame, text="Popüler Yazılımlar:", font=("Segoe UI", int(17 * scale), "bold")).pack(pady=10)
    program_icons = {"WinRAR": "winrar_base64.png", "FortiClientVPN": "forticlient_base64.png", "Google Chrome": "chrome_icon.png", "TightVNC": "tightvnc_icon_resized.png", "Microsoft Office": "office_base64.png"}
    programs = [("WinRAR", lambda: run_threaded_install(install_embedded_program, "WinRAR", winrar_base64, "exe")), ("FortiClientVPN", lambda: run_threaded_install(install_embedded_program, "FortiClientVPN", forticlient_base64, "exe")), ("Google Chrome", lambda: run_threaded_install(install_online_program, "Google Chrome", "https://dl.google.com/chrome/install/latest/chrome_installer.exe", None)), ("TightVNC", lambda: run_threaded_install(install_embedded_program, "TightVNC", vnc_base64, "msi")), ("Microsoft Office", lambda: run_threaded_install(install_embedded_program, "Office", office_base64, "exe"))]
    grid = ctk.CTkFrame(programs_scroll_frame, fg_color="transparent")
    grid.pack(pady=10, fill="x", expand=True)
    for i, (name, action) in enumerate(programs):
        card = ctk.CTkFrame(grid, fg_color="#1f1f1f", corner_radius=12)
        card.grid(row=i//2, column=i%2, padx=14, pady=10, sticky="nsew")
        icon_filename = program_icons.get(name)
        if icon_filename:
            try:
                icon_path = resource_path(icon_filename)
                if os.path.exists(icon_path):
                    img = ctk.CTkImage(Image.open(icon_path), size=(48, 48))
                    ctk.CTkLabel(card, image=img, text="").pack(pady=(12, 4))
            except Exception as e: log_error(f"İkon yüklenemedi {icon_filename}: {e}")
        ctk.CTkLabel(card, text=f"{name}", font=("Segoe UI", int(13 * scale), "bold"), text_color="#00d4ff").pack(pady=(4, 8))
        ctk.CTkButton(card, text="Kur", width=120, height=32, command=action).pack(pady=(0, 14))
    grid.grid_columnconfigure(0, weight=1); grid.grid_columnconfigure(1, weight=1)

    # --- Alt Durum ve Günlük Alanı ---
    bottom_container = ctk.CTkFrame(window, fg_color="transparent")
    bottom_container.grid(row=1, column=0, sticky="ew", padx=10, pady=(5, 10))
    bottom_container.grid_columnconfigure(0, weight=1)

    control_frame = ctk.CTkFrame(bottom_container)
    control_frame.grid(row=0, column=0, sticky="ew")
    
    silent_var = ctk.BooleanVar(value=True)
    cb = ctk.CTkCheckBox(control_frame, text="Sessiz Kurulum", variable=silent_var, font=("Segoe UI", int(11 * scale)))
    cb.pack(side="left", padx=12, pady=10)
    Tooltip(cb, "İşaretli olduğunda kurulumlar kullanıcıya soru sormadan, arka planda yapılır.")

    status_label = ctk.CTkLabel(control_frame, text="Başlatılmaya hazır.", text_color="#00ffff", font=("Segoe UI", int(12 * scale)))
    status_label.pack(side="left", padx=12, expand=True, fill="x")
    
    animation_label = ctk.CTkLabel(control_frame, text="", font=("Segoe UI", 16))
    animation_label.pack(side="right", padx=6)
    
    progress = ctk.CTkProgressBar(control_frame, width=200)
    progress.set(0)
    progress.pack(side="right", padx=6, pady=10)
    
    log_textbox = ctk.CTkTextbox(bottom_container, height=120, font=("Consolas", 12), state="disabled", wrap="word")
    log_textbox.grid(row=1, column=0, sticky="nsew", pady=(5,0))

    refresh_runtimes()
    window.mainloop()

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

if __name__ == "__main__":
    if is_admin():
        gui_main()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
