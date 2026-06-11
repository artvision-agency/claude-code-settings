import qrcode, os
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image, ImageDraw, ImageFont
D="/Users/antonk/artvision-data/clients/usmile/ideas/signage-v5-corner/bakeoff"
GR=(29,29,31); BLUE=(37,99,235)
# центр-лого: графит-кружок с белой U
def center_logo(sz=180):
    im=Image.new("RGBA",(sz,sz),(0,0,0,0)); d=ImageDraw.Draw(im)
    d.ellipse([0,0,sz-1,sz-1],fill=GR)
    try: f=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf",int(sz*0.62))
    except: f=ImageFont.load_default()
    t="U"; bb=d.textbbox((0,0),t,font=f); w=bb[2]-bb[0]; h=bb[3]-bb[1]
    d.text(((sz-w)//2-bb[0],(sz-h)//2-bb[1]),t,font=f,fill=(255,255,255))
    return im
def branded(data,out,color=GR):
    q=qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,box_size=18,border=3)
    q.add_data(data); q.make(fit=True)
    img=q.make_image(image_factory=StyledPilImage,module_drawer=RoundedModuleDrawer(),
                     color_mask=SolidFillColorMask(front_color=color,back_color=(255,255,255))).convert("RGBA")
    lg=center_logo(int(img.size[0]*0.20))
    # белая подложка под лого
    pad=int(lg.size[0]*1.18); bg=Image.new("RGBA",(pad,pad),(255,255,255,255))
    px=(img.size[0]-pad)//2; img.paste(bg,(px,px),bg); img.paste(lg,((img.size[0]-lg.size[0])//2,)*2,lg)
    img.convert("RGB").save(os.path.join(D,out)); print("OK",out,img.size)
branded("https://usmile.ru/","qr-branded-zapis.png",GR)
branded("https://vk.com/usmile.clinic","qr-branded-soc.png",BLUE)
branded("https://yandex.ru/maps/org/yunivers_smayl/126595337382/reviews/","qr-branded-otzyv.png",GR)
