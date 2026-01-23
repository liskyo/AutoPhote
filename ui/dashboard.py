import tkinter as tk
from tkinter import ttk, Toplevel
from PIL import Image, ImageTk
import threading
from config import UI_PREVIEW_WIDTH, UI_PREVIEW_HEIGHT, CAMERA_COUNT

# Dictionary for status colors
STATUS_COLORS = {
    0: "gray",    # Disconnected
    1: "green",   # Ready/Connected
    2: "yellow",  # Capturing
    3: "blue",    # Success/Queued
    4: "red",      # Error
    5: "orange"   # Reviewing
}

class DashboardApp:
    def __init__(self, root, on_snap, on_confirm, on_retake):
        self.root = root
        self.root.title("AutoPhote Operator Dashboard")
        self.root.configure(bg="#1e1e1e") # Dark Root
        
        self.on_snap_cb = on_snap
        self.on_confirm_cb = on_confirm
        self.on_retake_cb = on_retake
        
        self.cam_labels = []
        self.cam_canvases = []
        self.tk_images = [None] * CAMERA_COUNT 
        self.original_images = [None] * CAMERA_COUNT 
        self.upload_count_var = tk.StringVar(value="Upload Queue: 0")
        
        self.setup_theme()
        self.setup_ui()
        self.setup_bindings()

    def setup_theme(self):
        # Tech Colors
        self.colors = {
            "bg": "#1e1e1e",
            "surface": "#2d2d30",
            "accent": "#00adb5", # Cyan
            "text": "#ffffff",
            "text_dim": "#aaaaaa",
            "success": "#28a745",
            "warning": "#ffc107",
            "danger": "#dc3545",
            "border": "#3e3e42"
        }
        
        style = ttk.Style()
        style.theme_use('clam')
        
        # General Defaults
        style.configure(".", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 10))
        
        # Notebook (Tabs)
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", 
                        background=self.colors["surface"], 
                        foreground=self.colors["text_dim"], 
                        padding=[20, 10], 
                        font=("Segoe UI", 12, "bold"),
                        borderwidth=0)
        style.map("TNotebook.Tab", 
                  background=[("selected", self.colors["accent"])],
                  foreground=[("selected", "#000000")])
        
        # Frames
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Card.TFrame", background=self.colors["surface"], relief="flat")
        
        # LabelFrames
        style.configure("TLabelframe", background=self.colors["surface"], bordercolor=self.colors["accent"])
        style.configure("TLabelframe.Label", background=self.colors["surface"], foreground=self.colors["accent"], font=("Segoe UI", 11, "bold"))
        
        # Labels
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Card.TLabel", background=self.colors["surface"], foreground=self.colors["text"])
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), foreground=self.colors["accent"])
        
        # Buttons (using ttk for settings)
        style.configure("TButton", 
                        font=("Segoe UI", 10, "bold"), 
                        background=self.colors["surface"], 
                        foreground=self.colors["text"], 
                        borderwidth=1,
                        focuscolor=self.colors["accent"])
        style.map("TButton", 
                  background=[("active", self.colors["accent"])], 
                  foreground=[("active", "black")])
        
        # Entry
        style.configure("TEntry", fieldbackground=self.colors["surface"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        
    def setup_ui(self):
        try:
            self.root.state('zoomed')
        except:
            pass 

        # Main Container
        main_container = tk.Frame(self.root, bg=self.colors["bg"])
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20) # Add outer margin

        # Create Notebook (Tabs)
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Monitor
        self.monitor_frame = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.monitor_frame, text=' MOMITOR (監控) ')
        
        # Tab 2: Settings
        self.settings_frame = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.settings_frame, text=' SETTINGS (設定) ')

        self.setup_monitor_tab()
        self.setup_settings_tab()

    def setup_monitor_tab(self):
        main_container = self.monitor_frame
        
        # Grid Area - Use a dark frame
        self.grid_frame = tk.Frame(main_container, bg=self.colors["bg"])
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=10)

        self.grid_frame.columnconfigure(0, weight=1)
        self.grid_frame.columnconfigure(1, weight=1)
        self.grid_frame.columnconfigure(2, weight=1)
        self.grid_frame.rowconfigure(0, weight=1)
        self.grid_frame.rowconfigure(1, weight=1)

        # --- Generate Camera Blocks ---
        for i in range(CAMERA_COUNT):
            row = 0 if i < 3 else 1
            col = i if i < 3 else (i - 3)
            
            # Card style frame
            frame = tk.Frame(self.grid_frame, bg=self.colors["surface"], bd=1, relief="solid")
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            
            frame.rowconfigure(1, weight=1)
            frame.columnconfigure(0, weight=1)

            # Header
            header_frame = tk.Frame(frame, bg=self.colors["surface"])
            header_frame.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
            
            # Use accent color for CAM ID
            tk.Label(header_frame, text=f"CAM {i+1}", font=("Segoe UI", 12, "bold"), bg=self.colors["surface"], fg=self.colors["accent"]).pack(side=tk.LEFT, padx=5)
            
            # Image Preview (Black bg)
            preview_canvas = tk.Canvas(frame, bg="black", highlightthickness=0, cursor="hand2")
            preview_canvas.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
            
            preview_canvas.bind("<Button-1>", lambda event, idx=i: self.show_enlarged_image(idx))
            preview_canvas.bind("<Configure>", lambda event, idx=i: self.on_canvas_resize(event, idx))
            self.cam_canvases.append(preview_canvas)

            # Status Bar at bottom of card
            status_frame = tk.Frame(frame, bg=self.colors["surface"])
            status_frame.grid(row=2, column=0, sticky="ew", padx=2, pady=5)
            
            lbl_status = tk.Label(status_frame, text="INIT", bg=self.colors["border"], fg="white", font=("Segoe UI", 9, "bold"), width=10)
            lbl_status.pack(side=tk.RIGHT, padx=5)
            self.cam_labels.append(lbl_status)

        # --- Action Panel (Row 1, Col 2) ---
        action_frame = tk.Frame(self.grid_frame, bg=self.colors["surface"], bd=1, relief="solid")
        action_frame.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        
        action_frame.columnconfigure(0, weight=1)
        action_frame.columnconfigure(1, weight=1)
        action_frame.rowconfigure(0, weight=0)
        action_frame.rowconfigure(1, weight=1)

        tk.Label(action_frame, text="CONTROL PANEL", font=("Segoe UI", 14, "bold"), bg=self.colors["surface"], fg=self.colors["text"]).grid(row=0, column=0, columnspan=2, pady=15)

        # Flat styling for Control Buttons
        def make_btn(parent, text, bg, cmd, size=18):
            btn = tk.Button(parent, text=text, bg=bg, fg="white", font=("Segoe UI", size, "bold"), 
                            activebackground="white", activeforeground=bg,
                            relief="flat", cursor="hand2", command=cmd)
            return btn

        self.btn_snap = make_btn(action_frame, "START (拍照)", self.colors["accent"], self.handle_snap)
        self.btn_snap.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)
        
        self.btn_retake = make_btn(action_frame, "RETAKE (重拍)", self.colors["danger"], self.handle_retake, size=14)
        self.btn_confirm = make_btn(action_frame, "CONFIRM (確認)", self.colors["success"], self.handle_confirm, size=14)
        
        self.btn_retake.grid_remove()
        self.btn_confirm.grid_remove()

        # Info Section
        info_frame = tk.Frame(main_container, bg=self.colors["bg"])
        info_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(info_frame, textvariable=self.upload_count_var, font=("Segoe UI", 11), bg=self.colors["bg"], fg=self.colors["text_dim"]).pack(side=tk.LEFT)
        tk.Label(info_frame, text="Click image to enlarge", font=("Segoe UI", 10, "italic"), bg=self.colors["bg"], fg=self.colors["text_dim"]).pack(side=tk.RIGHT)

    def browse_directory(self, entry):
        from tkinter import filedialog
        path = filedialog.askdirectory()
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    def setup_settings_tab(self):
        import config # Late import to access save logic if needed, or just use config variables
        from config import save_settings, load_settings, CAMERA_IPS, CAMERA_COUNT, CAMERA_WIDTH, CAMERA_HEIGHT, LOCAL_TEMP_BUFFER, REMOTE_SERVER_STORAGE

        # Center the settings form - Use pack to fill
        container = tk.Frame(self.settings_frame, bg=self.colors["bg"])
        container.pack(fill=tk.BOTH, expand=True, padx=50, pady=30)
        
        tk.Label(container, text="SYSTEM CONFIGURATION", font=("Segoe UI", 18, "bold"), bg=self.colors["bg"], fg=self.colors["accent"]).pack(anchor="w", pady=(0, 20))

        # --- Group 1: Camera Parameters ---
        grp_cam = ttk.LabelFrame(container, text=" Camera Parameters ", padding=15)
        grp_cam.pack(fill=tk.X, pady=10)
        
        # Grid layout for inputs
        grp_cam.columnconfigure(1, weight=1)
        grp_cam.columnconfigure(3, weight=1)
        
        # Row 0
        ttk.Label(grp_cam, text="Camera Count (相機數量):", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ent_cam_count = ttk.Entry(grp_cam, width=10)
        self.ent_cam_count.insert(0, str(CAMERA_COUNT))
        self.ent_cam_count.grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(grp_cam, text="Resolution (解析度 WxH):", style="Card.TLabel").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        res_box = tk.Frame(grp_cam, bg=self.colors["surface"])
        res_box.grid(row=0, column=3, sticky="w", padx=5)
        
        self.ent_cam_width = ttk.Entry(res_box, width=8)
        self.ent_cam_width.insert(0, str(CAMERA_WIDTH))
        self.ent_cam_width.pack(side=tk.LEFT)
        ttk.Label(res_box, text=" x ", style="Card.TLabel").pack(side=tk.LEFT)
        self.ent_cam_height = ttk.Entry(res_box, width=8)
        self.ent_cam_height.insert(0, str(CAMERA_HEIGHT))
        self.ent_cam_height.pack(side=tk.LEFT)

        # --- Group 2: Paths ---
        grp_path = ttk.LabelFrame(container, text=" Storage Paths ", padding=15)
        grp_path.pack(fill=tk.X, pady=10)
        grp_path.columnconfigure(1, weight=1)

        # Local
        ttk.Label(grp_path, text="Local Buffer (暫存):", style="Card.TLabel").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.ent_local_path = ttk.Entry(grp_path)
        self.ent_local_path.insert(0, LOCAL_TEMP_BUFFER)
        self.ent_local_path.grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(grp_path, text="SELECT", bg=self.colors["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", 
                 command=lambda: self.browse_directory(self.ent_local_path)).grid(row=0, column=2, padx=5)
        
        # Remote
        ttk.Label(grp_path, text="Remote Server (遠端):", style="Card.TLabel").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.ent_remote_path = ttk.Entry(grp_path)
        self.ent_remote_path.insert(0, REMOTE_SERVER_STORAGE)
        self.ent_remote_path.grid(row=1, column=1, sticky="ew", padx=5)
        tk.Button(grp_path, text="SELECT", bg=self.colors["accent"], fg="white", font=("Segoe UI", 9, "bold"), relief="flat", 
                 command=lambda: self.browse_directory(self.ent_remote_path)).grid(row=1, column=2, padx=5)

        # --- Group 3: IP Config ---
        grp_ip = ttk.LabelFrame(container, text=" IP Configuration ", padding=15)
        grp_ip.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.ip_entries = {}
        # Dynamic Grid for IPs
        columns = 4 # per row
        for i in range(1, 9):
            r = (i-1) // columns
            c_base = ((i-1) % columns) * 2 
            
            lbl = ttk.Label(grp_ip, text=f"Cam {i}:", style="Card.TLabel")
            lbl.grid(row=r, column=c_base, padx=(20 if c_base>0 else 5), pady=10, sticky="e")
            
            ent = ttk.Entry(grp_ip, width=14)
            val = CAMERA_IPS.get(i, "")
            ent.insert(0, val)
            ent.grid(row=r, column=c_base+1, padx=5, pady=10, sticky="w")
            self.ip_entries[i] = ent

        # --- Actions ---
        btn_frame = tk.Frame(container, bg=self.colors["bg"])
        btn_frame.pack(fill=tk.X, pady=30, side=tk.BOTTOM)
        
        # Make Save button full width (or at least prominent)
        btn_save = tk.Button(btn_frame, text="SAVE SETTINGS (儲存設定)", bg="lightgreen", fg="black", font=("Segoe UI", 12, "bold"), 
                             relief="flat", command=self.save_settings_ui)
        btn_save.pack(fill=tk.X, ipady=10)

    def save_settings_ui(self):
        from config import save_settings
        from tkinter import messagebox
        
        try:
            new_count = int(self.ent_cam_count.get())
            new_w = int(self.ent_cam_width.get())
            new_h = int(self.ent_cam_height.get())
            new_local = self.ent_local_path.get().strip()
            new_remote = self.ent_remote_path.get().strip()
            
            new_ips = {}
            for i, ent in self.ip_entries.items():
                val = ent.get().strip()
                if val:
                    new_ips[str(i)] = val
            
            payload = {
                "camera_count": new_count,
                "camera_width": new_w,
                "camera_height": new_h,
                "local_temp_buffer": new_local,
                "remote_server_storage": new_remote,
                "camera_ips": new_ips
            }
            
            success = save_settings(payload)
            if success:
                messagebox.showinfo("Success", "Settings Saved!\n\nPlease restart application.")
            else:
                messagebox.showerror("Error", "Failed to save settings.")
                
        except ValueError:
            messagebox.showerror("Invalid Input", "Please check numeric fields.")

    def setup_bindings(self):
        self.root.bind("<space>", lambda e: self.btn_snap.invoke() if self.btn_snap.winfo_viewable() else None)
        self.root.bind("<Return>", lambda e: self.btn_confirm.invoke() if self.btn_confirm.winfo_viewable() else None)
        self.root.bind("<Escape>", lambda e: self.btn_retake.invoke() if self.btn_retake.winfo_viewable() else None)

    def handle_snap(self):
        try:
            if self.notebook.index("current") != 0: return
        except: pass
        
        self.btn_snap.grid_remove()
        self.btn_retake.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=20)
        self.btn_confirm.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=20)
        if self.on_snap_cb: self.on_snap_cb()

    def handle_retake(self):
        try:
            if self.notebook.index("current") != 0: return
        except: pass
        
        self.btn_retake.grid_remove()
        self.btn_confirm.grid_remove()
        self.btn_snap.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)
        if self.on_retake_cb: self.on_retake_cb()

    def handle_confirm(self):
        try:
            if self.notebook.index("current") != 0: return
        except: pass
        
        self.btn_retake.grid_remove()
        self.btn_confirm.grid_remove()
        self.btn_snap.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=20)
        if self.on_confirm_cb: self.on_confirm_cb()

    def update_camera_status(self, index, status_code):
        color_map = {
            0: self.colors["border"],     # OFF
            1: self.colors["success"],    # READY
            2: self.colors["warning"],    # BUSY
            3: self.colors["accent"],     # OK
            4: self.colors["danger"],     # ERR
            5: self.colors["text_dim"]    # REVIEW
        }
        text_map = {0: "OFF", 1: "READY", 2: "BUSY", 3: "OK", 4: "ERR", 5: "REVIEW"}
        
        color = color_map.get(status_code, "white")
        text = text_map.get(status_code, "???")
        # Black text for yellow (BUSY), white for others
        fg_color = "black" if status_code == 2 else "white"
        
        self.root.after(0, lambda: self._set_cam_label(index, text, color, fg_color))

    def _set_cam_label(self, index, text, bg_color, fg_color):
        if 0 <= index < len(self.cam_labels):
            self.cam_labels[index].config(text=text, bg=bg_color, fg=fg_color) 

    def update_camera_image(self, index, pil_image):
        self.root.after(0, lambda: self._set_cam_image(index, pil_image))

    def _set_cam_image(self, index, pil_image):
        if 0 <= index < len(self.cam_canvases):
            self.original_images[index] = pil_image
            self._redraw_canvas(index)

    def on_canvas_resize(self, event, index):
        self._redraw_canvas(index)

    def _redraw_canvas(self, index):
        canvas = self.cam_canvases[index]
        img_pil = self.original_images[index]
        if img_pil is None: return
        
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw < 2 or ch < 2: return 

        img_w, img_h = img_pil.size
        ratio = min(cw/img_w, ch/img_h)
        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)
        
        resized = img_pil.resize((new_w, new_h), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(resized)
        
        self.tk_images[index] = tk_img
        canvas.delete("all")
        canvas.create_image(cw//2, ch//2, anchor=tk.CENTER, image=tk_img)

    def show_enlarged_image(self, index):
        if index < 0 or index >= len(self.original_images) or self.original_images[index] is None: return
        top = Toplevel(self.root, bg="black")
        top.attributes('-fullscreen', True)
        img = self.original_images[index]
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        ratio = min(screen_w/img.size[0], screen_h/img.size[1])
        new_size = (int(img.size[0]*ratio), int(img.size[1]*ratio))
        tk_img = ImageTk.PhotoImage(img.resize(new_size, Image.Resampling.LANCZOS))
        lbl = tk.Label(top, image=tk_img, bg="black")
        lbl.image = tk_img
        lbl.pack(expand=True) 
        top.bind("<Button-1>", lambda e: top.destroy())
        top.bind("<Escape>", lambda e: top.destroy())

    def update_upload_count(self, count):
        self.root.after(0, lambda: self.upload_count_var.set(f"Upload Queue: {count}"))
