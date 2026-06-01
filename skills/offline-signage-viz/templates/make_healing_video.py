import os,subprocess
from PIL import Image
D="/Users/antonk/artvision-data/clients/usmile/ideas/signage-v5-corner"
A=Image.open(f"{D}/bakeoff/story-A-sick__gemini3pro.png").convert("RGB")
B=Image.open(f"{D}/bakeoff/story-B-healed__gemini3pro.png").convert("RGB")
W,H=864,1184
A=A.resize((W,H));B=B.resize((W,H))
F="/tmp/heal-frames";os.makedirs(F,exist_ok=True)
[os.remove(os.path.join(F,f)) for f in os.listdir(F)]
FPS=30;idx=0
def hold(img,sec):
    global idx
    for _ in range(int(FPS*sec)):
        img.save(f"{F}/f{idx:04d}.png");idx+=1
def fade(a,b,sec):
    global idx
    n=int(FPS*sec)
    for i in range(n):
        t=i/(n-1)
        Image.blend(a,b,t).save(f"{F}/f{idx:04d}.png");idx+=1
hold(A,1.5)        # больной зуб
fade(A,B,2.0)      # лечение
hold(B,3.0)        # здоровый + U SMILE
fade(B,A,1.0)      # петля
out=f"{D}/tooth-healing-story.mp4"
r=subprocess.run(["ffmpeg","-y","-framerate",str(FPS),"-i",f"{F}/f%04d.png","-c:v","libx264","-preset","slow","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart","-r",str(FPS),out],capture_output=True,text=True)
print("rc",r.returncode, "OK" if r.returncode==0 else r.stderr[-200:])
print("OUT",os.path.getsize(out) if os.path.exists(out) else "MISS")
