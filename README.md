# receive_server_build

扫码直连文件接收系统（receive_server）的**自包含工程包**。
本目录包含完整的需求 Prompt、开发文档、源代码与可执行文件，
用于**日后继续维护**以及在**任何地方复现需求与代码**。

## 目录结构

```
receive_server_build/
├── requirements_prompt.md          ★ 可复现需求的完整 Prompt
│                                    （复制给任意 AI 即可从零重建整个系统）
├── docs/
│   └── receive_server_v1.0开发文档.md   ★ 需求演进记录（R1~R11）+ 技术要点 + 踩坑
└── source/
    ├── receive_server_v1.0.py       ★ 最新源代码（可改可维护）
    ├── receive_server_v1.0.exe      ★ 最新可执行文件（拷到主机直接用）
    └── 使用说明.txt                  ★ 主机端操作教程
```

## 系统一句话简介

隔离环境 Windows 主机（不能联网）上运行本程序，弹窗显示二维码 + WiFi 热点信息；
同事手机连上热点、扫码后填写部门/姓名（必填），即可把文件经局域网直连传到主机，
自动记录到 Excel 表格（谁、什么时间、传了什么文件），文件到达后同事自行打印。

## 常见用途

| 场景 | 怎么做 |
|---|---|
| **在别处复现需求** | 把 `requirements_prompt.md` 整份发给 AI，让它开发 |
| **继续开发新功能** | 改 `source/receive_server_v1.0.py`，参考开发文档的架构与坑 |
| **重新打包 exe** | 用 Python 3.14（含 tkinter）+ pyinstaller/qrcode/pillow/openpyxl，执行 `pyinstaller --onefile --windowed --name receive_server receive_server.py` |
| **部署到主机** | 只需把 `receive_server_v1.0.exe` + `使用说明.txt` 拷过去，双击运行 |

## 打包环境（复现用）

- Python 3.14（必须自带 tkinter）
- 依赖：`qrcode`、`pillow`、`openpyxl`、`pyinstaller`
- 命令：`pyinstaller --onefile --windowed --name receive_server receive_server.py`
- 产物约 19MB；运行时文件（config.json / received / 上传记录.xlsx）都生成在 exe 旁边

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| v1.0 | 2026-08-05 | 完整实现 R1~R11 全部需求（见开发文档） |
