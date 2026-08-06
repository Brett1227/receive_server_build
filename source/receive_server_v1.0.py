# -*- coding: utf-8 -*-
"""
扫码直连 · 文件接收服务器（屏幕二维码版）
功能：
  1. 启动后弹出一个窗口，大屏幕显示二维码 + 上传地址
  2. 同事手机连上电脑 WiFi 热点，扫屏幕上的二维码即可上传文件
  3. 文件保存到指定目录（目录会被记住，下次启动沿用）
  4. 文件到电脑后即可自行打印，无需其他操作
  5. 全程局域网直连，不经过互联网，适合隔离/无外网环境

用法：
  receive_server.exe                          # 双击运行（无黑窗口，只有二维码窗口）
  receive_server.exe "D:\\打印材料"           # （可选）启动时指定保存目录
  python receive_server.py                    # 源码方式运行

提示：运行中点击窗口里的【修改…】按钮即可随时更改保存位置，会自动记住。
"""
import os
import sys
import json
import time
import queue
import socket
import threading
import urllib.parse
import http.server

# ---------------------------------------------------------------- 基础配置
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)      # exe 所在目录
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
DEFAULT_DIR = os.path.join(BASE_DIR, "received")
PORT = 8080
MAX_SIZE = 500 * 1024 * 1024          # 单个文件上限 500MB
CHUNK = 64 * 1024                     # 写入分块 64KB

# 打包为无控制台窗口（--windowed）后 stdout/stderr 为 None，
# 必须重定向，否则 print 会报错导致程序闪退。stderr 写入 error.log 便于排查。
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    try:
        sys.stderr = open(os.path.join(BASE_DIR, "error.log"), "w", encoding="utf-8")
    except Exception:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
# Windows 控制台可能默认 GBK，强制 UTF-8 避免中文日志报错
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ---------------------------------------------------------------- 配置读写
def load_config():
    cfg = {"save_dir": DEFAULT_DIR}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if saved.get("save_dir"):
                cfg["save_dir"] = saved["save_dir"]
        except Exception:
            pass
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def safe_name(name):
    """去掉路径部分，只保留文件名，防止路径穿越"""
    name = os.path.basename(name.replace("\\", "/")).strip()
    return name or "unnamed"


def unique_path(directory, name):
    """同名文件自动加 (1)、(2) 后缀，不覆盖旧文件"""
    base, ext = os.path.splitext(name)
    target = os.path.join(directory, name)
    i = 1
    while os.path.exists(target):
        target = os.path.join(directory, f"{base} ({i}){ext}")
        i += 1
    return target


def get_best_ip():
    """找出手机最可能访问到的本机 IP：优先移动热点网段 192.168.137.x"""
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith("192.168.137."):
                return ip
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip.startswith(("10.", "172.", "192.168.")) and not ip.startswith("169."):
                return ip
    except Exception:
        pass
    return "192.168.137.1"


