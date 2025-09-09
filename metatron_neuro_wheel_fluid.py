# metatron_neuro_wheel_fluid.py
# Metatron lines reworked for FLUID growth & glow, ray-seeded activation.
# Based on prior build; same features (bands, nested sub-cycles, curved links, etc.)
import math, random, time, sys
import pygame

# ---------------- CONFIG (unchanged basics) ----------------
W,H = 1600,1000
BG  = (5,5,8)
FG  = (210,30,30)

FPS_CAP=144
SCENE_SECONDS=360

CENTER_PULSE_HZ=10.0
CENTER_ALPHA=128

BASE_RADIUS=320
RING_WIDTH=2
ALPHA_SOFT=42

INNER_N, MID_N, OUTER_N = 12, 14, 18
INNER_R, MID_R, OUTER_R = int(BASE_RADIUS*0.60), int(BASE_RADIUS*0.78), BASE_RADIUS
INNER_SIZE, MID_SIZE, OUTER_SIZE = 12,12,14

HANDOFF_ANG_THRESH=math.radians(10)
HANDOFF_COOLDOWN=0.6
LINK_TTL=0.9
LINK_SAMPLES=24
LINK_INNER_PULL=0.42

# ---- New fluid Metatron tuning ----
RAYS_ON=True
RAY_COUNT=6
RAY_SWEEP_HZ=0.02
RAY_SPREAD_DEG=12
RAY_SMOOTH=0.06          # low-pass factor (smaller = smoother)
RAY_MICRO_JITTER=0.015   # subtle random wobble

SEG_GROW_SPEED=0.65      # how fast segments extend toward target (px/frame 144fps ref)
SEG_DECAY_SPEED=0.35     # how fast they retract if not targeted
SEG_GLOW_ALPHA=90        # max alpha for center stroke
SEG_SOFT_ALPHA=34        # halo
SEG_GLOW_WIDTHS=(6,3,1)  # wide→thin stacked strokes
SEG_EASE=0.25            # ease-in/out curvature for growth

SHOW_CH_10,SHOW_CH_25,SHOW_CH_50=True,True,True
BURST_LEN=3.0
G_VISUAL=0.60
SPEED_TRIM=1.00
GLYPH_KINDS=6

SEED=None
if SEED is not None: random.seed(SEED)

pygame.init()
screen=pygame.display.set_mode((W,H), pygame.SCALED|pygame.RESIZABLE)
pygame.display.set_caption("Metatron Neuro Wheel — FLUID Lines & Rays")
clock=pygame.time.Clock()
font_small=pygame.font.SysFont("Arial",22)

def cxcy(): return screen.get_width()//2, screen.get_height()//2
def ring_points(cx,cy,r,n,phase=0.0):
    return [(cx+r*math.cos(2*math.pi*i/n+phase), cy+r*math.sin(2*math.pi*i/n+phase)) for i in range(n)]
def draw_circle(surf,color,center,r,width=1,alpha=None):
    s=pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    col=color if alpha is None else (color[0],color[1],color[2],alpha)
    pygame.draw.circle(s,col,center,r,width); surf.blit(s,(0,0))
def poly_points(x,y,sides,r,rot=0.0):
    return [(x+r*math.cos(2*math.pi*i/sides+rot), y+r*math.sin(2*math.pi*i/sides+rot)) for i in range(sides)]
def quad_bezier(p0,p1,p2,samples):
    pts=[]; 
    for i in range(samples+1):
        t=i/float(samples); u=1-t
        pts.append((u*u*p0[0]+2*u*t*p1[0]+t*t*p2[0], u*u*p0[1]+2*u*t*p1[1]+t*t*p2[1]))
    return pts
def angle_of_point(cx,cy,p): return math.atan2(p[1]-cy, p[0]-cx)

