"""PepeX card generator."""
import math
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

W, H = 1200, 630
THEMES = {
    "neon": {"bg": ((4,12,28),(8,48,62)), "win": ((70,255,195),(90,190,255)), "loss": ((255,90,115),(255,160,90)), "text": (240,248,255), "muted": (140,168,192), "ink": (6,16,30)},
    "gold": {"bg": ((8,8,10),(46,32,8)), "win": ((255,218,90),(255,158,28)), "loss": ((255,96,84),(190,40,64)), "text": (255,246,226), "muted": (178,160,124), "ink": (22,14,2)},
    "violet": {"bg": ((12,6,34),(66,14,92)), "win": ((110,255,225),(196,122,255)), "loss": ((255,100,150),(255,176,96)), "text": (246,240,255), "muted": (164,148,196), "ink": (14,6,34)},
    "frost": {"bg": ((10,14,24),(34,48,72)), "win": ((230,246,255),(110,196,255)), "loss": ((255,150,170),(255,205,205)), "text": (248,251,255), "muted": (150,166,190), "ink": (10,16,28)},
}

def font(size):
    for name in ("segoeuib.ttf","arialbd.ttf","DejaVuSans-Bold.ttf"):
        try: return ImageFont.truetype(name,size)
        except OSError: pass
    return ImageFont.load_default()

def fit_font(draw,text,max_w,start):
    size=start
    while size>24 and draw.textlength(text,font=font(size))>max_w: size-=6
    return font(size)

def hgradient(size,c1,c2):
    w,h=size; mask=Image.linear_gradient("L").rotate(90,expand=True).resize((w,h))
    return Image.composite(Image.new("RGB",(w,h),c2),Image.new("RGB",(w,h),c1),mask)

def vgradient(size,c1,c2):
    w,h=size; mask=Image.linear_gradient("L").resize((w,h))
    return Image.composite(Image.new("RGB",(w,h),c2),Image.new("RGB",(w,h),c1),mask)

def usd(v):
    v=float(v)
    for cut,s in ((1e12,"T"),(1e9,"B"),(1e6,"M"),(1e3,"K")):
        if abs(v)>=cut: return f"${v/cut:,.2f}{s}"
    return f"${v:,.2f}"

def px(v):
    for cut,s in ((1e12,"T"),(1e9,"B"),(1e6,"M")):
        if abs(v)>=cut: return f"{v/cut:,.2f}{s}"
    if abs(v)>=100: return f"{v:,.2f}"
    if abs(v)>=1: return f"{v:,.3f}"
    return f"{v:.6f}"

def save(img,path): img.convert("RGB").save(path,"PNG")

def glow(img,center,radius,color,strength=100):
    layer=Image.new("RGBA",img.size,(0,0,0,0)); x,y=center
    ImageDraw.Draw(layer).ellipse([x-radius,y-radius,x+radius,y+radius],fill=color+(strength,))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius*.6)))

def panel(img,box,radius=26,fill=(255,255,255,16),outline=(255,255,255,48)):
    layer=Image.new("RGBA",img.size,(0,0,0,0)); ImageDraw.Draw(layer).rounded_rectangle(box,radius=radius,fill=fill,outline=outline,width=2); img.alpha_composite(layer)

def paint_mask(img,mask,c1,c2,halo=.5,blur=18):
    box=mask.getbbox()
    if not box:return
    x0,_,x1,_=box
    if halo:
        haze=Image.new("RGBA",img.size,c1+(0,)); haze.putalpha(mask.filter(ImageFilter.GaussianBlur(blur)).point(lambda v:int(v*halo))); img.alpha_composite(haze)
    layer=Image.new("RGBA",img.size,(0,0,0,0)); layer.paste(hgradient((max(x1-x0,1),img.height),c1,c2),(x0,0)); img.paste(layer,(0,0),mask)

def gradient_text(img,xy,text,fnt,c1,c2,halo=.5,blur=18):
    mask=Image.new("L",img.size,0); ImageDraw.Draw(mask).text(xy,text,font=fnt,fill=255); paint_mask(img,mask,c1,c2,halo,blur)

