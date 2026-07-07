import os
import json
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from google import genai
from google.genai import types

# --- KONFIGURASI GLOBAL ---
HISTORY_FILE = "gemini_chat_history.json"

# Pemetaan Tampilan UI ke Nama Model Teknis Google API
MODEL_OPTIONS = {
    "Gemini 3.5 (Flash)": "gemini-3.5-flash",
    "Gemini 3 (Flash)": "gemini-3-flash",
    "Gemini 2.5 (Flash)": "gemini-2.5-flash",
    "Gemma 4 31B IT": "gemma-4-31b-it"
}

# Palet Warna Gemini Web App (Dark Mode)
BG_MAIN = "#131314"
BG_SIDE = "#1e1f20"
BG_BUTTON = "#2a2b2d"
BG_BUTTON_HOVER = "#3c4043"
TEXT_COLOR = "#e3e3e3"
ACCENT_BLUE = "#a8c7fa"
ACCENT_PURPLE = "#c3b3f9"
TEXT_MUTED = "#9aa0a6"

# =====================================================================
# 1. DOMAIN LAYER (Business Logic)
# =====================================================================
class ProjectBundler:
    """
    Domain Service untuk memetakan dan merangkum seluruh struktur direktori
    serta isi berkas teks/kode ke dalam satu berkas konteks terstruktur.
    """
    IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', 'venv', '.venv', '.idea', '.vscode', 'dist', 'build'}
    IGNORE_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.zip', '.tar', '.gz', '.exe', '.dll', '.pyc', '.pdf'}

    @classmethod
    def bundle(cls, folder_path: str) -> str:
        if not os.path.exists(folder_path):
            raise FileNotFoundError("Folder tidak ditemukan.")

        lines = []
        lines.append(f"=== PROJECT CODEBASE BUNDLE: {os.path.basename(folder_path)} ===\n")
        lines.append("--- STRUKTUR DIREKTORI ---")

        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if d not in cls.IGNORE_DIRS]
            level = root.replace(folder_path, '').count(os.sep)
            indent = ' ' * 4 * level
            lines.append(f"{indent}📁 {os.path.basename(root) or root}/")
            sub_indent = ' ' * 4 * (level + 1)
            for f in files:
                _, ext = os.path.splitext(f)
                if ext.lower() not in cls.IGNORE_EXTS:
                    lines.append(f"{sub_indent}📄 {f}")

        lines.append("\n--- ISI BERKAS KODE & TEKS ---")

        for root, dirs, files in os.walk(folder_path):
            dirs[:] = [d for d in dirs if d not in cls.IGNORE_DIRS]
            for f in files:
                _, ext = os.path.splitext(f)
                if ext.lower() in cls.IGNORE_EXTS:
                    continue
                
                file_path = os.path.join(root, f)
                relative_path = os.path.relpath(file_path, folder_path)
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file_ref:
                        content = file_ref.read()
                    lines.append(f"\n--- File: {relative_path} ---")
                    lines.append(content)
                    lines.append("-" * 40)
                except Exception as e:
                    lines.append(f"\n--- File: {relative_path} (Gagal membaca: {str(e)}) ---")

        return "\n".join(lines)


# =====================================================================
# 2. INFRASTRUCTURE LAYER (External APIs & OS Systems)
# =====================================================================
class ClipboardService:
    """
    Infrastructure Service untuk berinteraksi dengan Clipboard Sistem Operasi.
    """
    @classmethod
    def grab_image(cls):
        try:
            from PIL import ImageGrab, Image
            img = ImageGrab.grabclipboard()
            if isinstance(img, Image.Image):
                return img
        except ImportError:
            print("[System] Pustaka Pillow belum terinstal. Jalankan: pip install pillow")
        except Exception as e:
            print(f"[System] Gagal mengakses clipboard: {e}")
        return None


