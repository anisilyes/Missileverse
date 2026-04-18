"""
AIR DEFENSE WARFARE — Mobile (Kivy) — Optimized Build
======================================================
Dependencies: kivy ONLY (no numpy, no pillow)
pip install kivy requests
Place missile.png and interceptor.png next to main.py
"""

import kivy
kivy.require("2.1.0")

from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Line, Ellipse, Rectangle, Triangle
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.graphics.texture import Texture
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.metrics import dp, sp

import math, random, time, threading, io, struct, zlib
import urllib.request
from dataclasses import dataclass, field

# ─── CONSTANTS ────────────────────────────────────────────────────────────────

TILE_SIZE          = 256
TILE_SERVER        = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
ZOOM_MIN, ZOOM_MAX = 2, 10
ZOOM_DEFAULT       = 3
UI_H               = dp(130)
PANEL_H            = dp(270)

GREEN      = (0,    1,    0.3,  1)
GREEN_DIM  = (0,    0.7,  0.2,  1)
RED        = (1,    0.25, 0.25, 1)
ORANGE     = (1,    0.63, 0,    1)
YELLOW     = (1,    0.9,  0,    1)
CYAN       = (0,    0.85, 0.85, 1)
BLUE       = (0.25, 0.63, 1,    1)
WHITE      = (1,    1,    1,    1)
GRAY       = (0.47, 0.51, 0.47, 1)

COUNTRIES = {
    "Algeria": {"lat": 28.0,  "lon":  2.0},
    "USA":     {"lat": 37.0,  "lon": -95.0},
    "Russia":  {"lat": 60.0,  "lon":  90.0},
    "China":   {"lat": 35.0,  "lon": 105.0},
    "Iran":    {"lat": 32.0,  "lon":  53.0},
    "France":  {"lat": 46.0,  "lon":  2.0},
    "England": {"lat": 52.5,  "lon": -1.5},
    "Germany": {"lat": 51.0,  "lon":  10.0},
    "Ukraine": {"lat": 49.0,  "lon":  32.0},
    "Turkey":  {"lat": 39.0,  "lon":  35.0},
}

DEFAULT_CITIES = {
    "Algeria": [("Algiers",36.74,3.06,100),("Oran",35.69,-0.63,100),("Constantine",36.36,6.61,80)],
    "USA":     [("Washington",38.90,-77.03,100),("New York",40.71,-74.00,100),("Los Angeles",34.05,-118.24,100),("Chicago",41.87,-87.62,80)],
    "Russia":  [("Moscow",55.75,37.61,100),("St Petersburg",59.93,30.31,100),("Novosibirsk",54.99,82.90,80)],
    "China":   [("Beijing",39.90,116.40,100),("Shanghai",31.22,121.45,100),("Shenzhen",22.54,114.05,80)],
    "Iran":    [("Tehran",35.68,51.38,100),("Isfahan",32.66,51.67,80),("Shiraz",29.59,52.58,70)],
    "France":  [("Paris",48.85,2.35,100),("Lyon",45.74,4.83,80),("Marseille",43.29,5.38,80)],
    "England": [("London",51.50,-0.12,100),("Manchester",53.48,-2.24,80),("Birmingham",52.48,-1.89,70)],
    "Germany": [("Berlin",52.52,13.40,100),("Munich",48.13,11.57,80),("Hamburg",53.55,9.99,70)],
    "Ukraine": [("Kyiv",50.45,30.52,100),("Kharkiv",49.99,36.23,80),("Odessa",46.47,30.73,70)],
    "Turkey":  [("Ankara",39.92,32.85,100),("Istanbul",41.01,28.94,100),("Izmir",38.41,27.13,70)],
}

MISSILES = {
    "Tomahawk": {"range_km": 2500, "speed": 0.006, "cost": 5_000_000,  "color": RED},
    "KH-80":    {"range_km": 5000, "speed": 0.009, "cost": 12_000_000, "color": ORANGE},
}

INTERCEPTORS = {
    "S-400": {"range_km": 400,  "chance": 0.70, "cost": 50_000_000,  "color": CYAN},
    "S-500": {"range_km": 500,  "chance": 1.00, "cost": 120_000_000, "color": BLUE},
}

RADARS = {
    "Radar-1100": {"range_km": 1100, "cost": 80_000_000, "color": GREEN_DIM},
}

# ─── PURE-PYTHON PNG DECODER (replaces Pillow) ────────────────────────────────

def _paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p-a), abs(p-b), abs(p-c)
    if pa <= pb and pa <= pc: return a
    if pb <= pc: return b
    return c

