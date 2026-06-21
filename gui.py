import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import json
from urllib.parse import urlparse

class TranslatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("翻译插件控制台")
        self.root.geometry("600x600")
        self.root.resizable(True, True)

        self.llama_process = None
        self.flask_process = None

        self.create_widgets()
        self.load_config()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # llama-server 路径
        ttk.Label(main_frame, text="llama-server 路径:").pack(anchor=tk.W)
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=(0, 5))
        self.llama_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.llama_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="浏览", command=self.browse_llama).pack(side=tk.LEFT, padx=(5, 0))

        # GGUF 模型文件
        ttk.Label(main_frame, text="GGUF 模型文件:").pack(anchor=tk.W)
        model_frame = ttk.Frame(main_frame)
        model_frame.pack(fill=tk.X, pady=(0, 5))
        self.model_path_var = tk.StringVar()
        ttk.Entry(model_frame, textvariable=self.model_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(model_frame, text="浏览", command=self.browse_model).pack(side=tk.LEFT, padx=(5, 0))

        # 参数区
        params_frame = ttk.LabelFrame(main_frame, text="模型参数", padding=5)
        params_frame.pack(fill=tk.X, pady=(0, 5))

        row1 = ttk.Frame(params_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="GPU层数:").pack(side=tk.LEFT)
        self.ngl_var = tk.StringVar(value="100")
        ttk.Entry(row1, textvariable=self.ngl_var, width=8).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(row1, text="温度:").pack(side=tk.LEFT)
        self.temp_var = tk.StringVar(value="0.7")
        ttk.Entry(row1, textvariable=self.temp_var, width=8).pack(side=tk.LEFT)

        row2 = ttk.Frame(params_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Top-P:").pack(side=tk.LEFT)
        self.top_p_var = tk.StringVar(value="0.6")
        ttk.Entry(row2, textvariable=self.top_p_var, width=8).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(row2, text="Top-K:").pack(side=tk.LEFT)
        self.top_k_var = tk.StringVar(value="20")
        ttk.Entry(row2, textvariable=self.top_k_var, width=8).pack(side=tk.LEFT)

        row3 = ttk.Frame(params_frame)
        row3.pack(fill=tk.X, pady=2)
        ttk.Label(row3, text="重复惩罚:").pack(side=tk.LEFT)
        self.repeat_var = tk.StringVar(value="1.05")
        ttk.Entry(row3, textvariable=self.repeat_var, width=8).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(row3, text="最大Token:").pack(side=tk.LEFT)
        self.n_var = tk.StringVar(value="4096")
        ttk.Entry(row3, textvariable=self.n_var, width=8).pack(side=tk.LEFT)

        # 端口设置
        port_frame = ttk.Frame(main_frame)
        port_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(port_frame, text="llama-server 端口:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value="8080")
        ttk.Entry(port_frame, textvariable=self.port_var, width=8).pack(side=tk.LEFT, padx=(5, 0))

        # 按钮区
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 5))
        self.start_llama_btn = ttk.Button(btn_frame, text="启动 llama-server", command=self.start_llama)
        self.start_llama_btn.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.start_flask_btn = ttk.Button(btn_frame, text="启动翻译服务", command=self.start_flask, state=tk.DISABLED)
        self.start_flask_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.stop_btn = ttk.Button(main_frame, text="停止所有服务", command=self.stop_all)
        self.stop_btn.pack(fill=tk.X, pady=(0, 5))

        self.status_var = tk.StringVar(value="状态: 等待启动...")
        ttk.Label(main_frame, textvariable=self.status_var, foreground="gray").pack(anchor=tk.W)

        # 控制台输出区
        console_frame = ttk.LabelFrame(main_frame, text="控制台输出", padding=5)
        console_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.console = scrolledtext.ScrolledText(
            console_frame,
            height=12,
            state=tk.DISABLED,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#d4d4d4"
        )
        self.console.pack(fill=tk.BOTH, expand=True)

    def log(self, msg, tag="info"):
        """向控制台追加一行"""
        self.console.config(state=tk.NORMAL)
        self.console.insert(tk.END, msg + "\n", tag)
        self.console.see(tk.END)
        self.console.config(state=tk.DISABLED)

    def browse_llama(self):
        path = filedialog.askopenfilename(
            title="选择 llama-server.exe",
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]
        )
        if path:
            self.llama_path_var.set(path)

    def browse_model(self):
        path = filedialog.askopenfilename(
            title="选择 GGUF 模型文件",
            filetypes=[("GGUF模型", "*.gguf"), ("所有文件", "*.*")]
        )
        if path:
            self.model_path_var.set(path)

    def load_config(self):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            base_url = config.get("api_keys", {}).get("llama", {}).get("base_url", "http://127.0.0.1:8080/v1")
            parsed = urlparse(base_url)
            if parsed.port:
                self.port_var.set(str(parsed.port))
        except Exception:
            pass

    def start_llama(self):
        llama_path = self.llama_path_var.get().strip()
        model_path = self.model_path_var.get().strip()

        if not llama_path or not os.path.exists(llama_path):
            messagebox.showerror("错误", "请选择有效的 llama-server.exe 路径")
            return
        if not model_path or not os.path.exists(model_path):
            messagebox.showerror("错误", "请选择有效的 GGUF 模型文件")
            return

        if self.llama_process and self.llama_process.poll() is None:
            messagebox.showwarning("提示", "llama-server 已在运行")
            return

        port = self.port_var.get().strip()
        cmd = [
            llama_path,
            "-m", model_path,
            "-ngl", self.ngl_var.get().strip(),
            "--temp", self.temp_var.get().strip(),
            "--top-p", self.top_p_var.get().strip(),
            "--top-k", self.top_k_var.get().strip(),
            "--repeat-penalty", self.repeat_var.get().strip(),
            "-n", self.n_var.get().strip(),
            "--host", "127.0.0.1",
            "--port", port
        ]

        try:
            self.llama_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            self.status_var.set(f"状态: llama-server 已启动 (PID: {self.llama_process.pid})")
            self.start_llama_btn.config(state=tk.DISABLED)
            self.start_flask_btn.config(state=tk.NORMAL)
            self.log(f"[llama-server] 启动 PID={self.llama_process.pid}", "system")
            threading.Thread(target=self._monitor_llama, daemon=True).start()
        except Exception as e:
            messagebox.showerror("启动失败", str(e))

    def _monitor_llama(self):
        for line in self.llama_process.stdout:
            line = line.rstrip("\n")
            self.root.after(0, self.log, f"[llama] {line}", "llama")
            if "listening" in line.lower() or "server is listening" in line.lower():
                self.root.after(0, lambda: self.status_var.set("状态: llama-server 就绪，可启动翻译服务"))

    def start_flask(self):
        if self.flask_process and self.flask_process.poll() is None:
            messagebox.showwarning("提示", "翻译服务已在运行")
            return

        try:
            self.flask_process = subprocess.Popen(
                [sys.executable, "-u", "run_app.py"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            self.status_var.set(f"状态: 翻译服务已启动 (PID: {self.flask_process.pid})")
            self.start_flask_btn.config(state=tk.DISABLED)
            self.log(f"[Flask] 启动 PID={self.flask_process.pid}", "system")
            threading.Thread(target=self._monitor_flask, daemon=True).start()
        except Exception as e:
            messagebox.showerror("启动失败", str(e))

    def _monitor_flask(self):
        for line in self.flask_process.stdout:
            line = line.rstrip("\n")
            if not line:
                continue
            # 根据内容着色
            if "[原文]" in line:
                tag = "source"
            elif "[译文]" in line:
                tag = "result"
            elif "[错误]" in line or "[警告]" in line:
                tag = "error"
            else:
                tag = "flask"
            self.root.after(0, self.log, f"[Flask] {line}", tag)
            if "服务启动" in line:
                self.root.after(0, lambda: self.status_var.set("状态: 两个服务均已启动，可以使用"))

    def stop_all(self):
        for proc in [self.flask_process, self.llama_process]:
            if proc and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                if proc.stdout:
                    proc.stdout.close()
        self.llama_process = None
        self.flask_process = None
        self.start_llama_btn.config(state=tk.NORMAL)
        self.start_flask_btn.config(state=tk.DISABLED)
        self.status_var.set("状态: 所有服务已停止")
        self.log("[系统] 所有服务已停止", "system")

    def on_closing(self):
        self.stop_all()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TranslatorGUI(root)
    root.mainloop()
