import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
D="/Users/antonk/artvision-data/clients/usmile/ideas/signage-v5-corner/bakeoff"
GRAPHITE=(29,29,31); WOOD=(178,140,94); WOOD2=(150,115,75)
AB="/System/Library/Fonts/Supplemental/Arial Bold.ttf"
AR="/System/Library/Fonts/Supplemental/Arial.ttf"
def font(p,s): return ImageFont.truetype(p,s)
def qr(data):
    q=qrcode.QRCode(border=2,box_size=10,error_correction=qrcode.constants.ERROR_CORRECT_M)
    q.add_data(data);q.make(fit=True)
    return q.make_image(fill_color=(29,29,31),back_color=(255,255,255)).convert("RGB")
def center(d,txt,f,y,W,fill,maxw=None):
    bb=d.textbbox((0,0),txt,font=f);w=bb[2]-bb[0]
    d.text(((W-w)//2,y),txt,font=f,fill=fill)
    return y+(bb[3]-bb[1])
def stand(tagline,qrdata,outname):
    W,H=720,1000
    img=Image.new("RGB",(W,H),(238,240,243))
    d=ImageDraw.Draw(img)
    # деревянная подставка
    bx0,bx1,by0,by1=180,540,820,900
    d.rectangle([bx0,by0,bx1,by1],fill=WOOD)
    d.rectangle([bx0,by0,bx1,by0+14],fill=WOOD2)
    # оргстекло-панель (матовая)
    px0,px1,py0,py1=150,570,120,840
    panel=Image.new("RGB",(px1-px0,py1-py0),(250,251,252))
    img.paste(panel,(px0,py0))
    d.rounded_rectangle([px0,py0,px1,py1],radius=22,outline=(205,210,216),width=3)
    cw=px1-px0
    # лого
    yy=py0+46
    yy=center(d,"U SMILE",font(AB,58),yy,W,GRAPHITE)
    yy=center(d,"СТОМАТОЛОГИЯ",font(AR,22),yy+10,W,(90,93,99))
    # QR
    q=qr(qrdata).resize((300,300))
    img.paste(q,((W-300)//2,yy+34))
    yy=yy+34+300
    # tagline
    yy=center(d,tagline,font(AB,34),yy+24,W,GRAPHITE)
    yy=center(d,"Наведите камеру телефона",font(AR,20),yy+12,W,(120,123,129))
    # адрес внизу панели
    center(d,"Авиационная 9 · СПб",font(AR,22),py1-54,W,(90,93,99))
    img.save(os.path.join(D,outname));print("OK",outname)
stand("Запись онлайн","https://usmile.ru/","qr-stand-zapis.png")
stand("Оставьте отзыв","https://yandex.ru/maps/org/yunivers_smayl/126595337382/reviews/","qr-stand-otzyv.png")
stand("Мы в соцсетях","https://vk.com/usmile.clinic","qr-stand-soc.png")