class GeminiService:
    """
    Infrastruktur Gateway untuk mengelola koneksi API Client, 
    sesi chat, dan proses unggah file ke Google Gen AI SDK.
    """
    def __init__(self, api_key: str, model_name: str, system_prompt: str):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.chat = None

    def start_chat(self, history: list):
        # Mendaftarkan Google Search & Code Execution Sandbox sebagai Tools aktif
        self.chat = self.client.chats.create(
            model=self.model_name,
            history=history,
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt,
                tools=[
                    types.Tool(google_search=types.GoogleSearch()),
                    types.Tool(code_execution=types.ToolCodeExecution())
                ],
                thinking_config=types.ThinkingConfig(thinking_level="high")
            )
        )

    def upload_file(self, file_path: str):
        return self.client.files.upload(file=file_path)

    def send_message(self, message):
        return self.chat.send_message(message=message)

    def get_history(self):
        return self.chat.get_history()


# =====================================================================
# 3. PRESENTATION LAYER (GUI View & Controller)
# =====================================================================
class GeminiModernGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Multi-Model Chat Client")
        self.root.geometry("850x700")
        self.root.configure(bg=BG_MAIN)
        
        # State & Variabel Sesi
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        self.gemini_service = None
        self.staged_file_path = None
        self.staged_folder_path = None
        
        self.setup_scrollbar_style()
        self.create_widgets()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        if self.api_key:
            self.init_gemini_client()

    def setup_scrollbar_style(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure(
            "Vertical.TScrollbar",
            gripcount=0,
            background=BG_BUTTON,
            troughcolor=BG_MAIN,
            bordercolor=BG_MAIN,
            arrowcolor=TEXT_COLOR,
            lightcolor=BG_MAIN,
            darkcolor=BG_MAIN
        )
        # Penyesuaian tema dropdown Combobox agar senada dengan warna latar belakang
        self.style.configure(
            "TCombobox",
            fieldbackground=BG_MAIN,
            background=BG_BUTTON,
            foreground=TEXT_COLOR,
            bordercolor="#3c4043",
            arrowcolor=TEXT_COLOR
        )
        # Konfigurasi pop-up listbox milik Combobox
        self.root.option_add("*TCombobox*Listbox.background", BG_SIDE)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT_COLOR)
        self.root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_BLUE)
        self.root.option_add("*TCombobox*Listbox.selectForeground", BG_MAIN)

    def create_widgets(self):
        # Header Panel
        self.header_frame = tk.Frame(self.root, bg=BG_SIDE, pady=10, padx=15)
        self.header_frame.pack(fill=tk.X)
        
        self.lbl_title = tk.Label(self.header_frame, text="✦ AI Chat Client", font=("Product Sans", 14, "bold"), fg=ACCENT_BLUE, bg=BG_SIDE)
        self.lbl_title.pack(side=tk.LEFT)
        
        # Penambahan Label & Dropdown Selector Model
        self.lbl_model = tk.Label(self.header_frame, text="Model:", font=("Segoe UI", 10, "bold"), fg=TEXT_MUTED, bg=BG_SIDE)
        self.lbl_model.pack(side=tk.LEFT, padx=(15, 2))
        
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(
            self.header_frame, 
            textvariable=self.model_var, 
            values=list(MODEL_OPTIONS.keys()), 
            state="readonly", 
            width=18
        )
        self.model_combo.pack(side=tk.LEFT, padx=5)
        self.model_combo.set("Gemini 3.5 (Flash)")  # Model default awal
        self.model_combo.bind("<<ComboboxSelected>>", self.on_model_changed)
        
        self.api_entry = tk.Entry(self.header_frame, show="*", bg=BG_MAIN, fg=TEXT_COLOR, bd=0, 
                                  insertbackground="white", highlightthickness=1, highlightbackground="#3c4043",
                                  highlightcolor=ACCENT_BLUE, font=("Segoe UI", 10), width=24)
        self.api_entry.pack(side=tk.LEFT, padx=15, pady=5, ipady=3)
        if self.api_key:
            self.api_entry.insert(0, self.api_key)
            
        self.btn_connect = self.create_flat_button(self.header_frame, "Connect", self.init_gemini_client, bg=BG_BUTTON, fg=TEXT_COLOR)
        self.btn_connect.pack(side=tk.LEFT, padx=5)
        
        self.btn_save = self.create_flat_button(self.header_frame, "Download Chat", self.manual_save, bg=BG_BUTTON, fg=TEXT_COLOR)
        self.btn_save.pack(side=tk.RIGHT, padx=5)
        
        self.status_label = tk.Label(self.header_frame, text="Disconnected", font=("Segoe UI", 10, "bold"), fg="#ea4335", bg=BG_SIDE)
        self.status_label.pack(side=tk.RIGHT, padx=15)

        # Chat Log Area
        self.chat_frame = tk.Frame(self.root, bg=BG_MAIN, padx=15, pady=10)
        self.chat_frame.pack(fill=tk.BOTH, expand=True)
        
        self.chat_area = tk.Text(self.chat_frame, wrap=tk.WORD, state=tk.DISABLED,
                                 font=("Segoe UI", 11), bg=BG_MAIN, fg=TEXT_COLOR,
                                 bd=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.chat_frame, orient=tk.VERTICAL, command=self.chat_area.yview)
        self.chat_area.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.chat_area.tag_config("user", foreground=ACCENT_BLUE, font=("Segoe UI", 11, "bold"))
        self.chat_area.tag_config("gemini", foreground=ACCENT_PURPLE, font=("Segoe UI", 11, "bold"))
        self.chat_area.tag_config("system", foreground=TEXT_MUTED, font=("Segoe UI", 9, "italic"))
        self.chat_area.tag_config("body", foreground=TEXT_COLOR, font=("Segoe UI", 11))
        
        # Tag khusus untuk tautan rujukan dan header context pencarian
        self.chat_area.tag_config("source", foreground=ACCENT_BLUE, font=("Segoe UI", 10, "underline"))
        self.chat_area.tag_config("source_header", foreground=TEXT_MUTED, font=("Segoe UI", 10, "bold"))

        # Bottom Input Area
        self.bottom_frame = tk.Frame(self.root, bg=BG_MAIN, padx=15, pady=15)
        self.bottom_frame.pack(fill=tk.X)
        
        self.file_label = tk.Label(self.bottom_frame, text="", bg=BG_MAIN, fg=ACCENT_BLUE, font=("Segoe UI", 9, "italic"), anchor="w")
        self.file_label.pack(fill=tk.X, pady=(0, 5))
        
        # Pill Input Box
        self.input_container = tk.Frame(self.bottom_frame, bg=BG_SIDE, bd=0, highlightthickness=1, highlightbackground="#3c4043")
        self.input_container.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(0, 10))
        
        self.msg_entry = tk.Text(self.input_container, height=3, bg=BG_SIDE, fg=TEXT_COLOR,
                                 font=("Segoe UI", 11), insertbackground="white", bd=0,
                                 highlightthickness=0, wrap=tk.WORD, spacing1=3)
        self.msg_entry.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
        self.msg_entry.bind("<Return>", self.on_enter_pressed)
        
        # BINDING CTRL+V UNTUK DETEKSI PASTE GAMBAR
        self.msg_entry.bind("<Control-v>", self.on_paste_event)
        
        # Action Buttons
        self.action_frame = tk.Frame(self.bottom_frame, bg=BG_MAIN)
        self.action_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.btn_attach = self.create_flat_button(self.action_frame, "📎 File", self.attach_file, bg=BG_BUTTON, fg=TEXT_COLOR)
        self.btn_attach.pack(fill=tk.X, pady=2)

        self.btn_attach_folder = self.create_flat_button(self.action_frame, "📁 Folder", self.attach_folder, bg=BG_BUTTON, fg=TEXT_COLOR)
        self.btn_attach_folder.pack(fill=tk.X, pady=2)
        
        self.btn_send = self.create_flat_button(self.action_frame, "Send ➔", self.send_message_thread, bg="#1a73e8", fg="#ffffff", hover_bg="#1557b0")
        self.btn_send.pack(fill=tk.X, pady=2)

    def create_flat_button(self, parent, text, command, bg, fg, hover_bg=BG_BUTTON_HOVER):
        btn = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, 
                        activebackground=hover_bg, activeforeground="#ffffff", 
                        bd=0, relief="flat", font=("Segoe UI", 9, "bold"),
                        padx=12, pady=6, cursor="hand2")
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        return btn

    # --- DETEKSI DAN IMPLEMENTASI PASTE GAMBAR ---
    def on_paste_event(self, event):
        img = ClipboardService.grab_image()
        if img:
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, "clipboard_image.png")
            try:
                img.save(temp_file_path, "PNG")
                self.staged_file_path = temp_file_path
                self.staged_folder_path = None
                self.file_label.config(text="📎 Gambar Tempel (Clipboard) Terlampir (Siap dikirim!)")
                return "break"
            except Exception as e:
                print(f"[GUI] Gagal memproses gambar tempel: {e}")
        return None

    # --- LOGIKA PENALANAN / ALIH MODEL ---
    def on_model_changed(self, event=None):
        """
        Dijalankan saat pengguna memilih model baru di dropdown Combobox.
        Memperbarui model pada backend sambil membawa riwayat obrolan aktif.
        """
        selected_display = self.model_var.get()
        new_model_name = MODEL_OPTIONS.get(selected_display)
        
        self.lbl_title.config(text=f"✦ {selected_display}")
        
        # Jika koneksi sudah aktif, alihkan secara dinamis tanpa menghapus konteks log
        if self.gemini_service and self.api_key:
            self.append_to_chat("System", f"Mengalihkan model ke {selected_display}...", "system")
            try:
                self.gemini_service.model_name = new_model_name
                
                # Mengambil riwayat yang sedang berjalan dan membangun sesi chat baru dengan model terpilih
                current_history = self.gemini_service.get_history()
                self.gemini_service.start_chat(history=current_history)
                
                self.append_to_chat("System", f"Model berhasil dialihkan ke {selected_display}.", "system")
            except Exception as e:
                self.append_to_chat("System", f"Gagal mengalihkan model: {str(e)}", "system")
                messagebox.showerror("Error", f"Gagal mengalihkan model:\n{e}")

    # --- KONEKSI SERVIS ---
    def init_gemini_client(self):
        key = self.api_entry.get().strip()
        if not key:
            messagebox.showwarning("Warning", "Masukkan API Key terlebih dahulu.")
            return
            
        self.status_label.config(text="Connecting...", fg="orange")
        self.btn_connect.config(state=tk.DISABLED)
        
        threading.Thread(target=self._async_init, args=(key,), daemon=True).start()
        
    def _async_init(self, key):
        try:
            system_prompt = (
                "Aturan respons:\n"
                "1. Ketika user bertanya biasa, jawab dengan runut, sederhana, dan gunakan analogi "
                "yang mudah dipahami oleh orang awam (hindari jargon teknis yang rumit).\n"
                "2. JIKA menjelaskan alur proses, urutan langkah, atau diagram:\n"
                "   - JANGAN sekali-kali menggunakan format rumus matematika LaTeX seperti \\text{} atau \\rightarrow.\n"
                "   - WAJIB gunakan diagram teks/ASCII sederhana di dalam blok kode `bash` agar mudah dibaca dan di-copy-paste oleh user.\n"
                "   - Contoh format diagram: [Langkah 1] ──> [Langkah 2] ──> [Langkah 3]\n"
                "3. Ketika user meminta aplikasi, berikan kodenya setara MVP (Minimum Viable Product), "
                "menerapkan standar Clean Code, dan memiliki struktur DDD (Domain-Driven Design) yang jelas."
                "4. Ketika user menanyakan aturan yang tidak kamu ketahui, gunakan google search secara aktif."
                "5. Maksimalkan penggunaan tokenmu ketika menjawab."
            )
            
            # Mendapatkan model terpilih saat ini dari variabel dropdown
            selected_display = self.model_var.get()
            model_name = MODEL_OPTIONS.get(selected_display, "gemma-4-31b-it")
            
            service = GeminiService(api_key=key, model_name=model_name, system_prompt=system_prompt)
            history = self.load_history_local()
            service.start_chat(history=history)
            
            self.gemini_service = service
            self.api_key = key
            
            self.root.after(0, self._on_init_success, len(history), selected_display)
        except Exception as e:
            self.root.after(0, self._on_init_failure, str(e))
            
    def _on_init_success(self, history_count, model_display):
        self.status_label.config(text="Connected", fg="#34a853")
        self.btn_connect.config(state=tk.NORMAL)
        self.lbl_title.config(text=f"✦ {model_display}")
        self.append_to_chat("System", f"Terhubung ke model {model_display} dengan sistem instruksi aktif, pencarian web, serta eksekusi kode terintegrasi.", "system")
        if history_count > 0:
            self.append_to_chat("System", f"Memuat {history_count} pesan riwayat sebelumnya dari file lokal.", "system")
            self.populate_history_to_chat()
            
    def _on_init_failure(self, err_msg):
        self.status_label.config(text="Disconnected", fg="#ea4335")
        self.btn_connect.config(state=tk.NORMAL)
        self.append_to_chat("System", f"Gagal masuk: {err_msg}", "system")
        messagebox.showerror("Error", f"Gagal menginisialisasi API:\n{err_msg}")

    # --- MANAJEMEN RIWAYAT ---
    def load_history_local(self):
        if not os.path.exists(HISTORY_FILE):
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            history = []
            for item in data:
                history.append(
                    types.Content(role=item["role"], parts=[types.Part(text=item["text"])])
                )
            return history
        except Exception as e:
            print(f"Gagal memuat file history: {e}")
            return []

    def populate_history_to_chat(self):
        self.chat_area.configure(state=tk.NORMAL)
        self.chat_area.delete("1.0", tk.END)
        self.chat_area.insert(tk.END, "⚙️ RIWAYAT CHAT LOKAL DIMUAT\n\n", "system")
        
        for content in self.gemini_service.get_history():
            sender = "👤 Anda" if content.role == "user" else "✦ Gemini"
            tag = "user" if content.role == "user" else "gemini"
            
            text_parts = []
            for part in content.parts:
                if hasattr(part, 'text') and part.text:
                    text_parts.append(part.text)
                elif hasattr(part, 'inline_data') and part.inline_data:
                    text_parts.append("[Berkas Media]")
                elif hasattr(part, 'executable_code') and part.executable_code:
                    text_parts.append(f"\n```python\n# [Executed in Google Sandbox]\n{part.executable_code.code}\n```")
                elif hasattr(part, 'code_execution_result') and part.code_execution_result:
                    text_parts.append(f"\n```text\n# [Sandbox Output]\n{part.code_execution_result.output}\n```")
            
            if text_parts:
                self.chat_area.insert(tk.END, f"{sender}\n", tag)
                self.chat_area.insert(tk.END, f"{'\n'.join(text_parts)}\n\n", "body")
                
        self.chat_area.configure(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def get_history_list(self):
        if not self.gemini_service:
            return []
        try:
            raw_history = self.gemini_service.get_history()
            serializable_history = []
            for content in raw_history:
                text_parts = []
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                    elif hasattr(part, 'executable_code') and part.executable_code:
                        text_parts.append(f"\n```python\n# [Executed in Google Sandbox]\n{part.executable_code.code}\n```")
                    elif hasattr(part, 'code_execution_result') and part.code_execution_result:
                        text_parts.append(f"\n```text\n# [Sandbox Output]\n{part.code_execution_result.output}\n```")
                if text_parts:
                    serializable_history.append({"role": content.role, "text": "\n".join(text_parts)})
            return serializable_history
        except:
            return []

    def auto_save(self):
        history_list = self.get_history_list()
        if history_list:
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(history_list, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Auto-save gagal: {e}")

    def manual_save(self):
        if not self.gemini_service:
            messagebox.showwarning("Warning", "Tidak ada sesi obrolan aktif untuk diunduh.")
            return
        
        history_list = self.get_history_list()
        if history_list:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON Files", "*.json"), ("Text Files", "*.txt"), ("All Files", "*.*")],
                title="Ekspor Riwayat Percakapan"
            )
            if save_path:
                try:
                    if save_path.endswith(".json"):
                        with open(save_path, "w", encoding="utf-8") as f:
                            json.dump(history_list, f, indent=2, ensure_ascii=False)
                    else:
                        with open(save_path, "w", encoding="utf-8") as f:
                            for msg in history_list:
                                sender = "Anda" if msg["role"] == "user" else "Gemini"
                                f.write(f"{sender}:\n{msg['text']}\n\n" + "="*50 + "\n\n")
                    messagebox.showinfo("Sukses", f"Riwayat berhasil diunduh ke:\n{save_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Gagal mengunduh berkas: {e}")

    # --- PENGIRIMAN & PROSES UNGGAH ---
    def attach_file(self):
        file_path = filedialog.askopenfilename(
            title="Pilih Berkas",
            filetypes=[("All Files", "*.*")]
        )
        if file_path:
            self.staged_file_path = file_path
            self.staged_folder_path = None
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"📎 File Terlampir: {filename}")

    def attach_folder(self):
        folder_path = filedialog.askdirectory(title="Pilih Folder Sumber")
        if folder_path:
            self.staged_folder_path = folder_path
            self.staged_file_path = None
            foldername = os.path.basename(folder_path) or folder_path
            self.file_label.config(text=f"📁 Folder Terlampir: {foldername} (Menunggu dikirim...)")

    def on_enter_pressed(self, event):
        if not (event.state & 0x1):
            self.send_message_thread()
            return "break"

    def send_message_thread(self):
        if not self.gemini_service or not self.gemini_service.chat:
            messagebox.showerror("Error", "Gagal mengirim. Hubungkan API Key Anda terlebih dahulu.")
            return
            
        message_text = self.msg_entry.get("1.0", tk.END).strip()
        file_path = self.staged_file_path
        folder_path = self.staged_folder_path
        
        if not message_text and not file_path and not folder_path:
            return
            
        self.msg_entry.delete("1.0", tk.END)
        self.staged_file_path = None
        self.staged_folder_path = None
        self.file_label.config(text="")
        
        if file_path:
            filename = os.path.basename(file_path)
            if filename == "clipboard_image.png":
                self.append_to_chat("👤 Anda", f"[Gambar Tempel dari Clipboard]\n{message_text}", "user")
            else:
                self.append_to_chat("👤 Anda", f"[Berkas: {filename}]\n{message_text}", "user")
        elif folder_path:
            self.append_to_chat("👤 Anda", f"[Folder: {os.path.basename(folder_path)}]\n{message_text}", "user")
        else:
            self.append_to_chat("👤 Anda", message_text, "user")
            
        self.status_label.config(text="Thinking...", fg="orange")
        self.btn_send.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self.send_api_call, args=(message_text, file_path, folder_path), daemon=True)
        thread.start()

    def send_api_call(self, text, file_path, folder_path):
        try:
            content_payload = []
            
            # Kasus 1: Mengirim Berkas Tunggal (Termasuk Gambar Clipboard)
            if file_path:
                self.append_to_chat("System", f"Mengunggah berkas '{os.path.basename(file_path)}'...", "system")
                uploaded_file = self.gemini_service.upload_file(file_path)
                content_payload.append(uploaded_file)
                
                if "clipboard_image.png" in file_path:
                    try:
                        os.remove(file_path)
                    except:
                        pass
            
            # Kasus 2: Mengirim Folder
            elif folder_path:
                self.append_to_chat("System", "Sedang menyusun peta struktur dan menggabungkan berkas kode...", "system")
                bundled_text = ProjectBundler.bundle(folder_path)
                
                temp_dir = tempfile.gettempdir()
                temp_file_name = f"project_context_{os.path.basename(folder_path)}.txt"
                temp_file_path = os.path.join(temp_dir, temp_file_name)
                
                with open(temp_file_path, "w", encoding="utf-8") as temp_file:
                    temp_file.write(bundled_text)
                
                self.append_to_chat("System", "Mengunggah paket data proyek ke server...", "system")
                uploaded_file = self.gemini_service.upload_file(temp_file_path)
                content_payload.append(uploaded_file)
                
                try:
                    os.remove(temp_file_path)
                except:
                    pass
            
            # Payload Teks
            if text:
                content_payload.append(text)
            else:
                content_payload.append("Tolong analisis berkas/proyek yang saya unggah ini.")
                
            msg_param = content_payload[0] if len(content_payload) == 1 else content_payload
            response = self.gemini_service.send_message(msg_param)
            
            # Format respons untuk mengekstrak Teks, Hasil Eksekusi Sandbox, dan Grounding Sources
            formatted_text, sources = self.format_rich_response(response)
            
            self.root.after(0, self.on_response_success, formatted_text, sources)
        except Exception as e:
            self.root.after(0, self.on_response_failure, str(e))

    def format_rich_response(self, response):
        """
        Mengekstrak bagian-bagian teks utama, kode yang dijalankan di sandbox, 
        serta sumber-sumber pencarian context URL dari Google Search Grounding.
        """
        full_text_parts = []
        grounding_sources = []
        
        # 1. Ekstrak bagian-bagian konten (Teks biasa, Kode yang dieksekusi, Hasil output console)
        try:
            candidate = response.candidates[0]
            parts = candidate.content.parts
            for part in parts:
                if hasattr(part, 'text') and part.text:
                    full_text_parts.append(part.text)
                
                # Menangkap & Memformat kode Python yang dikirim ke sandbox
                if hasattr(part, 'executable_code') and part.executable_code:
                    code_block = f"\n\n```python\n# [Executed in Google Sandbox]\n{part.executable_code.code}\n```"
                    full_text_parts.append(code_block)
                    
                # Menangkap output eksekusi dari sandbox
                if hasattr(part, 'code_execution_result') and part.code_execution_result:
                    result_block = f"\n\n```text\n# [Sandbox Output - Outcome: {part.code_execution_result.outcome}]\n{part.code_execution_result.output}\n```"
                    full_text_parts.append(result_block)
        except Exception as e:
            if hasattr(response, 'text') and response.text:
                full_text_parts.append(response.text)
                
        # 2. Ekstrak Grounding Metadata (Context URLs pencarian Google)
        try:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                metadata = candidate.grounding_metadata
                if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                    for chunk in metadata.grounding_chunks:
                        if hasattr(chunk, 'web') and chunk.web:
                            grounding_sources.append({
                                "title": chunk.web.title or "Sumber Web",
                                "url": chunk.web.uri
                            })
        except Exception as e:
            print(f"[GUI] Gagal mengambil grounding metadata: {e}")
            
        return "\n".join(full_text_parts), grounding_sources

    def on_response_success(self, response_text, sources):
        self.append_to_chat("✦ Gemini", response_text, "gemini", grounding_sources=sources)
        self.status_label.config(text="Connected", fg="#34a853")
        self.btn_send.config(state=tk.NORMAL)
        self.auto_save()
        
    def on_response_failure(self, error_msg):
        self.append_to_chat("System", f"Gagal mengirim pesan: {error_msg}", "system")
        self.status_label.config(text="Error", fg="#ea4335")
        self.btn_send.config(state=tk.NORMAL)

    def append_to_chat(self, sender, text, tag, grounding_sources=None):
        self.chat_area.configure(state=tk.NORMAL)
        if sender:
            self.chat_area.insert(tk.END, f"{sender}\n", tag)
        self.chat_area.insert(tk.END, f"{text}\n\n", "body")
        
        # Menyajikan daftar URL Konteks / Rujukan Grounding (jika tersedia)
        if grounding_sources:
            self.chat_area.insert(tk.END, "🔗 CONTEXT SOURCES / GROUNDING URLS:\n", "source_header")
            for idx, source in enumerate(grounding_sources, 1):
                title = source.get("title", "Web Source")
                url = source.get("url", "")
                self.chat_area.insert(tk.END, f"  [{idx}] {title}\n", "body")
                self.chat_area.insert(tk.END, f"      {url}\n", "source")
            self.chat_area.insert(tk.END, "\n")
            
        self.chat_area.configure(state=tk.DISABLED)
        self.chat_area.see(tk.END)

    def on_close(self):
        if self.gemini_service:
            self.auto_save()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = GeminiModernGUI(root)
    root.mainloop()
