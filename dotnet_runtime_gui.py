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
import io
from packaging.version import parse as parse_version
import winreg
import shlex

# --- BAĞIMSIZ YARDIMCI FONKSİYONLAR ---

def resource_path(relative_path):
    """ PyInstaller tarafından oluşturulan geçici yola veya normal yola göre mutlak yolu döndürür. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_base64_file(filename):
    """ Belirtilen dosyadan base64 metnini okur. """
    try:
        with open(resource_path(filename), "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"{filename} dosyası okunurken hata: {e}")
        return None

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


# --- Ana Uygulama Sınıfı ---
class InstallerApp(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- Değişkenler ve Ayarlar ---
        self.is_animating = False
        self.spinner_cycle = cycle(["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"])
        logging.basicConfig(filename="runtime_installer.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

        # --- .NET Ayarları ---
        self.dotnet_index_url = "https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/releases-index.json"
        self.dotnet_versions_to_check = ["5", "6", "7", "8"] 
        self.latest_dotnet_versions = {}

        # --- C++ Ayarları ---
        self.cpp_versions = [
            {"year": "2005", "search_key": "2005", "url_x86": "https://download.microsoft.com/download/8/b/4/8b42259f-5d70-43f4-ac2e-4b208fd8d66a/vcredist_x86.EXE", "url_x64": "https://download.microsoft.com/download/8/b/4/8b42259f-5d70-43f4-ac2e-4b208fd8d66a/vcredist_x64.EXE"},
            {"year": "2008", "search_key": "2008", "url_x86": "https://download.microsoft.com/download/5/D/8/5D8C65CB-C849-4025-8E95-C3966CAFD8AE/vcredist_x86.exe", "url_x64": "https://download.microsoft.com/download/5/D/8/5D8C65CB-C849-4025-8E95-C3966CAFD8AE/vcredist_x64.exe"},
            {"year": "2010", "search_key": "2010", "url_x86": "https://download.microsoft.com/download/1/6/5/165255E7-1014-4D0A-B094-B6A430A6BFFC/vcredist_x86.exe", "url_x64": "https://download.microsoft.com/download/1/6/5/165255E7-1014-4D0A-B094-B6A430A6BFFC/vcredist_x64.exe"},
            {"year": "2012", "search_key": "2012", "url_x86": "https://download.microsoft.com/download/1/6/B/16B06F60-3B20-4FF2-B699-5E9B7962F9AE/VSU_4/vcredist_x86.exe", "url_x64": "https://download.microsoft.com/download/1/6/B/16B06F60-3B20-4FF2-B699-5E9B7962F9AE/VSU_4/vcredist_x64.exe"},
            {"year": "2013", "search_key": "2013", "url_x86": "https://aka.ms/highdpimfc2013x86enu", "url_x64": "https://aka.ms/highdpimfc2013x64enu"},
            {"year": "2015-2022", "search_key": "2015-2022", "url_x86": "https://aka.ms/vs/17/release/vc_redist.x86.exe", "url_x64": "https://aka.ms/vs/17/release/vc_redist.x64.exe"},
        ]

        # --- UI Elementlerini Saklamak İçin Konteynerler ---
        self.dotnet_ui_elements = {}
        self.cpp_ui_elements = {}
        self.program_buttons = []

        # --- Pencere Yapılandırması ---
        self.title("Yorglass Kurulum Yardımcısı")
        try:
            self.iconbitmap(resource_path("yorglass.ico"))
        except Exception as e:
            logging.error(f"İkon yüklenemedi: {e}")
        
        self.geometry("1100x750")
        self.minsize(900, 600)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Ana Arayüzü Oluştur ---
        self._create_navigation_frame()
        self._create_main_frames()
        self._create_status_bar()

        # --- Başlangıç İşlemleri ---
        self.select_frame_by_name("home")
        self.run_full_scan()

    def run_full_scan(self):
        threading.Thread(target=self.fetch_all_latest_versions, daemon=True).start()
        threading.Thread(target=self.refresh_cpp_ui, daemon=True).start()

    # --- LOGLAMA VE YARDIMCI METOTLAR ---
    def log_message(self, message, level="info"):
        if not hasattr(self, 'log_textbox'): return
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}\n"
        color_map = {"info": ("#00ffff", "INFO"), "success": ("#00ff88", "SUCCESS"), "error": ("#ff4d4d", "ERROR"), "warning": ("#ffd700", "WARN")}
        text_color, tag = color_map.get(level, ("white", "LOG"))
        
        self.log_textbox.tag_config(tag, foreground=text_color)
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", full_message, tag)
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")
        self.status_label.configure(text=message, text_color=text_color)
        self.update_idletasks()

    def log_error(self, message):
        logging.error(message)

    def _update_spinner_animation(self):
        if not self.is_animating:
            self.animation_label.configure(text="")
            return
        try:
            self.animation_label.configure(text=next(self.spinner_cycle))
            self.after(100, self._update_spinner_animation)
        except: pass

    def _set_all_buttons_state(self, state="normal"):
        """Tüm kurulum butonlarını devre dışı bırakır veya etkinleştirir."""
        buttons_to_toggle = self.program_buttons
        
        for elements in self.dotnet_ui_elements.values():
            buttons_to_toggle.extend([elements["install_x64"], elements["install_x86"], elements["uninstall_x64"], elements["uninstall_x86"]])
        
        for elements in self.cpp_ui_elements.values():
            buttons_to_toggle.extend([elements["install_x64"], elements["install_x86"], elements["uninstall_x64"], elements["uninstall_x86"]])

        for btn in buttons_to_toggle:
            if btn and btn.winfo_exists():
                btn.configure(state=state)
        
        if self.dotnet_refresh_button.winfo_exists(): self.dotnet_refresh_button.configure(state=state)
        if self.cpp_refresh_button.winfo_exists(): self.cpp_refresh_button.configure(state=state)

    # --- ARAYÜZ OLUŞTURMA METOTLARI ---
    def _create_navigation_frame(self):
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(5, weight=1)

        try:
            logo_image = ctk.CTkImage(Image.open(resource_path('yorglass_logo.png')), size=(150, 40))
            logo_label = ctk.CTkLabel(self.navigation_frame, image=logo_image, text="")
            logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))
        except Exception as e:
            self.log_error(f"Logo yüklenemedi: {e}")
            ctk.CTkLabel(self.navigation_frame, text="Yorglass", font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 30))
        
        button_config = {"corner_radius": 0, "height": 40, "border_spacing": 10, "fg_color": "transparent", "text_color": ("gray10", "gray90"), "hover_color": ("gray70", "gray30"), "anchor": "w"}
        self.home_button = ctk.CTkButton(self.navigation_frame, text="Anasayfa", command=lambda: self.select_frame_by_name("home"), **button_config)
        self.home_button.grid(row=1, column=0, sticky="ew")

        self.dotnet_button = ctk.CTkButton(self.navigation_frame, text=".NET Runtimes", command=lambda: self.select_frame_by_name("dotnet"), **button_config)
        self.dotnet_button.grid(row=2, column=0, sticky="ew")

        self.cpp_button = ctk.CTkButton(self.navigation_frame, text="C++ Runtimes", command=lambda: self.select_frame_by_name("cpp"), **button_config)
        self.cpp_button.grid(row=3, column=0, sticky="ew")

        self.programs_button = ctk.CTkButton(self.navigation_frame, text="Programlar", command=lambda: self.select_frame_by_name("programs"), **button_config)
        self.programs_button.grid(row=4, column=0, sticky="ew")
    
    def _create_main_frames(self):
        frame_config = {"corner_radius": 0, "fg_color": "transparent"}
        self.home_frame = ctk.CTkFrame(self, **frame_config)
        self.dotnet_frame = ctk.CTkFrame(self, **frame_config)
        self.cpp_frame = ctk.CTkFrame(self, **frame_config)
        self.programs_frame = ctk.CTkFrame(self, **frame_config)
        
        self._populate_home_frame()
        self._populate_dotnet_frame()
        self._populate_cpp_frame()
        self._populate_programs_frame()

    def _create_status_bar(self):
        bottom_container = ctk.CTkFrame(self, fg_color="transparent")
        bottom_container.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=(5, 10))
        bottom_container.grid_columnconfigure(0, weight=1)

        control_frame = ctk.CTkFrame(bottom_container)
        control_frame.grid(row=0, column=0, sticky="ew")
        
        self.silent_var = ctk.BooleanVar(value=True)
        cb = ctk.CTkCheckBox(control_frame, text="Sessiz Kurulum", variable=self.silent_var)
        cb.pack(side="left", padx=12, pady=10)
        Tooltip(cb, "İşaretli olduğunda kurulumlar kullanıcıya soru sormadan, arka planda yapılır.")

        self.status_label = ctk.CTkLabel(control_frame, text="Başlatılmaya hazır.", text_color="#00ffff")
        self.status_label.pack(side="left", padx=12, expand=True, fill="x")
        
        self.animation_label = ctk.CTkLabel(control_frame, text="", font=("Segoe UI", 16))
        self.animation_label.pack(side="right", padx=6)
        
        self.progress_bar = ctk.CTkProgressBar(control_frame, width=200)
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right", padx=6, pady=10)
        
        self.log_textbox = ctk.CTkTextbox(bottom_container, height=120, font=("Consolas", 12), state="disabled", wrap="word")
        self.log_textbox.grid(row=1, column=0, sticky="nsew", pady=(5,0))

    def _populate_home_frame(self):
        self.home_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.home_frame, text="Kurulum Yardımcısına Hoş Geldiniz", font=ctk.CTkFont(size=24, weight="bold"), text_color="#00d4ff").grid(row=0, column=0, pady=(40, 15), padx=30)
        welcome_text = "Yorglass Bilgi Teknolojileri departmanı tarafından hazırlanan bu araç, sık kullanılan yazılımların ve geliştirici paketlerinin hızlı ve standart bir şekilde kurulumu için tasarlanmıştır."
        ctk.CTkLabel(self.home_frame, text=welcome_text, wraplength=600, justify="center", font=ctk.CTkFont(size=14)).grid(row=1, column=0, pady=(0, 30), padx=30)
        notes_frame = ctk.CTkFrame(self.home_frame, fg_color="#2a2d2e")
        notes_frame.grid(row=2, column=0, pady=20, padx=40, sticky="ew")
        notes_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(notes_frame, text="Önemli Notlar", font=ctk.CTkFont(size=16, weight="bold"), text_color="#ffd700").grid(row=0, column=0, pady=(10, 5), padx=20, sticky="w")
        note1_text = "• Kurulum yapmak için lütfen sol menüden ilgili kategoriyi seçin."
        ctk.CTkLabel(notes_frame, text=note1_text, wraplength=550, justify="left", anchor="w").grid(row=1, column=0, pady=5, padx=20, sticky="w")
        note2_text = "• 'Sessiz Kurulum' seçeneği işaretliyken, kurulumlar size soru sormadan arka planda tamamlanacaktır."
        ctk.CTkLabel(notes_frame, text=note2_text, wraplength=550, justify="left", anchor="w").grid(row=2, column=0, pady=5, padx=20, sticky="w")
        note3_text = "• Bir sorunla karşılaşırsanız veya listede olmayan bir yazılıma ihtiyaç duyarsanız, lütfen IT Departmanı ile iletişime geçin."
        ctk.CTkLabel(notes_frame, text=note3_text, wraplength=550, justify="left", anchor="w").grid(row=3, column=0, pady=(5, 15), padx=20, sticky="w")

    def _populate_runtime_frame(self, parent_frame, title, versions_data, ui_elements_dict, refresh_command):
        parent_frame.grid_rowconfigure(0, weight=1)
        parent_frame.grid_columnconfigure(0, weight=1)
        
        scroll_frame = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        scroll_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        header_frame = ctk.CTkFrame(scroll_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(10,0))
        header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header_frame, text=title, font=ctk.CTkFont(size=20, weight="bold")).grid(row=0, column=0, sticky="w")
        
        refresh_button = ctk.CTkButton(header_frame, text="Yenile", command=refresh_command)
        refresh_button.grid(row=0, column=1, sticky="e")
        return refresh_button, scroll_frame

    def _populate_dotnet_frame(self):
        self.dotnet_refresh_button, scroll_frame = self._populate_runtime_frame(self.dotnet_frame, ".NET Runtimes", self.dotnet_versions_to_check, self.dotnet_ui_elements, self.run_full_scan)
        
        for version in self.dotnet_versions_to_check:
            self.dotnet_ui_elements[version] = self._create_runtime_card(scroll_frame, f".NET {version}", version, "dotnet")

    def _populate_cpp_frame(self):
        self.cpp_refresh_button, scroll_frame = self._populate_runtime_frame(self.cpp_frame, "Visual C++ Runtimes", self.cpp_versions, self.cpp_ui_elements, self.run_full_scan)

        for version_info in self.cpp_versions:
            year = version_info["year"]
            self.cpp_ui_elements[year] = self._create_runtime_card(scroll_frame, f"Visual C++ {year}", year, "cpp")

    def _create_runtime_card(self, parent, display_name, version_key, runtime_type):
        elements = {}
        card = ctk.CTkFrame(parent, fg_color="#2b2b2b")
        card.pack(fill="x", padx=20, pady=10)
        card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(card, text=display_name, font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, rowspan=2, padx=20, pady=20)
        
        for arch in ["x64", "x86"]:
            elements[f"status_{arch}"] = ctk.CTkLabel(card, text="Taranıyor...", text_color="gray60", anchor="w")
            elements[f"status_{arch}"].grid(row=0 if arch == "x64" else 1, column=1, padx=10, sticky="ew")
            
            actions_frame = ctk.CTkFrame(card, fg_color="transparent")
            actions_frame.grid(row=0 if arch == "x64" else 1, column=2, padx=10, pady=5, sticky="e")
            
            install_cmd = lambda v=version_key, a=arch: self.run_threaded_task(self.install_runtime, runtime_type, v, a)
            elements[f"install_{arch}"] = ctk.CTkButton(actions_frame, text=f"Kur ({arch})", width=100, command=install_cmd)
            elements[f"install_{arch}"].pack(side="left", padx=5)
            
            elements[f"uninstall_{arch}"] = ctk.CTkButton(actions_frame, text="Kaldır", width=60, fg_color="#C0392B", hover_color="#A93226")
            elements[f"uninstall_{arch}"].pack(side="left", padx=5)
        
        return elements

    def _populate_programs_frame(self):
        self.programs_frame.grid_columnconfigure(0, weight=1)
        self.programs_frame.grid_rowconfigure(0, weight=1)
        programs_scroll_frame = ctk.CTkScrollableFrame(self.programs_frame, fg_color="transparent")
        programs_scroll_frame.grid(row=0, column=0, padx=10, pady=0, sticky="nsew")
        
        ctk.CTkLabel(programs_scroll_frame, text="Popüler Yazılımlar", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)
        
        programs = [
            ("WinRAR", 'winrar_base64.txt', "exe", 'winrar_base64.png'),
            ("FortiClientVPN", 'forticlient_base64.txt', "exe", 'forticlient_base64.png'),
            ("TightVNC", 'vnc_base64.txt', "msi", 'tightvnc_icon_resized.png'),
            ("Microsoft Office", 'office_base64.txt', "exe", 'office_base64.png'),
        ]
        online_programs = [
             ("Google Chrome", "https://dl.google.com/chrome/install/latest/chrome_installer.exe", ["/silent", "/install"], 'chrome_icon.png')
        ]
        
        program_grid = ctk.CTkFrame(programs_scroll_frame, fg_color="transparent")
        program_grid.pack(pady=10, padx=20, fill="both", expand=True)
        
        cols = 3 
        all_progs = programs + online_programs
        for i, prog_info in enumerate(all_progs):
            program_grid.grid_columnconfigure(i % cols, weight=1)
            card = ctk.CTkFrame(program_grid, fg_color="#2b2b2b")
            card.grid(row=i // cols, column=i % cols, padx=15, pady=15, sticky="nsew")
            
            try:
                icon_path = resource_path(prog_info[3])
                img = ctk.CTkImage(Image.open(icon_path), size=(48, 48))
                ctk.CTkLabel(card, image=img, text="").pack(pady=(20, 10))
            except Exception as e:
                 self.log_error(f"{prog_info[3]} ikonu yüklenemedi: {e}")

            ctk.CTkLabel(card, text=f"{prog_info[0]}", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0, 10))
            
            action = None
            if len(prog_info) == 4 and isinstance(prog_info[1], str) and prog_info[1].endswith('.txt'):
                action = lambda name=prog_info[0], file=prog_info[1], type=prog_info[2]: self.run_threaded_task(self.install_embedded_program, name, load_base64_file(file), type)
            else:
                action = lambda name=prog_info[0], url=prog_info[1], params=prog_info[2]: self.run_threaded_task(self.install_online_program, name, url, params)

            button = ctk.CTkButton(card, text="Kur", width=120, height=32, command=action)
            button.pack(pady=(0, 20))
            self.program_buttons.append(button)

    # --- NAVİGASYON ---
    def select_frame_by_name(self, name):
        buttons = {"home": self.home_button, "dotnet": self.dotnet_button, "cpp": self.cpp_button, "programs": self.programs_button}
        frames = {"home": self.home_frame, "dotnet": self.dotnet_frame, "cpp": self.cpp_frame, "programs": self.programs_frame}
        
        for btn_name, button in buttons.items():
            button.configure(fg_color=("gray75", "gray25") if name == btn_name else "transparent")
        
        for frame_name, frame in frames.items():
            if name == frame_name:
                frame.grid(row=0, column=1, sticky="nsew")
            else:
                frame.grid_forget()

    # --- GENEL AMAÇLI METOTLAR ---
    def run_threaded_task(self, target_func, *args):
        def task_wrapper():
            self.after(0, self._set_all_buttons_state, "disabled")
            self.is_animating = True
            self.after(0, self._update_spinner_animation)
            try:
                target_func(*args)
            except Exception as e:
                self.log_message(f"İşlem sırasında beklenmedik bir hata oluştu: {e}", "error")
                self.log_error(f"Threaded task error in {target_func.__name__}: {e}")
            finally:
                self.is_animating = False
                self.after(0, self._set_all_buttons_state, "normal")
                self.after(0, self.progress_bar.set, 0)

        threading.Thread(target=task_wrapper, daemon=True).start()

    def scan_installed_programs(self, search_patterns):
        installed = {}
        for key in search_patterns:
            installed[key] = {"x64": None, "x86": None}

        uninstall_key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        access_masks = {"x64": winreg.KEY_READ | winreg.KEY_WOW64_64KEY, "x86": winreg.KEY_READ | winreg.KEY_WOW64_32KEY}

        for arch, access_mask in access_masks.items():
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key_path, 0, access_mask) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                for search_key, patterns in search_patterns.items():
                                    if any(p.lower() in display_name.lower() for p in patterns):
                                        installed[search_key][arch] = display_name
                                        break
                        except (OSError, FileNotFoundError):
                            continue
            except FileNotFoundError:
                self.log_error(f"Kayıt defteri yolu bulunamadı: {uninstall_key_path} ({arch})")
            except Exception as e:
                self.log_error(f"Kayıt defteri okunurken hata ({arch}): {e}")
        return installed

    # --- .NET ÖZEL METOTLARI ---
    def fetch_all_latest_versions(self):
        self.log_message("En son .NET sürüm bilgileri alınıyor...", "info")
        try:
            index_res = requests.get(self.dotnet_index_url, verify=False, timeout=10)
            index_res.raise_for_status()
            index = index_res.json()

            for release_index in index["releases-index"]:
                major_version = release_index["channel-version"].split('.')[0]
                if major_version in self.dotnet_versions_to_check:
                    try:
                        release_url = release_index["releases.json"]
                        releases_res = requests.get(release_url, verify=False, timeout=10)
                        releases_res.raise_for_status()
                        releases = releases_res.json()
                        latest_release = releases["releases"][0]
                        
                        if "runtime" in latest_release:
                            runtime_info = latest_release["runtime"]
                            version_data = {"version": runtime_info["version"], "x64_url": None, "x86_url": None}
                            
                            for file_info in runtime_info.get("files", []):
                                file_name = file_info.get("name", "")
                                if file_name.endswith("win-x64.exe") and "runtime" in file_name:
                                    version_data["x64_url"] = file_info.get("url")
                                elif file_name.endswith("win-x86.exe") and "runtime" in file_name:
                                    version_data["x86_url"] = file_info.get("url")
                                    
                            self.latest_dotnet_versions[major_version] = version_data
                    except (requests.exceptions.RequestException, json.JSONDecodeError, KeyError, IndexError) as e:
                        self.log_error(f"{major_version} için en son sürüm alınamadı: {e}")
            self.log_message(".NET sürüm bilgileri başarıyla alındı.", "success")
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            self.log_message(".NET sürüm bilgileri alınamadı. İnternet bağlantınızı kontrol edin.", "error")
            self.log_error(f"Ana .NET sürüm indeksi alınamadı: {e}")
        
        self.after(0, self.refresh_dotnet_ui)

    def refresh_dotnet_ui(self):
        self.log_message("Kurulu .NET sürümleri taranıyor...")
        search_patterns = {v: [f".NET Runtime - {v}."] for v in self.dotnet_versions_to_check}
        installed_programs = self.scan_installed_programs(search_patterns)

        for version_key, elements in self.dotnet_ui_elements.items():
            for arch in ["x64", "x86"]:
                installed_name = installed_programs.get(version_key, {}).get(arch)
                version_info = self.latest_dotnet_versions.get(version_key)
                latest_version = version_info.get("version") if version_info else None
                
                status_label = elements[f"status_{arch}"]
                install_button = elements[f"install_{arch}"]
                uninstall_button = elements[f"uninstall_{arch}"]

                if installed_name:
                    installed_version_str = ''.join(filter(lambda x: x.isdigit() or x == '.', installed_name.split(' - ')[-1]))
                    uninstall_button.configure(command=lambda n=installed_name, a=arch: self.run_threaded_task(self.uninstall_program, n, a))
                    uninstall_button.pack(side="left", padx=5)
                    
                    if latest_version and parse_version(installed_version_str) < parse_version(latest_version):
                        status_label.configure(text=f"Kurulu: {installed_version_str} (Güncelleme var)", text_color="#ffd700")
                        install_button.configure(text="Güncelle", fg_color="#E67E22", state="normal")
                    else:
                        status_label.configure(text=f"Kurulu: {installed_version_str}", text_color="#00ff88")
                        install_button.configure(text="Güncel", state="disabled")
                else:
                    uninstall_button.pack_forget()
                    status_label.configure(text="Kurulu değil", text_color="gray60")
                    install_button.configure(text="Kur", fg_color="#1F6AA5", state="normal")
        
        self.log_message(".NET taraması tamamlandı.", "success")

    # --- C++ ÖZEL METOTLARI ---
    def refresh_cpp_ui(self):
        self.log_message("Kurulu C++ sürümleri taranıyor...")
        search_patterns = {v["year"]: [f"c++ {v['search_key']} redistributable"] for v in self.cpp_versions}
        installed_programs = self.scan_installed_programs(search_patterns)

        for version_key, elements in self.cpp_ui_elements.items():
            for arch in ["x64", "x86"]:
                installed_name = installed_programs.get(version_key, {}).get(arch)
                
                status_label = elements[f"status_{arch}"]
                install_button = elements[f"install_{arch}"]
                uninstall_button = elements[f"uninstall_{arch}"]

                if installed_name:
                    status_label.configure(text="Kurulu", text_color="#00ff88")
                    install_button.configure(state="disabled", text="Kurulu")
                    uninstall_button.configure(command=lambda n=installed_name, a=arch: self.run_threaded_task(self.uninstall_program, n, a))
                    uninstall_button.pack(side="left", padx=5)
                else:
                    status_label.configure(text="Kurulu değil", text_color="gray60")
                    install_button.configure(state="normal", text=f"Kur ({arch})")
                    uninstall_button.pack_forget()
        
        self.log_message("C++ taraması tamamlandı.", "success")

    # --- GENEL KURULUM/KALDIRMA METOTLARI ---
    def install_runtime(self, runtime_type, version_key, arch):
        if runtime_type == "dotnet":
            version_info = self.latest_dotnet_versions.get(version_key)
            if not version_info or not version_info.get("version"):
                self.log_message(f".NET {version_key} için sürüm bilgisi bulunamadı.", "error")
                return
            runtime_version = version_info["version"]
            installer_url = version_info.get(f"{arch}_url")
            display_name = f".NET Runtime {runtime_version} ({arch})"
            params = ["/install", "/quiet", "/norestart"]
        
        elif runtime_type == "cpp":
            version_info = next((v for v in self.cpp_versions if v["year"] == version_key), None)
            if not version_info:
                self.log_message(f"C++ {version_key} için sürüm bilgisi bulunamadı.", "error")
                return
            installer_url = version_info.get(f"url_{arch}")
            display_name = f"Visual C++ {version_key} ({arch})"
            params = self._get_cpp_params(version_key)
        
        else:
            return

        if not installer_url:
            self.log_message(f"{display_name} için indirme linki bulunamadı.", "error")
            return
        
        self.install_online_program(display_name, installer_url, params)
        self.after(500, self.run_full_scan)

    def uninstall_program(self, display_name, arch):
        self.log_message(f"{display_name} ({arch}) kaldırılıyor...")
        access_mask = winreg.KEY_READ | (winreg.KEY_WOW64_64KEY if arch == 'x64' else winreg.KEY_WOW64_32KEY)
        uninstall_key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
        uninstall_command = None

        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, uninstall_key_path, 0, access_mask) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            reg_display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            if reg_display_name.lower() == display_name.lower():
                                uninstall_command = winreg.QueryValueEx(subkey, "UninstallString")[0]
                                break
                    except (OSError, FileNotFoundError):
                        continue
        except Exception as e:
            self.log_message(f"Kayıt defteri okunurken hata: {e}", "error")
            return

        if not uninstall_command:
            self.log_message(f"{display_name} için kaldırma komutu bulunamadı.", "warning")
            return

        try:
            is_silent = self.silent_var.get()
            command_parts = shlex.split(uninstall_command.replace(' /I', ' /X'))
            
            if is_silent:
                if ".exe" in command_parts[0].lower():
                    if "/uninstall" not in command_parts: command_parts.append("/uninstall")
                    if "/quiet" not in command_parts: command_parts.append("/quiet")
                    if "/norestart" not in command_parts: command_parts.append("/norestart")
                else: # MsiExec
                    if "/quiet" not in command_parts and "/qn" not in command_parts:
                        command_parts.append("/qn")
            else:
                command_parts = [p for p in command_parts if p.lower() not in ["/quiet", "/norestart", "/qn"]]

            self.log_message(f"Kaldırma komutu çalıştırılıyor: {' '.join(command_parts)}", "info")
            subprocess.run(command_parts, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            self.log_message(f"{display_name} başarıyla kaldırıldı.", "success")

        except subprocess.CalledProcessError as e:
            error_output = e.stderr or e.stdout
            self.log_message(f"Kaldırma sırasında hata oluştu: {error_output}", "error")
        except Exception as e:
            self.log_message(f"Kaldırma işlemi başarısız: {e}", "error")

        self.after(500, self.run_full_scan)

    def install_embedded_program(self, name, base64_data, filetype="exe"):
        if not base64_data:
            self.log_message(f"{name} için kaynak dosyası okunamadı veya boş.", "error")
            return

        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                self.log_message(f"{name} kurulumu hazırlanıyor...")
                file_path = os.path.join(temp_dir, f"{name}_installer.{filetype}")
                with open(file_path, "wb") as f:
                    f.write(base64.b64decode(base64_data.encode()))
                
                self.log_message(f"{name} kurulumu başlatılıyor...")
                silent = self.silent_var.get()
                cmd = []
                if filetype == "msi":
                    cmd = ["msiexec", "/i", file_path]
                    if silent: cmd.extend(["/quiet", "/norestart"])
                else:
                    cmd = [file_path]
                    if silent: cmd.append("/S")
                
                subprocess.run(cmd, check=True)
                self.log_message(f"{name} kurulumu tamamlandı.", "success")
            except Exception as e:
                self.log_message(f"{name} kurulumunda hata: {e}", "error")

    def _get_cpp_params(self, version_key):
        silent_params = {
            "2005": ["/q"], "2008": ["/q"], "2010": ["/q"], "2012": ["/quiet", "/norestart"],
            "2013": ["/quiet", "/norestart"], "2015-2022": ["/quiet", "/norestart"]
        }
        return silent_params.get(version_key, []) if self.silent_var.get() else []

    def install_online_program(self, name, url, extra_params=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                self.log_message(f"{name} indiriliyor...")
                file_path = os.path.join(temp_dir, f"{name.replace(' ', '_')}_installer.exe")
                r = requests.get(url, stream=True, verify=False, timeout=30)
                r.raise_for_status()
                content_length = int(r.headers.get("Content-Length", 0))
                downloaded = 0
                with open(file_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if content_length > 0:
                            percent = downloaded / content_length
                            self.progress_bar.set(min(percent, 1.0))
                            self.status_label.configure(text=f"{name} indiriliyor... %{int(percent * 100)}")
                            self.update_idletasks()

                self.log_message(f"{name} kurulumu başlatılıyor...")
                cmd = [file_path]
                if self.silent_var.get() and extra_params:
                    cmd.extend(extra_params)

                subprocess.run(cmd, check=True)
                self.log_message(f"{name} kurulumu tamamlandı.", "success")
            except requests.exceptions.RequestException as e:
                self.log_message(f"{name} indirilemedi: {e}", "error")
            except subprocess.CalledProcessError as e:
                self.log_message(f"{name} kurulumu başarısız oldu: {e}", "error")
            except Exception as e:
                self.log_message(f"{name} kurulumunda hata: {e}", "error")


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

# --- UYGULAMA GİRİŞ NOKTASI ---
if __name__ == "__main__":
    if is_admin():
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        app = InstallerApp()
        app.mainloop()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