def decode_png_rgba(data: bytes):
    """
    Pure-Python PNG → military-tinted RGBA bytes (flipped for Kivy).
    Handles 8-bit RGB and RGBA (all OSM tiles).
    Returns (raw_bytes, width, height).
    No Pillow or NumPy required.
    """
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos = 8
    idat = []
    width = height = color_type = 0

    while pos < len(data):
        length = struct.unpack('>I', data[pos:pos+4])[0]
        ctype  = data[pos+4:pos+8]
        chunk  = data[pos+8:pos+8+length]
        pos   += 12 + length
        if ctype == b'IHDR':
            width, height = struct.unpack('>II', chunk[:8])
            color_type = chunk[9]
        elif ctype == b'IDAT':
            idat.append(chunk)
        elif ctype == b'IEND':
            break

    raw  = zlib.decompress(b''.join(idat))
    ch   = 4 if color_type == 6 else 3
    stride = width * ch
    recon  = bytearray()
    prev   = bytearray(stride)
    idx    = 0

    for _ in range(height):
        filt = raw[idx]; idx += 1
        row  = bytearray(raw[idx:idx+stride]); idx += stride
        if filt == 1:
            for i in range(ch, stride):
                row[i] = (row[i] + row[i-ch]) & 0xFF
        elif filt == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif filt == 3:
            for i in range(stride):
                a = row[i-ch] if i >= ch else 0
                row[i] = (row[i] + (a + prev[i]) // 2) & 0xFF
        elif filt == 4:
            for i in range(stride):
                a = row[i-ch] if i >= ch else 0
                b = prev[i]
                c = prev[i-ch] if i >= ch else 0
                row[i] = (row[i] + _paeth(a, b, c)) & 0xFF
        recon.extend(row)
        prev = row

    # Tint (R*0.35, G*0.55, B*0.35) + flip vertically for Kivy
    out = bytearray(width * height * 4)
    for row_i in range(height):
        sr = row_i * stride
        dr = (height - 1 - row_i) * width * 4
        for x in range(width):
            s = sr + x * ch
            d = dr + x * 4
            out[d]   = int(recon[s]   * 0.35)
            out[d+1] = int(recon[s+1] * 0.55)
            out[d+2] = int(recon[s+2] * 0.35)
            out[d+3] = recon[s+3] if ch == 4 else 255
    return bytes(out), width, height

# ─── GEO ──────────────────────────────────────────────────────────────────────

def ll_to_tile(lat, lon, zoom):
    n  = 2 ** zoom
    x  = (lon + 180) / 360 * n
    lr = math.radians(lat)
    y  = (1 - math.log(math.tan(lr) + 1/math.cos(lr)) / math.pi) / 2 * n
    return x, y

def tile_to_ll(tx, ty, zoom):
    n   = 2 ** zoom
    lon = tx / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2*ty/n))))
    return lat, lon