# ---------------- Background stack ----------------
def draw_tundra(surf,t):
    W,H=surf.get_width(), surf.get_height()
    sky=pygame.Surface((W,H//2)); sky.fill((12,16,24))
    ground=pygame.Surface((W,H//2)); ground.fill((16,20,24))
    surf.blit(sky,(0,0)); surf.blit(ground,(0,H//2))
    m=pygame.Surface((W,H//2), pygame.SRCALPHA)
    for i in range(6):
        x0=int(W*(i/5)); h=int(H*0.16+0.06*H*math.sin(0.7*i))
        pygame.draw.polygon(m,(150,160,170,24),[(x0-240,H//2),(x0+30,H//2-h),(x0+280,H//2)])
    surf.blit(m,(0,0))
    s=pygame.Surface((W,H), pygame.SRCALPHA)
    for k in range(70):
        a=(k*0.9+0.2*t)%(2*math.pi); r=(t*35+k*28)%(min(W,H)//2)
        x=W//2+int(r*math.cos(a)); y=H//2+int(r*math.sin(a)*0.55)
        pygame.draw.circle(s,(220,220,240,26),(x,y),2)
    surf.blit(s,(0,0))
def draw_reticle(surf,t):
    cx,cy=cxcy(); a=60+int(30*math.sin(t*math.pi*0.8))
    s=pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(s,(FG[0],FG[1],FG[2],a),(cx,cy),36,2)
    pygame.draw.line(s,(FG[0],FG[1],FG[2],a),(cx-48,cy),(cx+48,cy),1)
    pygame.draw.line(s,(FG[0],FG[1],FG[2],a),(cx,cy-48),(cx,cy+48),1)
    surf.blit(s,(0,0))
def draw_g_wheel(surf,t,g=0.60):
    cx,cy=cxcy(); s=pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for i in range(6):
        R=int((100+70*i)*(1+0.18*math.sin(t*0.42)*g))
        pygame.draw.circle(s,(210,30,30,22),(cx,cy),R,1)
    surf.blit(s,(0,0))
def draw_channel_overlay(surf,t,hz,color,radius,alpha=28,boost=0.0):
    cx,cy=cxcy(); s=pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    r=int(radius*(1+0.10*math.sin(t*hz*math.tau)))
    a=int(alpha*(1+1.5*boost))
    pygame.draw.circle(s,(color[0],color[1],color[2],a),(cx,cy),r,2); surf.blit(s,(0,0))

# ---------------- Base rosette ----------------
def draw_base_rings():
    cx,cy=cxcy()
    for k,a in enumerate([ALPHA_SOFT]*3):
        draw_circle(screen,FG,(cx,cy),int(BASE_RADIUS*(0.70+0.15*k)),RING_WIDTH,a)
    petal_r=int(BASE_RADIUS*0.60); node_r=int(BASE_RADIUS*0.36)
    for (x,y) in ring_points(cx,cy,petal_r,6,0.0):
        draw_circle(screen,FG,(int(x),int(y)),node_r,RING_WIDTH,ALPHA_SOFT+8)
    draw_circle(screen,FG,(cx,cy),node_r,RING_WIDTH,ALPHA_SOFT+14)

# ---------------- Fluid Metatron ----------------
def metatron_points(cx,cy,r):
    pts=[(cx,cy)]
    for k in range(6):
        a=2*math.pi*k/6; pts.append((cx+r*math.cos(a), cy+r*math.sin(a)))
    for k in range(6):
        a=2*math.pi*k/6+math.pi/6
        pts.append((cx+r*math.sqrt(3)*math.cos(a), cy+r*math.sqrt(3)*math.sin(a)))
    return pts
def all_segments(pts):
    segs=[]
    for i in range(len(pts)):
        for j in range(i+1,len(pts)):
            segs.append((pts[i],pts[j]))
    return segs

class FluidMetatron:
    def __init__(self):
        self.cx,self.cy=cxcy()
        self.base_r=int(BASE_RADIUS*0.58)
        self.pts=metatron_points(self.cx,self.cy,self.base_r)
        self.segs=all_segments(self.pts)
        # state per segment: progress in [0..1] of visible length
        self.state=[0.0]*len(self.segs)
        self.target=[0.0]*len(self.segs)    # desired progress
        self.ray_angles=[i*math.tau/RAY_COUNT for i in range(RAY_COUNT)]
        self.smooth_angles=self.ray_angles[:]

    def update_rays(self, t):
        # desired angles (pure sweep)
        base = t*RAY_SWEEP_HZ*math.tau
        desired=[(base+i*math.tau/RAY_COUNT)% (2*math.pi) for i in range(RAY_COUNT)]
        # low-pass + micro jitter
        for i in range(RAY_COUNT):
            jitter=(random.random()-0.5)*RAY_MICRO_JITTER
            d=math.atan2(math.sin(desired[i]-self.smooth_angles[i]), math.cos(desired[i]-self.smooth_angles[i]))
            self.smooth_angles[i]=(self.smooth_angles[i]+d*RAY_SMOOTH + jitter)%(2*math.pi)

    def gate(self, p):
        # distance (angle) to nearest smoothed ray
        ang=angle_of_point(self.cx,self.cy,p)
        d=min(abs(math.atan2(math.sin(ang-r), math.cos(ang-r))) for r in self.smooth_angles)
        return d < math.radians(RAY_SPREAD_DEG), 1.0 - min(1.0, d/math.radians(RAY_SPREAD_DEG))

    def step_targets(self):
        # for each segment, set target visibility by whether its midpoint is near any ray
        for i,(a,b) in enumerate(self.segs):
            mid=((a[0]+b[0])/2.0, (a[1]+b[1])/2.0)
            ok,k=self.gate(mid)
            # more weight near the center (shorter segs = less visual clutter)
            dist=( (mid[0]-self.cx)**2 + (mid[1]-self.cy)**2 )**0.5
            w=0.65 + 0.35*max(0.0, 1.0 - dist/(self.base_r*1.4))
            self.target[i]=k*w if ok else 0.0

    def ease(self,x):
        # smoothstep-ish; sharper with SEG_EASE
        a=max(0.0,min(1.0,x))
        return a**(1+SEG_EASE*2) / (a**(1+SEG_EASE*2) + (1-a)**(1+SEG_EASE*2) + 1e-6)

    def update_progress(self, dt):
        # grow/decay toward target smoothly
        for i in range(len(self.segs)):
            trg=self.target[i]; cur=self.state[i]
            if trg>cur:
                cur=min(1.0, cur + SEG_GROW_SPEED*dt*self.ease(1-cur))
            else:
                cur=max(0.0, cur - SEG_DECAY_SPEED*dt*self.ease(cur))
            self.state[i]=cur

    def draw(self, surf):
        base = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        # faint net (very soft)
        for a,b in self.segs:
            pygame.draw.line(base,(FG[0],FG[1],FG[2],22),a,b,1)
        surf.blit(base,(0,0))

        hi = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        for (a,b), prog in zip(self.segs, self.state):
            if prog<=0: continue
            # draw partial line A -> lerp(A,B,prog)
            px = a[0] + (b[0]-a[0])*prog
            py = a[1] + (b[1]-a[1])*prog
            p_end=(px,py)
            # halo + glow + core strokes
            widths=SEG_GLOW_WIDTHS
            alphas=(SEG_SOFT_ALPHA, int(SEG_SOFT_ALPHA*1.8), SEG_GLOW_ALPHA)
            for w,al in zip(widths, alphas):
                pygame.draw.line(hi,(255,180,180,al),a,p_end,w)
        surf.blit(hi,(0,0))

# ---------------- Rings/Glyphs & links ----------------
def draw_ring_icons(pts,size,kinds,alpha=108):
    s=pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    for i,(x,y) in enumerate(pts):
        g=kinds[i]%GLYPH_KINDS; col=(FG[0],FG[1],FG[2],alpha)
        pygame.draw.circle(s,col,(int(x),int(y)),size,2); rot=i*0.3
        if g==0: pygame.draw.polygon(s,col,poly_points(x,y,3,int(size*0.9),rot),2)
        elif g==1: pygame.draw.polygon(s,col,poly_points(x,y,6,int(size*0.9),rot),2)
        elif g==2:
            pygame.draw.polygon(s,col,poly_points(x,y,3,int(size*0.9),rot),2)
            pygame.draw.polygon(s,col,poly_points(x,y,3,int(size*0.9),rot+math.pi/3),2)
        elif g==3:
            pygame.draw.line(s,col,(x-size*0.8,y),(x+size*0.8,y),2)
            pygame.draw.line(s,col,(x,y-size*0.8),(x,y+size*0.8),2)
        elif g==4:
            for k in range(6):
                a=rot+2*math.pi*k/6
                pygame.draw.circle(s,col,(int(x+size*0.7*math.cos(a)), int(y+size*0.7*math.sin(a))),2,2)
        else:
            pygame.draw.arc(s,col,(x-size,y-size,2*size,2*size),rot,rot+math.pi*0.8,2)
    screen.blit(s,(0,0))
def draw_links(surf,links):
    now=time.time(); s=pygame.Surface(surf.get_size(), pygame.SRCALPHA); cx,cy=cxcy()
    for ev in list(links):
        life=(now-ev["t0"])/LINK_TTL
        if life>=1.0: links.remove(ev); continue
        p0=ev["p_in"]; p2=ev["p_out"]; mid=((p0[0]+p2[0])/2.0,(p0[1]+p2[1])/2.0)
        ctrl=(mid[0]+(cx-mid[0])*LINK_INNER_PULL, mid[1]+(cy-mid[1])*LINK_INNER_PULL)
        pts=quad_bezier(p0,ctrl,p2,LINK_SAMPLES); a=int(150*(1.0-life))
        for i in range(len(pts)-1):
            pygame.draw.line(s,(FG[0],FG[1],FG[2],a),pts[i],pts[i+1],2)
    surf.blit(s,(0,0))

def draw_center_pulse(surf,t,hz):
    cx,cy=cxcy()
    r=int(104+26*math.sin(t*hz*math.tau))
    a=max(0,min(255,int(CENTER_ALPHA+60*math.sin(t*hz*math.tau+math.pi/2))))
    s=pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(s,(200,40,40,a),(cx,cy),max(34,r)); surf.blit(s,(0,0))

# ---------------- Band scheduler (same logic as previous) ----------------
BAND_SCHEDULE=[("gamma",40.0,15.0), ("alpha",10.0,60.0), ("beta",14.0,60.0), ("theta",8.0,60.0)]
SUBCYCLE_OUTER=[("alpha",10.0,18.0),("beta",14.0,18.0),("theta",8.0,18.0)]
SUBCYCLE_MID  =[("alpha",10.0,18.0),("beta",14.0,18.0),("theta",8.0,18.0)]
def band_params(name):
    if name=="gamma": inner=0.35; mid=0.35*0.9; outer=-0.35*1.05; ch=(False,True,False)
    elif name=="alpha": inner=0.22; mid=0.22*0.95; outer=-0.22*1.05; ch=(True,True,False)
    elif name=="beta":  inner=0.27; mid=0.27*0.95; outer=-0.27*1.05; ch=(True,False,False)
    else:               inner=0.18; mid=0.18*0.95; outer=-0.18*1.05; ch=(False,True,True)
    return inner,mid,outer,ch

# ---------------- Main ----------------
def run():
    global CENTER_PULSE_HZ, SPEED_TRIM
    start=time.time()
    inner_kinds=[i%GLYPH_KINDS for i in range(INNER_N)]
    mid_kinds=[(i*3)%GLYPH_KINDS for i in range(MID_N)]
    outer_kinds=[(i*2)%GLYPH_KINDS for i in range(OUTER_N)]
    inner_last=[0.0]*INNER_N; mid_last=[0.0]*MID_N; outer_last=[0.0]*OUTER_N
    links=[]

    schedule_index=0; sub_phase=None; sub_index=0
    band_start_t=time.time(); burst_until=band_start_t+BURST_LEN

    # Fluid Metatron instance
    FM=FluidMetatron()

    def hud():
        return font_small.render(
            f"ESC quit  R restart  SPACE emergency   +/- pulse {CENTER_PULSE_HZ:.1f}Hz   [ / ] speed {SPEED_TRIM:.2f}   1/2/3 overlays   L rays",
            True,(120,120,135))
    hint=hud()

    while True:
        dt=clock.tick(FPS_CAP)/1000.0
        now=time.time(); t=now-start

        for e in pygame.event.get():
            if e.type==pygame.QUIT: pygame.quit(); sys.exit(0)
            if e.type==pygame.KEYDOWN:
                if e.key==pygame.K_ESCAPE: pygame.quit(); sys.exit(0)
                elif e.key in (pygame.K_PLUS, pygame.K_EQUALS): CENTER_PULSE_HZ=min(24.0,CENTER_PULSE_HZ+0.5); hint=hud()
                elif e.key in (pygame.K_MINUS, pygame.K_UNDERSCORE): CENTER_PULSE_HZ=max(1.0,CENTER_PULSE_HZ-0.5); hint=hud()
                elif e.key==pygame.K_LEFTBRACKET: SPEED_TRIM=max(0.6,SPEED_TRIM-0.05); hint=hud()
                elif e.key==pygame.K_RIGHTBRACKET: SPEED_TRIM=min(1.6,SPEED_TRIM+0.05); hint=hud()
                elif e.key==pygame.K_1: globals()['SHOW_CH_10']=not SHOW_CH_10; hint=hud()
                elif e.key==pygame.K_2: globals()['SHOW_CH_25']=not SHOW_CH_25; hint=hud()
                elif e.key==pygame.K_3: globals()['SHOW_CH_50']=not SHOW_CH_50; hint=hud()
                elif e.key==pygame.K_l: globals()['RAYS_ON']=not RAYS_ON; hint=hud()
                elif e.key==pygame.K_SPACE:
                    screen.fill((0,0,0)); pygame.display.flip()
                    while True:
                        f=pygame.event.wait()
                        if f.type==pygame.KEYDOWN and f.key==pygame.K_r: return
                elif e.key==pygame.K_r: return

        band_name,band_freq,band_dur=BAND_SCHEDULE[schedule_index]
        CENTER_PULSE_HZ=band_freq
        time_in_band=now-band_start_t
        burst_boost=max(0.0, min(1.0,(burst_until-now)/BURST_LEN)) if now<burst_until else 0.0

        if band_name=="theta":
            if sub_phase is None:
                sub_phase="outer"; sub_index=0; sub_start=now
            sub_list = SUBCYCLE_OUTER if sub_phase=="outer" else SUBCYCLE_MID
            s_name,s_freq,s_dur=sub_list[sub_index]
            if now-sub_start>=s_dur:
                sub_index+=1
                if sub_index>=len(sub_list):
                    if sub_phase=="outer":
                        sub_phase="mid"; sub_index=0
                    else:
                        sub_phase="done"
                sub_start=now
            base_inner,base_mid,base_outer,chmask=band_params("theta")
            if sub_phase=="outer": _,_,o,_=band_params(s_name); base_outer=o
            elif sub_phase=="mid": _,m,_,_=band_params(s_name); base_mid=m
            inner_hz=base_inner*SPEED_TRIM; mid_hz=base_mid*SPEED_TRIM; outer_hz=base_outer*SPEED_TRIM
            ch10,ch25,ch50=chmask
        else:
            inner_hz,mid_hz,outer_hz,chmask=band_params(band_name)
            inner_hz*=SPEED_TRIM; mid_hz*=SPEED_TRIM; outer_hz*=SPEED_TRIM
            ch10,ch25,ch50=chmask

        if time_in_band>=band_dur and band_name!="theta":
            schedule_index=min(len(BAND_SCHEDULE)-1, schedule_index+1)
            band_start_t=now; burst_until=now+BURST_LEN
        if band_name=="theta" and sub_phase=="done" and time_in_band>=band_dur:
            schedule_index=0; band_start_t=now; sub_phase=None; burst_until=now+BURST_LEN

        phi_inner=2*math.pi*inner_hz*(now-start)
        phi_mid  =2*math.pi*mid_hz  *(now-start)
        phi_outer=2*math.pi*outer_hz*(now-start)

        # DRAW
        screen.fill(BG)
        draw_tundra(screen,t); draw_g_wheel(screen,t,G_VISUAL)
        if SHOW_CH_10 and ch10: draw_channel_overlay(screen,t,1.0,(200,200,200),100,24,burst_boost)
        if SHOW_CH_25 and ch25: draw_channel_overlay(screen,t,10.0,(0,200,200),180,30,burst_boost)
        if SHOW_CH_50 and ch50: draw_channel_overlay(screen,t,8.0,(200,0,200),260,36,burst_boost)

        draw_base_rings()

        # --- FLUID METATRON ---
        if RAYS_ON:
            FM.update_rays(now-start)
        FM.step_targets()
        FM.update_progress(dt)
        FM.draw(screen)
        lit_ray_angles = FM.smooth_angles if RAYS_ON else []

        # RINGS
        cx,cy=cxcy()
        inner_pts=ring_points(cx,cy,INNER_R,INNER_N,phi_inner)
        mid_pts  =ring_points(cx,cy,MID_R,  MID_N,  phi_mid)
        outer_pts=ring_points(cx,cy,OUTER_R,OUTER_N,phi_outer)

        draw_ring_icons(inner_pts,INNER_SIZE,inner_kinds,alpha=104)
        draw_ring_icons(mid_pts,  MID_SIZE,  mid_kinds,  alpha=98)
        draw_ring_icons(outer_pts,OUTER_SIZE,outer_kinds,alpha=132)

        def gate_by_rays(p):
            if not RAYS_ON: return True
            ang=angle_of_point(cx,cy,p)
            d=min(abs(math.atan2(math.sin(ang-r), math.cos(ang-r))) for r in lit_ray_angles) if lit_ray_angles else 10.0
            return d < math.radians(RAY_SPREAD_DEG)

        nowT=time.time()
        # inner↔outer
        for oi,(ox,oy) in enumerate(outer_pts):
            o_ang=math.atan2(oy-cy,ox-cx)
            ni=round(((o_ang - phi_inner)%(2*math.pi))/(2*math.pi/INNER_N))%INNER_N
            ix,iy=inner_pts[ni]; i_ang=math.atan2(iy-cy,ix-cx)
            d=math.atan2(math.sin(o_ang-i_ang), math.cos(o_ang-i_ang))
            if abs(d)<HANDOFF_ANG_THRESH and (nowT-inner_last[ni])>HANDOFF_COOLDOWN and gate_by_rays(((ix+ox)/2,(iy+oy)/2)):
                outer_kinds[oi]=inner_kinds[ni]; inner_kinds[ni]=(inner_kinds[ni]+1)%GLYPH_KINDS
                inner_last[ni]=nowT; links.append({"t0":nowT,"p_in":(ix,iy),"p_out":(ox,oy)})
        # inner↔mid
        for mi,(mx,my) in enumerate(mid_pts):
            m_ang=math.atan2(my-cy,mx-cx)
            ni=round(((m_ang - phi_inner)%(2*math.pi))/(2*math.pi/INNER_N))%INNER_N
            ix,iy=inner_pts[ni]; i_ang=math.atan2(iy-cy,ix-cx)
            d=math.atan2(math.sin(m_ang-i_ang), math.cos(m_ang-i_ang))
            if abs(d)<HANDOFF_ANG_THRESH and (nowT-inner_last[ni])>HANDOFF_COOLDOWN and gate_by_rays(((ix+mx)/2,(iy+my)/2)):
                mid_kinds[mi]=inner_kinds[ni]; inner_kinds[ni]=(inner_kinds[ni]+1)%GLYPH_KINDS
                inner_last[ni]=nowT; links.append({"t0":nowT,"p_in":(ix,iy),"p_out":(mx,my)})

        draw_links(screen,links)
        draw_center_pulse(screen,t,CENTER_PULSE_HZ); draw_reticle(screen,t)

        hint=font_small.render(
            f"{BAND_SCHEDULE[schedule_index][0].upper()}   speed x{SPEED_TRIM:.2f}", True,(120,120,135))
        screen.blit(hint,(16,screen.get_height()-36))
        pygame.display.flip()

        if t>=SCENE_SECONDS: break

while True:
    run()