# ---------------------------------------------------------------- 上传页面
PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>上传到打印机主机</title>
<style>
body{font-family:system-ui,-apple-system,'Microsoft YaHei',sans-serif;background:#eef1f5;margin:0;padding:16px;color:#222}
.card{max-width:460px;margin:40px auto;background:#fff;border-radius:16px;padding:28px;box-shadow:0 2px 12px rgba(0,0,0,.08)}
h1{font-size:20px;margin:0 0 6px}
.sub{color:#8a8f98;font-size:13px;margin-bottom:16px}
input[type=file]{display:block;width:100%;padding:14px;border:1.5px dashed #b9c2cd;border-radius:10px;box-sizing:border-box;background:#fafbfc;font-size:14px;margin-top:10px}
.txt{display:block;width:100%;padding:12px;border:1px solid #c9d2db;border-radius:10px;box-sizing:border-box;background:#fafbfc;font-size:14px;margin-top:10px}
.txt:focus{outline:none;border-color:#185fa5;background:#fff}
.btn{display:block;width:100%;padding:14px;border:none;border-radius:10px;background:#185fa5;color:#fff;font-size:16px;cursor:pointer;margin-top:16px}
.btn:disabled{background:#b8c6d6;cursor:not-allowed}
.status{margin-top:16px;font-size:14px;line-height:1.6;word-break:break-all}
.ok{color:#0f6e56}
.err{color:#a32d2d}
.dir{font-size:13px;color:#5f656d;margin-top:16px;background:#f0f2f5;padding:10px 12px;border-radius:8px;word-break:break-all}
details.help{margin-top:16px;border:1px solid #e3d8b8;background:#fdf8ec;border-radius:10px;padding:10px 14px}
details.help summary{cursor:pointer;font-size:13px;color:#854f0b;font-weight:500}
details.help .body{font-size:13px;color:#5f5a4a;line-height:1.7;margin-top:10px}
details.help .body h4{margin:10px 0 4px;font-size:13px;color:#633806}
details.help ol{margin:4px 0 8px;padding-left:20px}
details.help li{margin:3px 0}
</style>
</head>
<body>
<div class="card">
<h1>上传文件到打印机主机</h1>
<div class="sub">文件经 WiFi 直连传输，不经过互联网</div>
<details class="help" id="help">
<summary>微信里收的文件找不到？点这里看导出方法（30秒搞定）</summary>
<div class="body">
<h4>Android（Word、PDF 等文档）</h4>
<ol>
<li>微信里<strong>点开</strong>那个文件，等它打开</li>
<li>点右上角 <strong>···</strong>，点 <strong>保存</strong></li>
<li>回到本页，选文件时在 <strong>最近 / 下载</strong> 里就能看到</li>
</ol>
<h4>iPhone（Word、PDF 等文档）</h4>
<ol>
<li>微信里<strong>点开</strong>文件</li>
<li>点右上角 <strong>···</strong>，点 <strong>用其他应用打开</strong></li>
<li>点 <strong>存储到"文件"</strong>，选好位置后点 <strong>存储</strong></li>
<li>如果当前位置是 <strong>iCloud 云盘</strong>，先点 <strong>浏览</strong>，在"位置"里选 <strong>我的 iPhone</strong>，再存储（这样才存到手机本地）</li>
<li>回到本页选文件时，进 <strong>文件</strong> App 里刚保存的位置</li>
</ol>
<h4>图片 / 照片（通用）</h4>
<ol>
<li>微信里<strong>长按图片 → 保存到相册</strong></li>
<li>回到本页选择文件时，选 <strong>相册 / 图片</strong> 里的这张图</li>
</ol>
</div>
</details>
<input type="text" id="dept" class="txt" placeholder="上传人部门（必填）">
<input type="text" id="user" class="txt" placeholder="上传人姓名（必填）">
<input type="file" id="f" multiple>
<button class="btn" id="b" onclick="up()">开始上传</button>
<div class="dir" id="dir">保存目录：读取中…</div>
<div class="status" id="s"></div>
</div>
<script>
function fmt(n){if(n>1048576)return (n/1048576).toFixed(1)+' MB';if(n>1024)return (n/1024).toFixed(1)+' KB';return n+' B'}
async function up(){
  var dept=document.getElementById('dept').value.trim();
  var user=document.getElementById('user').value.trim();
  if(!dept){alert('请先填写上传人部门');document.getElementById('dept').focus();return}
  if(!user){alert('请先填写上传人姓名');document.getElementById('user').focus();return}
  var files=document.getElementById('f').files;
  if(!files.length){alert('请先选择要上传的文件');return}
  var b=document.getElementById('b');b.disabled=true;
  var s=document.getElementById('s');
  for(var i=0;i<files.length;i++){
    var f=files[i];
    s.className='status';s.textContent='正在上传 '+(i+1)+'/'+files.length+'：'+f.name+'（'+fmt(f.size)+'）…';
    try{
      var r=await fetch('/upload?name='+encodeURIComponent(f.name)+'&dept='+encodeURIComponent(dept)+'&user='+encodeURIComponent(user),{method:'POST',body:f});
      var j=await r.json();
      if(r.ok){s.className='status ok';s.textContent='✓ 已保存：'+f.name+'（'+j.path+'）'}
      else{s.className='status err';s.textContent='✗ 失败：'+f.name+'（'+(j.error||r.status)+'）'}
    }catch(e){
      s.className='status err';s.textContent='✗ 连接失败：'+f.name+'（'+e.message+'）';b.disabled=false;return;
    }
  }
  s.className='status ok';s.textContent='全部上传完成，共 '+files.length+' 个文件。';
  document.getElementById('f').value='';
  b.disabled=false;
}
fetch('/dir').then(function(r){return r.json()}).then(function(j){document.getElementById('dir').textContent='保存目录：'+j.dir}).catch(function(){});
</script>
</body>
</html>"""


# ---------------------------------------------------------------- 日志通道（跨线程）
log_queue = queue.Queue()
_last_folder_open = [0.0]   # 打开文件夹节流：批量上传时避免连续弹多个窗口
RECORDS_FILE = os.path.join(BASE_DIR, "上传记录.xlsx")
records_lock = threading.Lock()


def append_record(info):
    """把上传记录追加到 Excel 表格（.xlsx，预设列宽，打开不会出现 #######）"""
    with records_lock:
        try:
            from openpyxl import Workbook, load_workbook
            if os.path.exists(RECORDS_FILE):
                wb = load_workbook(RECORDS_FILE)
                ws = wb.active
            else:
                wb = Workbook()
                ws = wb.active
                ws.title = "上传记录"
                ws.append(["上传时间", "部门", "姓名", "文件名", "保存路径"])
                ws.column_dimensions["A"].width = 22   # 上传时间
                ws.column_dimensions["B"].width = 14   # 部门
                ws.column_dimensions["C"].width = 12   # 姓名
                ws.column_dimensions["D"].width = 34   # 文件名
                ws.column_dimensions["E"].width = 55   # 保存路径
            ws.append([info["time"], info["dept"], info["user"],
                       info["name"], info["path"]])
            wb.save(RECORDS_FILE)
        except Exception as e:
            print(f"写入上传记录失败：{e}")


def notify_file(info):
    """把"新文件"事件推给界面线程；同时打印到控制台"""
    log_queue.put(("file", info))
    print(f"[{info['time']}] 收到文件：{info['name']}（{info['size_mb']:.2f} MB）")


def request_open_folder(path):
    """请求主线程打开资源管理器（5 秒内只打开一次）"""
    now = time.time()
    if now - _last_folder_open[0] < 5:
        return
    _last_folder_open[0] = now
    log_queue.put(("open_folder", path))


# ---------------------------------------------------------------- HTTP 处理
class Handler(http.server.BaseHTTPRequestHandler):
    cfg = load_config()
    received_count = 0

    def log_message(self, *args):
        pass  # 关闭默认访问日志

    def _send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/dir":
            self._send_json({"dir": self.cfg["save_dir"]})
        else:
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path != "/upload":
            self._send_json({"error": "接口不存在"}, 404)
            return
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        name = safe_name(qs.get("name", ["unnamed"])[0])
        dept = qs.get("dept", [""])[0].strip()
        user = qs.get("user", [""])[0].strip()
        if not dept or not user:
            self._send_json({"error": "缺少上传人部门或姓名，请填写完整"}, 400)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            length = 0
        if length <= 0:
            self._send_json({"error": "文件为空或请求异常"}, 400)
            return
        if length > MAX_SIZE:
            self._send_json({"error": "文件超过 500MB 上限"}, 413)
            return

        directory = self.cfg["save_dir"]
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            self._send_json({"error": f"无法创建保存目录：{e}"}, 500)
            return

        dest = unique_path(directory, name)
        try:
            with open(dest, "wb") as f:
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(CHUNK, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)
        except Exception as e:
            self._send_json({"error": f"写入失败：{e}"}, 500)
            return

        Handler.received_count += 1
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        size_mb = length / 1024 / 1024
        info = {
            "time": stamp,
            "name": name,
            "path": dest,
            "size_mb": size_mb,
            "seq": Handler.received_count,
            "dept": dept,
            "user": user,
        }
        append_record(info)
        notify_file(info)
        request_open_folder(directory)
        self._send_json({"ok": True, "path": dest, "size": length})


# ---------------------------------------------------------------- 二维码生成
def make_qr_png(text, box=380):
    """生成二维码 PIL 图片（失败时返回 None）"""
    try:
        import qrcode
        from PIL import Image
        qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img = img.resize((box, box), Image.LANCZOS)
        return img
    except Exception:
        return None


# ---------------------------------------------------------------- 打包自检
def run_self_test():
    """无界面验证打包依赖；供 CI 在没有交互桌面的环境中调用。"""
    import io
    import tkinter as tk
    from openpyxl import Workbook

    # Tcl() 不创建可见窗口，但会加载打包后的 Tcl 运行库和 init.tcl。
    interp = tk.Tcl()
    patchlevel = interp.call("info", "patchlevel")
    if not patchlevel:
        raise RuntimeError("Tcl/Tk 运行库初始化失败")

    qr_img = make_qr_png("http://127.0.0.1:8080", box=128)
    if qr_img is None or qr_img.size != (128, 128):
        raise RuntimeError("二维码/Pillow 自检失败")

    workbook = Workbook()
    workbook.active.append(["time", "department", "user", "file"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    if buffer.tell() <= 0:
        raise RuntimeError("openpyxl 自检失败")


# ---------------------------------------------------------------- 界面窗口
def run_gui(ip, port):
    """主线程运行 tkinter 窗口，返回后程序结束"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        from PIL import ImageTk
    except Exception as e:
        print(f"界面初始化失败（{e}），请通过浏览器访问 http://{ip}:{port}")
        return

    def current_dir():
        return Handler.cfg["save_dir"]

    root = tk.Tk()
    root.title("扫码上传 · 打印机主机")
    root.configure(bg="white")
    root.resizable(True, True)

    # Tk 会按 Windows 当前 DPI 缩放报告逻辑分辨率。窗口尺寸必须基于这里的
    # 实际可用逻辑尺寸计算，不能假定所有电脑都有 720px 以上的可用高度。
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    compact = screen_h < 800 or screen_w < 1100

    window_w = min(720, max(460, int(screen_w * 0.62)))
    window_h = min(900, max(520, int(screen_h * 0.88)))
    window_w = min(window_w, max(420, screen_w - 40))
    window_h = min(window_h, max(480, screen_h - 80))
    pos_x = max(0, (screen_w - window_w) // 2)
    pos_y = max(0, (screen_h - window_h) // 2)
    root.geometry(f"{window_w}x{window_h}+{pos_x}+{pos_y}")
    root.minsize(min(420, screen_w), min(480, screen_h))

    # 内容可能高于小屏幕的可用高度。Canvas + Scrollbar 保证任何分辨率、
    # 任何窗口状态下都能滚动到最下面的“打开上传记录”按钮。
    shell = tk.Frame(content, bg="white")
    shell.pack(fill="both", expand=True)
    canvas = tk.Canvas(shell, bg="white", highlightthickness=0)
    scrollbar = tk.Scrollbar(shell, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    content = tk.Frame(canvas, bg="white")
    content_window = canvas.create_window((0, 0), window=content, anchor="nw")

    def sync_scroll_region(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def fit_content_width(event):
        canvas.itemconfigure(content_window, width=event.width)

    def scroll_content(event):
        # Windows 的 event.delta 通常为 120 的倍数；触控板也可能给出较小值。
        step = -1 if event.delta > 0 else 1
        canvas.yview_scroll(step * 3, "units")
        return "break"

    content.bind("<Configure>", sync_scroll_region)
    canvas.bind("<Configure>", fit_content_width)
    canvas.bind("<MouseWheel>", scroll_content)
    content.bind("<MouseWheel>", scroll_content)
    # bind_all 让鼠标位于标签、二维码、按钮等子控件上时也能滚动整页。
    root.bind_all("<MouseWheel>", scroll_content, add="+")

    FONT_TITLE = ("Microsoft YaHei", 16 if compact else 18, "bold")
    FONT_SUB = ("Microsoft YaHei", 12)
    FONT_INFO = ("Microsoft YaHei", 11)
    COLOR_SUB = "#666666"
    COLOR_OK = "#0f6e56"

    tk.Label(content, text="扫码上传到打印机主机", font=FONT_TITLE,
             bg="white", fg="#185fa5").pack(pady=(24, 2))
    tk.Label(content, text="连接电脑热点后，扫下方二维码上传文件",
             font=FONT_SUB, bg="white", fg=COLOR_SUB).pack(pady=(0, 4))
    # WiFi 热点名称 + 密码（醒目提示）
    tk.Label(content, text="WiFi 热点名称：打印机主机连接",
             font=("Microsoft YaHei", 14, "bold"),
             bg="white", fg="#b25e00").pack(pady=(0, 2))
    tk.Label(content, text="WiFi 热点密码：73556088",
             font=("Microsoft YaHei", 14, "bold"),
             bg="white", fg="#b25e00").pack(pady=(0, 10))

    # 二维码
    qr_size = max(210, min(380, int(screen_h * (0.34 if compact else 0.38))))
    qr_img = make_qr_png(f"http://{ip}:{port}", box=qr_size)
    if qr_img is not None:
        photo = ImageTk.PhotoImage(qr_img)
        tk.Label(content, image=photo, bg="white").pack(pady=6)
        root._qr_photo = photo  # 防止被 GC
    else:
        tk.Label(content, text="（二维码生成失败，请用下方地址）",
                 font=FONT_SUB, bg="white", fg="#a32d2d").pack(pady=6)

    # 上传地址
    url_text = f"http://{ip}:{port}"
    tk.Label(content, text="上传地址（也可手动输入）", font=("Microsoft YaHei", 10),
             bg="white", fg=COLOR_SUB).pack()
    url_label = tk.Label(content, text=url_text, font=("Consolas", 15, "bold"),
                         bg="white", fg="#185fa5", cursor="hand2")
    url_label.pack(pady=(2, 10))
    url_label.bind("<Button-1>", lambda e: copy_text(url_text))

    # 保存目录 + 修改按钮
    dir_frame = tk.Frame(content, bg="#f0f2f5")
    dir_frame.pack(fill="x", padx=36, pady=4)
    tk.Label(dir_frame, text="保存目录：", font=FONT_INFO,
             bg="#f0f2f5", fg=COLOR_SUB).pack(side="left", padx=(10, 0), pady=8)
    dir_value = tk.Label(dir_frame, text=current_dir(), font=("Consolas", 10),
                         bg="#f0f2f5", fg="#333333", wraplength=max(180, window_w - 300),
                         justify="left")
    dir_value.pack(side="left", pady=8, padx=4)

    def styled_button(parent, text, command):
        """带悬停/按下动效的按钮"""
        btn = tk.Button(parent, text=text, font=("Microsoft YaHei", 10),
                        command=command, bg="#185fa5", fg="white", relief="flat",
                        activebackground="#0f4d84", activeforeground="white",
                        cursor="hand2", padx=12, pady=2)
        btn.bind("<Enter>", lambda e: btn.configure(bg="#2a74bd"))
        btn.bind("<Leave>", lambda e: btn.configure(bg="#185fa5"))
        return btn

    def change_dir():
        d = filedialog.askdirectory(initialdir=current_dir(), title="选择文件保存位置")
        if not d:
            return
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            try:
                import tkinter.messagebox as mb
                mb.showerror("无法创建目录", str(e))
            except Exception:
                pass
            return
        Handler.cfg["save_dir"] = d
        save_config(Handler.cfg)
        dir_value.configure(text=d)

    styled_button(dir_frame, "修改…", change_dir).pack(side="right", padx=10, pady=6)

    # 已接收文件列表（点击文件名打开）
    tk.Label(content, text="已接收文件（点击文件名打开）", font=("Microsoft YaHei", 10),
             bg="white", fg=COLOR_SUB).pack(pady=(14, 2))
    log_box = tk.Text(content, height=4 if compact else 6, font=("Microsoft YaHei", 10),
                      bg="#fafbfc", fg="#333333", relief="flat",
                      state="disabled", wrap="word", cursor="hand2")
    log_box.pack(fill="both", expand=True, padx=36, pady=(2, 6))
    log_box.tag_configure("file", foreground="#185fa5", underline=True)

    tk.Label(content, text="点击文件名可打开文件 · 点【修改…】可更改保存位置",
             font=("Microsoft YaHei", 9), bg="white", fg="#999999").pack(pady=(0, 6))

    # 打开上传记录按钮
    def open_records():
        if os.path.exists(RECORDS_FILE):
            try:
                os.startfile(RECORDS_FILE)
            except Exception:
                pass
        else:
            try:
                import tkinter.messagebox as mb
                mb.showinfo("暂无记录", "还没有上传记录，等同事上传文件后这里会出现表格。")
            except Exception:
                pass

    btn_row = tk.Frame(content, bg="white")
    btn_row.pack(pady=(0, 12))
    styled_button(btn_row, "打开上传记录", open_records).pack(side="left", padx=8)

    def copy_text(text):
        root.clipboard_clear()
        root.clipboard_append(text)
        url_label.configure(text=url_text + "  （已复制）")
        root.after(1500, lambda: url_label.configure(text=url_text))

    def open_path(path):
        try:
            os.startfile(path)
        except Exception:
            pass

    def append_file(info):
        log_box.configure(state="normal")
        short = info["time"][11:] if len(info["time"]) >= 11 else info["time"]
        line = f"{short}  {info['name']}\n"
        start = log_box.index("insert")
        log_box.insert("end", line)
        end = log_box.index("end-1c")
        tag = f"f{info['seq']}"
        log_box.tag_add(tag, start, end)
        log_box.tag_bind(tag, "<Button-1>", lambda e, p=info["path"]: open_path(p))
        log_box.see("end")
        log_box.configure(state="disabled")

    def poll_log():
        try:
            while True:
                msg = log_queue.get_nowait()
                if msg[0] == "file":
                    append_file(msg[1])
                elif msg[0] == "open_folder":
                    try:
                        os.startfile(msg[1])
                    except Exception:
                        pass
        except queue.Empty:
            pass
        root.after(200, poll_log)

    def on_close():
        root.unbind_all("<MouseWheel>")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.after(200, poll_log)
    root.after_idle(sync_scroll_region)
    root.after_idle(lambda: canvas.yview_moveto(0))
    root.mainloop()


# ---------------------------------------------------------------- 启动入口
def main():
    save_dir = None
    args = sys.argv[1:]
    if "--self-test" in args:
        run_self_test()
        return
    if args and args[0].startswith("--dir"):
        save_dir = args[1] if len(args) > 1 else None
    elif args:
        save_dir = args[0]

    if save_dir:
        save_dir = os.path.abspath(os.path.expanduser(save_dir))
        Handler.cfg["save_dir"] = save_dir
        save_config(Handler.cfg)
        print(f"已设置保存目录：{save_dir}（已记住，下次启动继续使用）")

    directory = Handler.cfg["save_dir"]
    try:
        os.makedirs(directory, exist_ok=True)
    except Exception as e:
        print(f"警告：无法创建保存目录 {directory}（{e}），已改回默认目录")
        directory = DEFAULT_DIR
        os.makedirs(directory, exist_ok=True)
        Handler.cfg["save_dir"] = directory

    try:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    except OSError as e:
        # 无黑窗口时看不到报错，改用弹窗提示
        msg = f"启动失败：{e}\n\n可能程序已在运行，或端口 {PORT} 被占用。\n请关闭已打开的程序后重试。"
        try:
            import tkinter.messagebox as mb
            mb.showerror("启动失败", msg)
        except Exception:
            print(msg)
        return

    threading.Thread(target=server.serve_forever, daemon=True).start()
    ip = get_best_ip()

    print("=" * 52)
    print("  扫码直连 · 文件接收服务器已启动")
    print("=" * 52)
    print(f"  手机上传地址：http://{ip}:{PORT}")
    print(f"  保存目录：{directory}")
    print("  程序窗口已弹出，请让同事扫屏幕上的二维码")
    print("  按窗口右上角 X 关闭程序")
    print("=" * 52)

    run_gui(ip, PORT)
    server.shutdown()


if __name__ == "__main__":
    main()