def haversine(la1, lo1, la2, lo2):
    R = 6371
    dla = math.radians(la2-la1); dlo = math.radians(lo2-lo1)
    a = math.sin(dla/2)**2 + math.cos(math.radians(la1))*math.cos(math.radians(la2))*math.sin(dlo/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def km_px(km, zoom, lat=0):
    return km * 1000 / (156543.03392 * math.cos(math.radians(lat)) / (2**zoom))

# ─── TILE CACHE ───────────────────────────────────────────────────────────────

_FB = None
def fallback_tex():
    global _FB
    if _FB: return _FB
    raw = bytearray(TILE_SIZE * TILE_SIZE * 4)
    for y in range(TILE_SIZE):
        for x in range(TILE_SIZE):
            i = (y*TILE_SIZE+x)*4
            g = (x%32==0 or y%32==0)
            raw[i]=20 if g else 10; raw[i+1]=35 if g else 18
            raw[i+2]=20 if g else 10; raw[i+3]=255
    t = Texture.create(size=(TILE_SIZE,TILE_SIZE), colorfmt='rgba')
    t.blit_buffer(bytes(raw), colorfmt='rgba', bufferfmt='ubyte')
    _FB = t; return t

class TileCache:
    def __init__(self):
        self.cache={}; self.loading=set(); self.lock=threading.Lock()

    def get(self, z, x, y):
        with self.lock: return self.cache.get((z,x,y))

    def req(self, z, x, y, cb):
        k=(z,x,y)
        with self.lock:
            if k in self.cache or k in self.loading: return
            self.loading.add(k)
        threading.Thread(target=self._fetch, args=(z,x,y,cb), daemon=True).start()

    def _fetch(self, z, x, y, cb):
        k=(z,x,y)
        try:
            url = TILE_SERVER.format(z=z,x=x,y=y)
            req = urllib.request.Request(url, headers={"User-Agent":"AirDefenseWarfare/2.0"})
            with urllib.request.urlopen(req, timeout=8) as r: data=r.read()
            rgba, w, h = decode_png_rgba(data)
            def _up(dt):
                t=Texture.create(size=(w,h),colorfmt='rgba')
                t.blit_buffer(rgba,colorfmt='rgba',bufferfmt='ubyte')
                with self.lock: self.cache[k]=t; self.loading.discard(k)
                cb()
            Clock.schedule_once(_up, 0)
        except:
            def _fb(dt):
                with self.lock: self.cache[k]=fallback_tex(); self.loading.discard(k)
                cb()
            Clock.schedule_once(_fb, 0)

# ─── GAME DATA ────────────────────────────────────────────────────────────────

@dataclass
class City:
    name:str; lat:float; lon:float; hp:int; max_hp:int=100; country:str=""

@dataclass
class Missile:
    id:int; kind:str
    slat:float; slon:float; dlat:float; dlon:float
    progress:float=0.0; alive:bool=True; owner:str=""
    trail:list=field(default_factory=list); intercepted:bool=False

@dataclass
class Interceptor:
    id:int; kind:str
    slat:float; slon:float; dlat:float; dlon:float
    tid:int; progress:float=0.0; alive:bool=True; owner:str=""

@dataclass
class Defense:
    id:int; kind:str; lat:float; lon:float
    country:str; range_km:float; cooldown:float=0.0

@dataclass
class Explosion:
    lat:float; lon:float; radius:float=0.0
    max_r:float=25.0; alpha:float=1.0; done:bool=False

# ─── GAME STATE ───────────────────────────────────────────────────────────────

class GS:
    def __init__(self):
        self.mode="select_country"; self.player=""
        self.money={c:999_000_000 for c in COUNTRIES}
        self.cities={c:[City(n,la,lo,hp,hp,c) for n,la,lo,hp in v] for c,v in DEFAULT_CITIES.items()}
        self.defs:list[Defense]=[]; self.missiles:list[Missile]=[]
        self.ints:list[Interceptor]=[]; self.explosions:list[Explosion]=[]
        self._id=1
        self.sel_missile="Tomahawk"; self.sel_defense="S-400"
        self.placing=None; self.building=False; self.click=None
        self.show_traj=True; self.show_radar=True; self.show_int=True
        self.msgs=[]; self.ai_t=0.0; self.ai_iv=14.0; self.paused=False

    def uid(self): self._id+=1; return self._id

    def msg(self, t, col=None, dur=3.5):
        col=col or GREEN; self.msgs.append((t,time.time()+dur,col)); self.msgs=self.msgs[-6:]

    def launch(self, kind, sl, so, dl, do_, owner):
        cost=MISSILES[kind]["cost"]
        if self.money[owner]<cost: self.msg("Not enough money!",RED); return
        if haversine(sl,so,dl,do_)>MISSILES[kind]["range_km"]: self.msg(f"{kind} out of range!",RED); return
        self.money[owner]-=cost
        self.missiles.append(Missile(self.uid(),kind,sl,so,dl,do_,owner=owner))
        self.msg(f"{kind} launched!",MISSILES[kind]["color"])

    def buy_def(self, kind, lat, lon, country):
        d=INTERCEPTORS if kind in INTERCEPTORS else RADARS
        cost,rng=d[kind]["cost"],d[kind]["range_km"]
        if self.money[country]<cost: self.msg("Not enough money!",RED); return
        self.money[country]-=cost
        self.defs.append(Defense(self.uid(),kind,lat,lon,country,rng))
        self.msg(f"{kind} deployed!",CYAN)

    def build_city(self, country, lat, lon):
        if self.money[country]<20_000_000: self.msg("Not enough money!",RED); return
        self.money[country]-=20_000_000
        self.cities[country].append(City(f"City-{self.uid()}",lat,lon,100,100,country))
        self.msg(f"City built in {country}!",GREEN)

    def update(self, dt):
        if self.paused: return
        now=time.time(); self.msgs=[(t,e,c) for t,e,c in self.msgs if e>now]

        for m in list(self.missiles):
            if not m.alive: continue
            m.progress+=dt*MISSILES[m.kind]["speed"]
            cl=m.slat+(m.dlat-m.slat)*m.progress; co=m.slon+(m.dlon-m.slon)*m.progress
            m.trail.append((cl,co))
            if len(m.trail)>35: m.trail.pop(0)
            if m.intercepted: m.alive=False; self.explosions.append(Explosion(cl,co,max_r=12)); continue
            if m.progress>=1.0:
                m.alive=False; self.explosions.append(Explosion(m.dlat,m.dlon))
                self._dmg(m.dlat,m.dlon,m.kind)

        for i in list(self.ints):
            if not i.alive: continue
            i.progress+=dt*0.012
            if i.progress>=1.0: i.alive=False

        for u in self.defs:
            if u.cooldown>0: u.cooldown=max(0,u.cooldown-dt)
            if u.kind not in INTERCEPTORS or u.cooldown>0: continue
            for m in self.missiles:
                if not m.alive or m.intercepted or m.owner==u.country: continue
                cl=m.slat+(m.dlat-m.slat)*m.progress; co=m.slon+(m.dlon-m.slon)*m.progress
                if haversine(u.lat,u.lon,cl,co)<=u.range_km:
                    u.cooldown=3.0
                    self.ints.append(Interceptor(self.uid(),u.kind,u.lat,u.lon,
                        cl+(m.dlat-cl)*0.1, co+(m.dlon-co)*0.1, m.id, owner=u.country))
                    if random.random()<INTERCEPTORS[u.kind]["chance"]:
                        m.intercepted=True; self.msg(f"✓ {u.kind} hit {m.kind}!",CYAN)
                    else: self.msg(f"✗ {u.kind} missed!",RED)
                    break

        for e in list(self.explosions):
            e.radius+=35*dt; e.alpha=max(0.0,1.0-e.radius/e.max_r)
            if e.radius>=e.max_r: e.done=True
        self.explosions=[e for e in self.explosions if not e.done]
        self.missiles=[m for m in self.missiles if m.alive or m.progress<1.0]
        self.ints=[i for i in self.ints if i.alive]

        if self.mode=="pvai":
            self.ai_t+=dt
            if self.ai_t>=self.ai_iv: self.ai_t=0; self._ai()

    def _dmg(self, lat, lon, kind):
        dmg=35 if kind=="KH-80" else 25
        for country,cities in self.cities.items():
            for city in cities:
                if haversine(lat,lon,city.lat,city.lon)<80:
                    city.hp=max(0,city.hp-dmg); self.msg(f"💥 {city.name} HP:{city.hp}",RED,4.0)

    def _ai(self):
        if not self.player: return
        enemies=[c for c in COUNTRIES if c!=self.player]
        att=random.choice(enemies)
        tgts=[c for c in self.cities.get(self.player,[]) if c.hp>0]
        if not tgts: return
        tgt=max(tgts,key=lambda c:c.hp)
        srcs=self.cities.get(att,[]); 
        if not srcs: return
        src=random.choice(srcs)
        dist=haversine(src.lat,src.lon,tgt.lat,tgt.lon)
        kind="KH-80" if dist>2400 else "Tomahawk"
        if dist>MISSILES[kind]["range_km"]: return
        self.launch(kind,src.lat,src.lon,tgt.lat,tgt.lon,att)

# ─── MAP WIDGET ───────────────────────────────────────────────────────────────

class MapWidget(Widget):
    def __init__(self, gs:GS, **kw):
        super().__init__(**kw)
        self.gs=gs; self.tc=TileCache()
        self.zoom=float(ZOOM_DEFAULT); self.ctx=0.0; self.cty=0.0
        self._tch={}; self._ds=None; self._dc=None
        self._pd=None; self._pz=None; self._tp=None; self._tt=0.0
        self._sm=self._img("missile.png"); self._si=self._img("interceptor.png")
        self.bind(size=lambda*a:self.rd(), pos=lambda*a:self.rd())
        Clock.schedule_interval(self._tick,1/60)

    def _img(self,f):
        try: return CoreImage(f).texture
        except: return None

    def center(self,lat,lon):
        tx,ty=ll_to_tile(lat,lon,self.zoom)
        self.ctx=tx-self.width/(2*TILE_SIZE); self.cty=ty-self.height/(2*TILE_SIZE)

    def p2ll(self,px,py):
        return tile_to_ll(self.ctx+px/TILE_SIZE, self.cty+(self.height-py)/TILE_SIZE, self.zoom)

    def ll2p(self,lat,lon):
        tx,ty=ll_to_tile(lat,lon,self.zoom)
        return (tx-self.ctx)*TILE_SIZE, self.height-(ty-self.cty)*TILE_SIZE

    def _tick(self,dt): self.gs.update(dt); self.rd()

    def rd(self):
        self.canvas.clear()
        with self.canvas:
            Color(0.03,0.07,0.03,1); Rectangle(pos=self.pos,size=self.size)
        self._tiles(); 
        if self.gs.show_radar: self._radars()
        self._cities(); self._defs(); self._missiles(); self._expls(); self._marker()

    def _tiles(self):
        n=int(2**self.zoom); tx0=int(self.ctx); ty0=int(self.cty)
        cols=int(self.width/TILE_SIZE)+2; rows=int(self.height/TILE_SIZE)+2; fb=fallback_tex()
        with self.canvas:
            for dy in range(rows):
                for dx in range(cols):
                    tx=tx0+dx; ty=ty0+dy
                    if tx<0 or ty<0 or tx>=n or ty>=n: continue
                    tex=self.tc.get(int(self.zoom),tx,ty)
                    if tex is None: self.tc.req(int(self.zoom),tx,ty,self.rd); tex=fb
                    Color(1,1,1,1)
                    Rectangle(texture=tex,
                               pos=(self.x+(tx-self.ctx)*TILE_SIZE,
                                    self.y+self.height-(ty-self.cty+1)*TILE_SIZE),
                               size=(TILE_SIZE,TILE_SIZE))

    def _radars(self):
        with self.canvas:
            for u in self.gs.defs:
                px,py=self.ll2p(u.lat,u.lon)
                r=km_px(u.range_km,self.zoom,u.lat)
                if r<4 or r>6000: continue
                col=INTERCEPTORS[u.kind]["color"] if u.kind in INTERCEPTORS else GREEN_DIM
                Color(col[0],col[1],col[2],0.10)
                Ellipse(pos=(self.x+px-r,self.y+py-r),size=(r*2,r*2))
                Color(col[0],col[1],col[2],0.45)
                Line(circle=(self.x+px,self.y+py,r),width=dp(1))

    def _cities(self):
        with self.canvas:
            for country,cities in self.gs.cities.items():
                for c in cities:
                    px,py=self.ll2p(c.lat,c.lon)
                    if not(-12<px<self.width+12 and -12<py<self.height+12): continue
                    hr=c.hp/c.max_hp; col=GREEN if hr>.6 else YELLOW if hr>.3 else RED
                    r=dp(6)
                    Color(*col); Ellipse(pos=(self.x+px-r,self.y+py-r),size=(r*2,r*2))
                    Color(1,1,1,.7); Line(circle=(self.x+px,self.y+py,r),width=dp(1))
                    bw=dp(26); bh=dp(4); bx=self.x+px-bw/2; by=self.y+py+r+dp(2)
                    Color(.2,.2,.2,.8); Rectangle(pos=(bx,by),size=(bw,bh))
                    Color(*col); Rectangle(pos=(bx,by),size=(bw*hr,bh))

    def _defs(self):
        with self.canvas:
            for u in self.gs.defs:
                px,py=self.ll2p(u.lat,u.lon)
                if not(-12<px<self.width+12 and -12<py<self.height+12): continue
                s=dp(8); col=INTERCEPTORS[u.kind]["color"] if u.kind in INTERCEPTORS else GREEN_DIM
                Color(*col)
                Triangle(points=[self.x+px,self.y+py+s*1.4,
                                  self.x+px-s,self.y+py-s*.7,self.x+px+s,self.y+py-s*.7])
                Color(1,1,1,.5)
                Line(points=[self.x+px,self.y+py+s*1.4,self.x+px-s,self.y+py-s*.7,
                              self.x+px+s,self.y+py-s*.7,self.x+px,self.y+py+s*1.4],width=dp(1))

    def _missiles(self):
        gs=self.gs
        with self.canvas:
            for m in gs.missiles:
                if not m.alive: continue
                cl=m.slat+(m.dlat-m.slat)*m.progress; co=m.slon+(m.dlon-m.slon)*m.progress
                px,py=self.ll2p(cl,co); col=MISSILES[m.kind]["color"]
                if gs.show_traj and len(m.trail)>1:
                    for i in range(1,len(m.trail)):
                        p1x,p1y=self.ll2p(*m.trail[i-1]); p2x,p2y=self.ll2p(*m.trail[i])
                        Color(col[0],col[1],col[2],.6*i/len(m.trail))
                        Line(points=[self.x+p1x,self.y+p1y,self.x+p2x,self.y+p2y],width=dp(1))
                if gs.show_traj:
                    dx,dy=self.ll2p(m.dlat,m.dlon); Color(col[0],col[1],col[2],.2)
                    Line(points=[self.x+px,self.y+py,self.x+dx,self.y+dy],
                         width=dp(1),dash_length=4,dash_offset=4)
                if self._sm:
                    Color(*col); Rectangle(texture=self._sm,pos=(self.x+px-dp(9),self.y+py-dp(13)),size=(dp(18),dp(26)))
                else:
                    Color(*col); Ellipse(pos=(self.x+px-dp(5),self.y+py-dp(5)),size=(dp(10),dp(10)))

            for ic in gs.ints:
                if not ic.alive: continue
                cl=ic.slat+(ic.dlat-ic.slat)*ic.progress; co=ic.slon+(ic.dlon-ic.slon)*ic.progress
                px,py=self.ll2p(cl,co)
                if gs.show_int:
                    dx,dy=self.ll2p(ic.dlat,ic.dlon); Color(*CYAN[:3],.3)
                    Line(points=[self.x+px,self.y+py,self.x+dx,self.y+dy],width=dp(1))
                if self._si:
                    Color(*CYAN); Rectangle(texture=self._si,pos=(self.x+px-dp(6),self.y+py-dp(11)),size=(dp(12),dp(22)))
                else:
                    Color(*CYAN); Ellipse(pos=(self.x+px-dp(4),self.y+py-dp(4)),size=(dp(8),dp(8)))

    def _expls(self):
        with self.canvas:
            for e in self.gs.explosions:
                px,py=self.ll2p(e.lat,e.lon); r=e.radius*dp(1.2)
                Color(1,.85,.3,e.alpha*.8); Ellipse(pos=(self.x+px-r,self.y+py-r),size=(r*2,r*2))
                Color(1,.3,.1,e.alpha*.45); Line(circle=(self.x+px,self.y+py,r*1.2),width=dp(2))

    def _marker(self):
        if not self.gs.click: return
        px,py=self.ll2p(*self.gs.click); r=dp(9)
        with self.canvas:
            Color(0,1,.3,.9); Line(circle=(self.x+px,self.y+py,r),width=dp(1.5))
            Line(points=[self.x+px-r*2,self.y+py,self.x+px+r*2,self.y+py],width=dp(1))
            Line(points=[self.x+px,self.y+py-r*2,self.x+px,self.y+py+r*2],width=dp(1))

    # touch
    def on_touch_down(self,t):
        self._tch[t.uid]=t
        if len(self._tch)==1:
            self._ds=(t.x,t.y); self._dc=(self.ctx,self.cty)
            self._tp=(t.x,t.y); self._tt=time.time()
        elif len(self._tch)==2:
            a,b=list(self._tch.values())
            self._pd=math.hypot(a.x-b.x,a.y-b.y); self._pz=self.zoom
        return True

    def on_touch_move(self,t):
        self._tch[t.uid]=t
        if len(self._tch)==1:
            dx=(t.x-self._ds[0])/TILE_SIZE; dy=(t.y-self._ds[1])/TILE_SIZE
            self.ctx=self._dc[0]-dx; self.cty=self._dc[1]+dy
        elif len(self._tch)==2:
            a,b=list(self._tch.values()); d=math.hypot(a.x-b.x,a.y-b.y)
            if self._pd and self._pd>0:
                nz=max(ZOOM_MIN,min(ZOOM_MAX,self._pz*(d/self._pd)))
                cx=(a.x+b.x)/2; cy=(a.y+b.y)/2
                lat,lon=self.p2ll(cx,cy); self.zoom=nz
                tx,ty=ll_to_tile(lat,lon,self.zoom)
                self.ctx=tx-cx/TILE_SIZE; self.cty=ty-(self.height-cy)/TILE_SIZE
        return True

    def on_touch_up(self,t):
        if t.uid in self._tch: del self._tch[t.uid]
        if len(self._tch)==0 and self._tp:
            if abs(t.x-self._tp[0])<dp(12) and abs(t.y-self._tp[1])<dp(12) and time.time()-self._tt<.35:
                self._tap(t.x,t.y)
        return True

    def _tap(self,tx,ty):
        gs=self.gs; lat,lon=self.p2ll(tx,ty); country=gs.player or list(COUNTRIES.keys())[0]
        if gs.placing: gs.buy_def(gs.placing,lat,lon,country); gs.placing=None; return
        if gs.building: gs.build_city(country,lat,lon); gs.building=False; return
        gs.click=(lat,lon)

# ─── HUD ──────────────────────────────────────────────────────────────────────

def B(text,cb,bg=(0,.12,.05,.95),fg=None,sh=(None,None),fs=None):
    fg=fg or GREEN; fs=fs or sp(11)
    b=Button(text=text,size_hint=sh,background_normal='',background_color=bg,
             color=fg,font_size=fs,halign='center',valign='middle')
    b.bind(on_press=cb); return b

class HUD(FloatLayout):
    def __init__(self,gs:GS,mw:MapWidget,**kw):
        super().__init__(**kw); self.gs=gs; self.mw=mw
        self._pnl=None; self._pname=None; self._pop=None
        self._bar_build(); self._msgs_build()
        Clock.schedule_interval(self._tick,.2)

    def _bar_build(self):
        bar=BoxLayout(orientation='horizontal',size_hint=(1,None),
                      height=UI_H,pos_hint={'x':0,'y':0},spacing=dp(2),padding=dp(3))
        with bar.canvas.before:
            Color(0,0,0,.88); self._bg=Rectangle()
            Color(0,1,.3,.75); self._bd=Line(width=dp(1.5))
        bar.bind(pos=self._ubg,size=self._ubg)
        self._bm=B("🚀\nMISSILES",  lambda x:self._tog("missiles"),   sh=(1,1))
        self._bd2=B("🛡\nDEFENSE",  lambda x:self._tog("interceptors"),sh=(1,1))
        self._bc=B("🏙\nCITIES",    lambda x:self._tog("cities"),      sh=(1,1))
        self._bmn=B("💰\n$999M",    lambda x:None,fg=YELLOW,           sh=(1,1))
        self._bs=B("⚙\nSETTINGS",  lambda x:self._tog("settings"),    sh=(1,1))
        for b in [self._bm,self._bd2,self._bc,self._bmn,self._bs]: bar.add_widget(b)
        self.add_widget(bar); self._bar=bar

    def _ubg(self,i,v):
        self._bg.pos=i.pos; self._bg.size=i.size
        self._bd.rectangle=(i.x,i.y,i.width,i.height)

    def _msgs_build(self):
        self._mb=BoxLayout(orientation='vertical',size_hint=(.72,None),
                            height=dp(90),pos_hint={'x':0,'top':1})
        self.add_widget(self._mb)

    def _tick(self,dt):
        gs=self.gs; m=gs.money.get(gs.player,0)
        self._bmn.text=f"💰\n${m/1e6:.0f}M" if m>=1e6 else f"💰\n${m:,}"
        self._mb.clear_widgets()
        now=time.time()
        for txt,exp,col in gs.msgs[-4:]:
            a=min(1.,(exp-now)/1.) if exp-now<1. else 1.
            self._mb.add_widget(Label(text=txt,font_size=sp(11),size_hint=(1,None),
                                       height=dp(18),color=(col[0],col[1],col[2],a)))
        for k,b in [("missiles",self._bm),("interceptors",self._bd2),
                    ("cities",self._bc),("settings",self._bs)]:
            b.background_color=(0,.28,.11,.95) if self._pname==k else (0,.12,.05,.95)
        if gs.click and self._pop is None: self._show_pop()
        if not gs.click and self._pop: self._pop.dismiss(); self._pop=None

    def _tog(self,name):
        if self._pname==name: self._cpnl()
        else: self._cpnl(); self._pname=name; self._opnl(name)

    def _cpnl(self):
        if self._pnl: self.remove_widget(self._pnl); self._pnl=None
        self._pname=None

    def _opnl(self,name):
        p=self._mkpnl(name); p.size_hint=(1,None); p.height=PANEL_H
        p.pos_hint={'x':0,'y':UI_H/Window.height}
        self._pnl=p; self.add_widget(p)

    def _pbg(self,l):
        with l.canvas.before:
            Color(0,0,0,.93); bg=Rectangle()
            Color(0,1,.3,.65); bd=Line(width=dp(1.2))
        def u(i,v): bg.pos=i.pos; bg.size=i.size; bd.rectangle=(i.x,i.y,i.width,i.height)
        l.bind(pos=u,size=u)

    def _mkpnl(self,name):
        gs=self.gs; box=BoxLayout(orientation='vertical',spacing=dp(4),padding=dp(6))
        self._pbg(box)

        if name=="missiles":
            box.add_widget(Label(text="SELECT MISSILE",font_size=sp(12),color=GREEN_DIM,size_hint=(1,None),height=dp(22)))
            row=BoxLayout(spacing=dp(6),size_hint=(1,None),height=dp(80))
            for mn,md in MISSILES.items():
                sel=gs.sel_missile==mn
                row.add_widget(B(f"{mn}\n{md['range_km']}km\n${md['cost']//1_000_000}M",
                                  lambda x,n=mn:self._smiss(n),
                                  bg=(0,.3,.1,.95) if sel else (0,.1,.04,.95),
                                  fg=md["color"],sh=(1,1),fs=sp(10)))
            box.add_widget(row)
            box.add_widget(Label(text="Tap map → Attack popup to launch",font_size=sp(10),
                                  color=GRAY,size_hint=(1,None),height=dp(18)))

        elif name=="interceptors":
            box.add_widget(Label(text="SELECT DEFENSE",font_size=sp(12),color=GREEN_DIM,size_hint=(1,None),height=dp(22)))
            row=BoxLayout(spacing=dp(4),size_hint=(1,None),height=dp(95))
            for dn,dd in INTERCEPTORS.items():
                sel=gs.sel_defense==dn
                row.add_widget(B(f"{dn}\n{dd['range_km']}km\n{int(dd['chance']*100)}%\n${dd['cost']//1_000_000}M",
                                  lambda x,n=dn:self._sdef(n),
                                  bg=(0,.15,.3,.95) if sel else (0,.05,.1,.95),
                                  fg=dd["color"],sh=(1,1),fs=sp(9)))
            for rn,rd in RADARS.items():
                sel=gs.sel_defense==rn
                row.add_widget(B(f"{rn}\n{rd['range_km']}km\n${rd['cost']//1_000_000}M",
                                  lambda x,n=rn:self._sdef(n),
                                  bg=(0,.2,.08,.95) if sel else (0,.08,.03,.95),
                                  fg=GREEN,sh=(1,1),fs=sp(9)))
            box.add_widget(row)
            act=gs.placing is not None
            box.add_widget(B(f"{'✅ PLACING...' if act else f'📍 PLACE {gs.sel_defense}'}",
                              lambda x:self._place(),
                              bg=(.1,.4,.1,.95) if act else (0,.22,.1,.95),
                              fg=GREEN,sh=(1,None),fs=sp(12)))
            box.height=dp(200)

        elif name=="cities":
            country=gs.player or list(COUNTRIES.keys())[0]
            box.add_widget(Label(text=f"CITIES — {country}",font_size=sp(12),color=GREEN_DIM,size_hint=(1,None),height=dp(22)))
            sv=ScrollView(size_hint=(1,1)); cb=BoxLayout(orientation='vertical',size_hint=(1,None),spacing=dp(2))
            cb.bind(minimum_height=cb.setter('height'))
            for c in gs.cities.get(country,[]):
                hr=c.hp/c.max_hp; col=GREEN if hr>.6 else YELLOW if hr>.3 else RED
                cb.add_widget(Label(text=f"{c.name}  HP:{c.hp}/{c.max_hp}",font_size=sp(11),
                                     color=col,size_hint=(1,None),height=dp(20)))
            sv.add_widget(cb); box.add_widget(sv)
            box.add_widget(B("🏙 BUILD CITY ($20M) — tap map",lambda x:self._bcity(),
                              bg=(0,.25,.1,.95),fg=GREEN,sh=(1,None),fs=sp(11)))

        elif name=="settings":
            box.add_widget(Label(text="SETTINGS",font_size=sp(13),color=GREEN,size_hint=(1,None),height=dp(24)))
            for attr,label in [("show_traj","Missile trajectory"),("show_radar","Radar rings"),("show_int","Interceptor trail")]:
                val=getattr(gs,attr)
                row=BoxLayout(size_hint=(1,None),height=dp(36),spacing=dp(4))
                row.add_widget(Label(text=label,font_size=sp(11),color=WHITE,size_hint=(.7,1)))
                row.add_widget(B("ON" if val else "OFF",lambda x,a=attr:self._tog_s(a),
                                  bg=(0,.3,.12,.95) if val else (.2,.05,.05,.95),
                                  fg=GREEN if val else RED,sh=(.3,1),fs=sp(12)))
                box.add_widget(row)
            mr=BoxLayout(size_hint=(1,None),height=dp(38),spacing=dp(4))
            for mk,ml in [("pvai","PvAI"),("sandbox","Sandbox")]:
                sel=gs.mode==mk
                mr.add_widget(B(ml,lambda x,m=mk:self._smode(m),
                                 bg=(0,.3,.12,.95) if sel else (0,.1,.04,.95),
                                 fg=GREEN if sel else GRAY,sh=(1,1),fs=sp(12)))
            box.add_widget(mr)
        return box

    def _smiss(self,n): self.gs.sel_missile=n; self._cpnl(); self._opnl("missiles")
    def _sdef(self,n):  self.gs.sel_defense=n; self._cpnl(); self._opnl("interceptors")
    def _place(self):   self.gs.placing=self.gs.sel_defense; self.gs.msg(f"Tap map to place {self.gs.sel_defense}",CYAN); self._cpnl()
    def _bcity(self):   self.gs.building=True; self.gs.msg("Tap map to place city",GREEN); self._cpnl()
    def _tog_s(self,a): setattr(self.gs,a,not getattr(self.gs,a)); self._cpnl(); self._opnl("settings")
    def _smode(self,m): self.gs.mode=m; self.gs.msg(f"Mode: {'PvAI' if m=='pvai' else 'Sandbox'}",GREEN); self._cpnl(); self._opnl("settings")

    def _show_pop(self):
        if not self.gs.click: return
        lat,lon=self.gs.click
        cnt=BoxLayout(orientation='vertical',spacing=dp(6),padding=dp(8))
        cnt.add_widget(Label(text=f"LAT  {lat:.4f}°\nLON {lon:.4f}°",font_size=sp(12),color=WHITE,size_hint=(1,None),height=dp(40)))
        row=BoxLayout(size_hint=(1,None),height=dp(42),spacing=dp(6))
        a=Button(text="🎯 ATTACK",background_normal='',background_color=(.3,.03,.03,1),color=RED,font_size=sp(13))
        c=Button(text="✕",background_normal='',background_color=(0,.15,.06,1),color=GREEN,font_size=sp(13))
        a.bind(on_press=lambda x:self._atk(lat,lon)); c.bind(on_press=lambda x:self._dis())
        row.add_widget(a); row.add_widget(c); cnt.add_widget(row)
        pop=Popup(title='',content=cnt,size_hint=(.52,None),height=dp(140),
                  background='',background_color=(0,0,0,0),separator_height=0)
        pop.pos_hint={'center_x':.3,'top':.99}
        with pop.canvas.before:
            Color(0,0,0,.9); pb=Rectangle()
            Color(0,1,.3,.75); pl=Line(width=dp(1.5))
        def u(i,v): pb.pos=i.pos; pb.size=i.size; pl.rectangle=(i.x,i.y,i.width,i.height)
        pop.bind(pos=u,size=u); pop.open(); self._pop=pop

    def _atk(self,lat,lon):
        gs=self.gs; country=gs.player or list(COUNTRIES.keys())[0]
        srcs=gs.cities.get(country,[])
        if srcs:
            src=min(srcs,key=lambda c:haversine(c.lat,c.lon,lat,lon))
            gs.launch(gs.sel_missile,src.lat,src.lon,lat,lon,country)
        self._dis()

    def _dis(self):
        self.gs.click=None
        if self._pop: self._pop.dismiss(); self._pop=None

# ─── COUNTRY SELECT ───────────────────────────────────────────────────────────

class SelScreen(FloatLayout):
    def __init__(self,gs,cb,**kw):
        super().__init__(**kw); self.gs=gs; self.cb=cb
        self.bind(size=self._b,pos=self._b)

    def _b(self,*a):
        self.clear_widgets()
        with self.canvas.before: Color(.02,.06,.02,1); Rectangle(pos=self.pos,size=self.size)
        self.add_widget(Label(text="AIR DEFENSE WARFARE",font_size=sp(20),bold=True,
                               color=GREEN,size_hint=(1,None),height=dp(48),pos_hint={'x':0,'top':1}))
        self.add_widget(Label(text="SELECT YOUR COUNTRY",font_size=sp(13),color=GREEN_DIM,
                               size_hint=(1,None),height=dp(28),
                               pos_hint={'x':0,'top':(self.height-dp(48))/self.height}))
        cols=2; cw=self.width/cols-dp(10); ch=dp(54); pt=self.height-dp(92)
        for i,(name,_) in enumerate(COUNTRIES.items()):
            c=i%cols; r=i//cols
            x=self.x+dp(5)+c*(cw+dp(8)); y=self.y+pt-(r+1)*(ch+dp(5))
            b=Button(text=name,pos=(x,y),size=(cw,ch),size_hint=(None,None),
                     background_normal='',background_color=(0,.18,.07,.95),
                     color=GREEN,font_size=sp(13),bold=True)
            b.bind(on_press=lambda x,n=name:self._pick(n)); self.add_widget(b)
        my=self.y+dp(18); mw=(self.width-dp(70))/2
        self.add_widget(Label(text="MODE:",font_size=sp(11),color=GREEN_DIM,
                               pos=(self.x+dp(5),my),size=(dp(55),dp(34)),size_hint=(None,None)))
        for i,(k,v) in enumerate([("pvai","Player vs AI"),("sandbox","Sandbox")]):
            sel=self.gs.mode==k or (self.gs.mode not in("pvai","sandbox") and k=="pvai")
            mb=Button(text=v,pos=(self.x+dp(62)+i*(mw+dp(4)),my),size=(mw,dp(34)),
                      size_hint=(None,None),background_normal='',
                      background_color=(0,.3,.12,.95) if sel else (0,.1,.04,.95),
                      color=GREEN if sel else GRAY,font_size=sp(11))
            mb.bind(on_press=lambda x,m=k:self._sm(m)); self.add_widget(mb)

    def _pick(self,n):
        self.gs.player=n
        if self.gs.mode not in("pvai","sandbox"): self.gs.mode="pvai"
        self.cb(n)

    def _sm(self,m): self.gs.mode=m; self._b()

# ─── ROOT & APP ───────────────────────────────────────────────────────────────

class Root(FloatLayout):
    def __init__(self,**kw):
        super().__init__(**kw); self.gs=GS(); self._sel()

    def _sel(self):
        self.clear_widgets()
        self.add_widget(SelScreen(self.gs,self._start,size_hint=(1,1),pos_hint={'x':0,'y':0}))

    def _start(self,country):
        self.clear_widgets()
        mw=MapWidget(self.gs,size_hint=(1,1),pos_hint={'x':0,'y':0})
        hd=HUD(self.gs,mw,size_hint=(1,1),pos_hint={'x':0,'y':0})
        self.add_widget(mw); self.add_widget(hd)
        mw.zoom=ZOOM_DEFAULT; mw.center(COUNTRIES[country]["lat"],COUNTRIES[country]["lon"])
        self.gs.msg(f"Commander. You control {country}. Good luck.",GREEN,6.0)

class AirDefenseApp(App):
    def build(self): Window.clearcolor=(.02,.06,.02,1); return Root()
    def on_pause(self): return True
    def on_resume(self): pass

if __name__=="__main__": AirDefenseApp().run()
