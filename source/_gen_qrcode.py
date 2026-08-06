# -*- coding: utf-8 -*-
"""
生成带说明文字的打印版二维码（备用工具）
用途：在联网环境跑一次，生成可打印张贴的二维码图片（早期版本用；新版程序启动时会在屏幕动态生成二维码，本脚本仅作为备用）。
"""
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

OUT = r"C:\Users\Brett\WorkBuddy\receive_server_build\source"
URL = "http://192.168.137.1:8080"
TITLE = "扫码上传文件到打印机主机"
SUBTITLE = "手机需先连接电脑的移动热点，再扫此码"
BOTTOM = "上传地址：" + URL

W, H = 640, 860
img = Image.new("RGB", (W, H), "white")
draw = ImageDraw.Draw(img)

font_path = r"C:\Windows\Fonts\msyh.ttc"
def font(size):
    return ImageFont.truetype(font_path, size)

def center_text(y, text, f, fill=(30, 30, 30)):
    w = draw.textlength(text, font=f)
    draw.text(((W - w) / 2, y), text, font=f, fill=fill)

center_text(46, TITLE, font(30), (24, 68, 121))
center_text(100, SUBTITLE, font(18), (120, 120, 120))

qr = qrcode.QRCode(border=4, error_correction=qrcode.constants.ERROR_CORRECT_M)
qr.add_data(URL)
qr.make(fit=True)
qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
qr_size = 480
qr_img = qr_img.resize((qr_size, qr_size), Image.NEAREST)
img.paste(qr_img, ((W - qr_size) // 2, 150))

center_text(665, BOTTOM, font(24), (30, 30, 30))
center_text(730, "电脑上运行 receive_server.py 后即可使用", font(16), (150, 150, 150))

path = os.path.join(OUT, "上传二维码.png")
img.save(path, "PNG")
print("saved:", path)
