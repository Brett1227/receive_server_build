# receive_server_build — 项目记忆

## 项目是什么
扫码直连文件接收系统（receive_server）的自包含工程包。
隔离环境 Windows 主机（不能联网）连接特殊打印机 → 同事手机连电脑 WiFi 热点、扫电脑屏幕二维码 → 填部门/姓名（必填）→ 文件经局域网直连传到主机 → 自动记录到 Excel，同事自行打印。

## 关键事实（长期有效）
- 热点名称：打印机主机连接；热点密码：73556088（用户指定固定值，窗口内橙色大字显示）
- 主机不能联网 → 程序打包为单文件 exe（PyInstaller --onefile --windowed），主机免装 Python
- 二维码只传连接地址（http://<IP>:8080，优先 192.168.137.x 热点网段），文件走 HTTP 局域网直连
- 上传记录：上传记录.xlsx（openpyxl，预设列宽 A=22/B=14/C=12/D=34/E=55），表头 时间|部门|姓名|文件名|路径
- 微信文件需先"保存/导出"才能上传（微信私有目录网页无法访问）：Android 走"···→保存"；iPhone 走"···→用其他应用打开→存储到文件"，iCloud 云盘要先点浏览选"我的 iPhone"
- 打包环境：系统 Python 3.14（C:\Python314，含 tkinter）+ qrcode/pillow/openpyxl/pyinstaller，venv 在 C:\Users\Brett\.workbuddy\binaries\python\envs\pack

## 关键工程约定
- sys.frozen 判断 BASE_DIR = exe 所在目录（否则文件写进 _MEIPASS 临时目录丢失）
- windowed 无标准流：stdout 重定向 devnull、stderr 写 error.log
- 跨线程 UI：queue + root.after 轮询，消息元组 ("file", info) / ("open_folder", path)
- 打包前必须确认无 receive_server 进程占用，mv 后验证时间戳/体积
- 同名文件自动加 (1)；单文件上限 500MB

## 目录结构
- requirements_prompt.md —— 可复现需求的完整 Prompt（复制给任意 AI 即可重建）
- docs/receive_server_v1.0开发文档.md —— 需求演进 R1~R11 + 技术要点
- source/ —— receive_server_v1.0.py / .exe / 使用说明.txt

## 状态
- v1.0 已完成全部 R1~R11 需求，用户已实际部署使用（2026-08-05）
- 后续迭代在此项目内继续，新需求在 requirements_prompt.md 追加并更新开发文档
