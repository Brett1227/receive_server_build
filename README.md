# receive_server_build

扫码直连文件接收系统（receive_server）的**可维护工程仓库**。
仓库保存需求 Prompt、开发文档、源代码与使用说明；编译后的 Windows 可执行文件统一通过 [GitHub Releases](https://github.com/Brett1227/receive_server_build/releases) 发布。

## 下载与校验

最新正式版本：[receive_server v1.2](https://github.com/Brett1227/receive_server_build/releases/tag/v1.2)

- 可执行文件：[receive_server_v1.2.exe](https://github.com/Brett1227/receive_server_build/releases/download/v1.2/receive_server_v1.2.exe)
- 文件大小：21,241,874 字节（约 20.3 MB）
- SHA-256：`ACE6D7CF41899E264BED061C75E87EA2F4A16801BB018E6D977206474156A8DE`

请只从本仓库的 Releases 下载，并在部署前核对 SHA-256。Windows 可能对未签名程序显示安全提示。

## 目录结构

```
receive_server_build/
├── requirements_prompt.md              ★ 可复现需求的完整 Prompt
│                                        （复制给任意 AI 即可从零重建整个系统）
├── docs/
│   └── receive_server_v1.0开发文档.md   ★ 需求演进记录（R1~R11）+ 技术要点 + 踩坑
└── source/
    ├── receive_server_v1.0.py           ★ 最新源代码（可改可维护）
    └── 使用说明.txt                     ★ 主机端操作教程
```

可执行文件不提交到 Git 仓库，统一作为版本附件保存在 Releases 中。

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
| **部署到主机** | 从 Releases 下载 `receive_server_v1.2.exe`，同时参考 `source/使用说明.txt` |

## 打包环境（复现用）

- Python 3.14（必须自带 tkinter）
- 依赖：`qrcode`、`pillow`、`openpyxl`、`pyinstaller`
- 命令：`pyinstaller --onefile --windowed --name receive_server receive_server.py`
- 产物约 19MB；运行时文件（config.json / received / 上传记录.xlsx）都生成在 exe 旁边

## 发布约定

1. 源代码、文档和构建说明提交到仓库。
2. 编译后的 `.exe`、安装包和压缩包上传到对应版本的 Release。
3. Release 说明中记录 SHA-256；如以后配置代码签名，同时记录签名信息。
4. 每次正式发布创建独立版本标签，避免覆盖已有资产。

## 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| [v1.2](https://github.com/Brett1227/receive_server_build/releases/tag/v1.2) | 2026-08-13 | 修复 GUI 启动崩溃；增加打包后 GUI 启动烟雾测试 |\n| [v1.1](https://github.com/Brett1227/receive_server_build/releases/tag/v1.1) | 2026-08-06 | 修复不同分辨率和 Windows 缩放比例下的窗口显示；增加页面滚动与打包自检 |
| [v1.0](https://github.com/Brett1227/receive_server_build/releases/tag/v1.0) | 2026-08-05 | 完整实现 R1~R11 全部需求（见开发文档） |