def pill(img,xy,text,fnt,c1,c2,ink):
    d=ImageDraw.Draw(img); w,h=int(d.textlength(text,font=fnt))+44,48; x,y=xy
    mask=Image.new("L",(w,h),0); ImageDraw.Draw(mask).rounded_rectangle([0,0,w-1,h-1],radius=h//2,fill=255)
    img.paste(hgradient((w,h),c1,c2),(x,y),mask); d.text((x+22,y+h//2),text,font=fnt,fill=ink,anchor="lm"); return w

def background(t,c1,c2):
    img=vgradient((W,H),*t["bg"]).convert("RGBA"); glow(img,(W-170,40),340,c1,62); glow(img,(60,H-30),280,c2,48); img.paste(hgradient((W,4),c1,c2),(0,0)); return img

def mascot_badge(path,size,c1,c2):
    if not path:return None
    try:m=Image.open(path).convert("RGBA")
    except FileNotFoundError:return None
    side=max(int(min(m.width,m.height)*.85),1); cx,cy=.57*m.width,.45*m.height
    left=min(max(cx-side/2,0),m.width-side); top=min(max(cy-side/2,0),m.height-side)
    face=m.crop((int(left),int(top),int(left)+side,int(top)+side)).resize((size,size),Image.LANCZOS)
    big=size*4; disc=Image.new("L",(big,big),0); ImageDraw.Draw(disc).ellipse([0,0,big-1,big-1],fill=255); disc=disc.resize((size,size),Image.LANCZOS)
    ring=Image.new("L",(big,big),0); rd=ImageDraw.Draw(ring); rd.ellipse([0,0,big-1,big-1],fill=255); rd.ellipse([12,12,big-13,big-13],fill=0); ring=ring.resize((size,size),Image.LANCZOS)
    badge=Image.new("RGBA",(size,size),(0,0,0,0)); badge.paste(face,(0,0),disc); badge.paste(hgradient((size,size),c1,c2),(0,0),ring); return badge

def short_wallet(wallet):
    if not wallet or str(wallet).lower()=="demo": return "DEMO WALLET"
    s=str(wallet); return f"{s[:5]}...{s[-4:]}" if len(s)>=9 else s

def identity_block(img,owner_name=None,wallet_address=None,t=None):
    if not owner_name and not wallet_address:return
    d=ImageDraw.Draw(img); name=(owner_name or "Wallet").strip()[:28]; addr=short_wallet(wallet_address)
    # Keep identity compact and visually distinct without interfering with the main metrics.
    panel(img,(70,86,590,120),radius=17,fill=(255,255,255,10),outline=(255,255,255,28))
    d.text((88,103),name,font=fit_font(d,name,240,20),fill=t["text"],anchor="lm")
    d.text((560,103),addr,font=font(17),fill=t["muted"],anchor="rm")

def header(img,t,c1,c2,label,mascot_path=None,tag="",owner_name=None,wallet_address=None):
    d=ImageDraw.Draw(img); gradient_text(img,(70,40),"PEPEX",font(38),c1,c2,.4,9)
    badge=mascot_badge(mascot_path,54,c1,c2) if mascot_path else None
    if badge:
        bx=70+int(d.textlength("PEPEX",font=font(38)))+18; glow(img,(bx+27,63),38,c1,70); img.alpha_composite(badge,(bx,36))
    d.text((W-70,54),f"{label} | {tag}" if tag else label,font=font(20),fill=t["muted"],anchor="rm")
    identity_block(img,owner_name,wallet_address,t)

def stat(img,x,y,label,value,t,color=None):
    d=ImageDraw.Draw(img); d.text((x,y),label,font=font(19),fill=t["muted"]); d.text((x,y+30),value,font=font(38),fill=color or t["text"])

def stat_strip(img,t,items,color):
    panel(img,(70,490,1130,588))
    for i,(label,value) in enumerate(items): stat(img,104+i*350,504,label,value,t,color if i==len(items)-1 else None)

def place_mascot(img,path,c1,c2):
    try:m=Image.open(path).convert("RGBA")
    except (FileNotFoundError,TypeError):return None
    m.thumbnail((410,200)); x,y=720+(410-m.width)//2,84; glow(img,(x+m.width//2,y+m.height//2),150,c1,70)
    mask=Image.new("L",m.size,0); ImageDraw.Draw(mask).rounded_rectangle([0,0,m.width-1,m.height-1],radius=28,fill=255); img.paste(m,(x,y),mask)
    ring=Image.new("RGBA",img.size,(0,0,0,0)); ImageDraw.Draw(ring).rounded_rectangle([x,y,x+m.width,y+m.height],radius=28,outline=c1+(230,),width=3); img.alpha_composite(ring); return y+m.height

def line_chart(img,box,values,c1,c2):
    x0,y0,x1,y1=box; panel(img,box); lo,hi=min(values),max(values); span=(hi-lo) or 1; n=max(len(values)-1,1); top,bottom=y0+30,y1-22
    pts=[(x0+24+i*(x1-x0-48)/n,bottom-(v-lo)/span*(bottom-top)) for i,v in enumerate(values)]
    grid=Image.new("RGBA",img.size,(0,0,0,0)); gd=ImageDraw.Draw(grid)
    for k in range(4): gy=top+k*(bottom-top)/3; gd.line([(x0+20,gy),(x1-20,gy)],fill=(255,255,255,20),width=1)
    img.alpha_composite(grid)
    area=Image.new("L",img.size,0); ImageDraw.Draw(area).polygon(pts+[(pts[-1][0],bottom+10),(pts[0][0],bottom+10)],fill=255)
    ramp=ImageOps.invert(Image.linear_gradient("L").resize((x1-x0,y1-y0))).point(lambda v:int(v*.55)); fade=Image.new("L",img.size,0); fade.paste(ramp,(x0,y0)); fill=Image.new("RGBA",img.size,c1+(0,)); fill.putalpha(ImageChops.multiply(area,fade)); img.alpha_composite(fill)
    line=Image.new("L",img.size,0); ImageDraw.Draw(line).line(pts,fill=255,width=5,joint="curve"); paint_mask(img,line,c1,c2,.9,10); ex,ey=pts[-1]; glow(img,(ex,ey),26,c2,150); ImageDraw.Draw(img).ellipse([ex-8,ey-8,ex+8,ey+8],fill=(255,255,255),outline=c2,width=4)

def divider(img,x0,x1,y):
    layer=Image.new("RGBA",img.size,(0,0,0,0)); ImageDraw.Draw(layer).line([(x0,y),(x1,y)],fill=(255,255,255,26),width=1); img.alpha_composite(layer)

def details_panel(img,box,rows,t):
    x0,y0,x1,y1=box; panel(img,box); d=ImageDraw.Draw(img); row_h=min(60,(y1-y0-20)/len(rows)); start=y0+(y1-y0-row_h*len(rows))/2
    for i,(label,value) in enumerate(rows):
        cy=start+row_h*(i+.5); d.text((x0+26,cy),label,font=font(19),fill=t["muted"],anchor="lm"); room=x1-x0-52-d.textlength(label,font=font(19))-16; d.text((x1-26,cy),value,font=fit_font(d,value,room,27),fill=t["text"],anchor="rm")
        if i<len(rows)-1: divider(img,x0+22,x1-22,start+row_h*(i+1))

def make_card(coin,side,leverage,roe,pnl,entry,exit_px,curve=None,details=None,exit_label="EXIT",theme="neon",mascot_path="mascot.png",tag="",owner_name=None,wallet_address=None,path="card.png"):
    t=THEMES[theme]; c1,c2=t["win"] if pnl>=0 else t["loss"]; img=background(t,c1,c2); header(img,t,c1,c2,"PNL CARD",mascot_path,tag,owner_name,wallet_address); d=ImageDraw.Draw(img)
    pair=f"{coin} / USD"; pf=fit_font(d,pair,330,54); d.text((70,132),pair,font=pf,fill=t["text"]); pill(img,(70+int(d.textlength(pair,font=pf))+26,136),f"{side} {leverage}x",font(28),c1,c2,t["ink"])
    big=f"{roe:+.2f}%"; gradient_text(img,(62,232),big,fit_font(d,big,620,150),c1,c2,.55,26); d.text((74,412),"RETURN ON EQUITY",font=font(19),fill=t["muted"])
    bottom=place_mascot(img,mascot_path,c1,c2); top=84 if bottom is None else bottom+32
    if curve: line_chart(img,(720,top,1130,462),curve,c1,c2)
    elif details: details_panel(img,(720,top,1130,462),details,t)
    stat_strip(img,t,[("ENTRY",px(entry)),(exit_label,px(exit_px)),("PNL (USD)",f"{pnl:+,.2f}")],c1); save(img,path)

def make_volume_card(vol_24h,vol_7d,vol_30d,daily,trades=0,fees=0.0,labels=None,theme="neon",mascot_path="mascot.png",tag="",owner_name=None,wallet_address=None,path="volume.png"):
    t=THEMES[theme]; c1,c2=t["win"]; img=background(t,c1,c2); header(img,t,c1,c2,"VOLUME CARD",mascot_path,tag,owner_name,wallet_address); d=ImageDraw.Draw(img)
    d.text((74,136),"24H TRADING VOLUME",font=font(24),fill=t["muted"]); big=usd(vol_24h); gradient_text(img,(62,175),big,fit_font(d,big,560,150),c1,c2,.55,26)
    x=74
    for label,value in (("7D",usd(vol_7d)),("30D",usd(vol_30d))):
        text=f"{label}   {value}"; w=int(d.textlength(text,font=font(28)))+44; panel(img,(x,372,x+w,424),radius=26); d.text((x+22,398),label,font=font(28),fill=t["muted"],anchor="lm"); d.text((x+22+d.textlength(label+"   ",font=font(28)),398),value,font=font(28),fill=t["text"],anchor="lm"); x+=w+18
    bx0,by0,bx1,by1=660,84,1130,462; panel(img,(bx0,by0,bx1,by1)); labels=labels or ["6d","5d","4d","3d","2d","1d","Today"]; n,hi=len(daily),max(daily) or 1; slot=(bx1-bx0-60)/n; bw=int(slot*.56); base,ceiling=by1-52,by0+40
    for i,v in enumerate(daily):
        h=max(int((v/hi)*(base-ceiling)),10); bx=int(bx0+30+i*slot+(slot-bw)/2); by=base-h; last=i==n-1; mask=Image.new("L",(bw,h),0); ImageDraw.Draw(mask).rounded_rectangle([0,0,bw-1,h+12],radius=12,fill=255)
        if not last: mask=mask.point(lambda a:int(a*.5))
        else: glow(img,(bx+bw//2,by+h//2),90,c1,70)
        img.paste(vgradient((bw,h),c1,c2),(bx,by),mask); d.text((bx+bw//2,base+24),labels[i],font=font(18),fill=t["text"] if last else t["muted"],anchor="mm")
    avg=usd(vol_24h/trades) if trades else "-"; stat_strip(img,t,[("TRADES (24H)",f"{trades:,}"),("FEES PAID",usd(fees)),("AVG TRADE SIZE",avg)],c1); save(img,path)

def make_portfolio_card(account_value,upnl,margin_used,withdrawable,exposure,positions,theme="neon",mascot_path="mascot.png",tag="",owner_name=None,wallet_address=None,path="portfolio.png"):
    t=THEMES[theme]; c1,c2=t["win"]; img=background(t,c1,c2); header(img,t,c1,c2,"PORTFOLIO CARD",mascot_path,tag,owner_name,wallet_address); d=ImageDraw.Draw(img)
    d.text((74,136),f"{tag} ACCOUNT VALUE" if tag else "PERP ACCOUNT VALUE",font=font(24),fill=t["muted"]); big=usd(account_value); gradient_text(img,(62,175),big,fit_font(d,big,560,150),c1,c2,.55,26)
    up_color=t["win"][0] if upnl>=0 else t["loss"][0]; x=74
    for label,value,color in (("uPNL",f"{upnl:+,.2f}",up_color),("OPEN",str(len(positions)),t["text"])):
        w=int(d.textlength(f"{label}   {value}",font=font(28)))+44; panel(img,(x,372,x+w,424),radius=26); d.text((x+22,398),label,font=font(28),fill=t["muted"],anchor="lm"); d.text((x+22+d.textlength(label+"   ",font=font(28)),398),value,font=font(28),fill=color,anchor="lm"); x+=w+18
    x0,y0,x1,y1=660,84,1130,462; panel(img,(x0,y0,x1,y1)); d.text((x0+26,y0+28),"OPEN POSITIONS",font=font(19),fill=t["muted"],anchor="lm")
    if not positions: d.text(((x0+x1)//2,(y0+y1)//2+10),"No open positions",font=font(26),fill=t["muted"],anchor="mm")
    y=y0+58
    for i,p in enumerate(positions[:4]):
        side_color=t["win"][0] if p["side"]=="LONG" else t["loss"][0]; pnl_color=t["win"][0] if p["pnl"]>=0 else t["loss"][0]
        d.text((x0+26,y+16),p["coin"],font=font(30),fill=t["text"],anchor="lm"); d.text((x0+26,y+48),f"{p['side']} {p['lev']}x",font=font(18),fill=side_color,anchor="lm"); d.text((x1-26,y+16),f"{p['pnl']:+,.2f}",font=font(30),fill=pnl_color,anchor="rm"); d.text((x1-26,y+48),usd(p["value"]),font=font(18),fill=t["muted"],anchor="rm")
        if i<min(len(positions),4)-1: divider(img,x0+22,x1-22,y+70)
        y+=74
    if len(positions)>4: d.text((x0+26,y1-22),f"+{len(positions)-4} more",font=font(18),fill=t["muted"],anchor="lm")
    stat_strip(img,t,[("MARGIN USED",usd(margin_used)),("WITHDRAWABLE",usd(withdrawable)),("EXPOSURE",usd(exposure))],c1); save(img,path)
