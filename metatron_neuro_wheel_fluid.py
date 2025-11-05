import math
import random
import sys
import time
from dataclasses import dataclass
from typing import Callable, List, Sequence, Set, Tuple

import pygame


Color = Tuple[int, int, int]
Vec2 = Tuple[float, float]
Segment = Tuple[Vec2, Vec2]


@dataclass
class BandStage:
    name: str
    frequency: float
    duration: float


@dataclass
class WheelConfig:
    width: int = 1600
    height: int = 1000
    background: Color = (5, 5, 8)
    foreground: Color = (210, 30, 30)
    fps_cap: int = 144
    scene_seconds: int = 360
    base_radius: int = 320
    inner_radius_ratio: float = 0.60
    mid_radius_ratio: float = 0.78
    outer_radius_ratio: float = 1.0
    ring_width: int = 2
    alpha_soft: int = 42
    inner_nodes: int = 12
    mid_nodes: int = 14
    outer_nodes: int = 18
    inner_size: int = 12
    mid_size: int = 12
    outer_size: int = 14
    handoff_angle_threshold: float = math.radians(10)
    handoff_cooldown: float = 0.6
    link_ttl: float = 0.9
    link_samples: int = 24
    link_inner_pull: float = 0.42
    burst_length: float = 3.0
    g_visual: float = 0.60
    speed_trim: float = 1.0
    glyph_kinds: int = 6
    center_pulse_hz: float = 10.0
    center_alpha: int = 128
    show_ch_10: bool = True
    show_ch_25: bool = True
    show_ch_50: bool = True
    font_family: str = "Arial"
    font_size: int = 22
    min_width: int = 960
    min_height: int = 600
    scale_presets: Tuple[float, ...] = (0.75, 1.0, 1.25, 1.5)
    default_scale_index: int = 1


@dataclass
class FluidMetatronConfig:
    ray_count: int = 6
    ray_sweep_hz: float = 0.02
    ray_spread_deg: float = 12
    ray_smooth: float = 0.06
    ray_micro_jitter: float = 0.015
    seg_grow_speed: float = 0.65
    seg_decay_speed: float = 0.35
    seg_glow_alpha: int = 90
    seg_soft_alpha: int = 34
    seg_glow_widths: Sequence[int] = (6, 3, 1)
    seg_ease: float = 0.25


DEFAULT_BAND_SCHEDULE: Sequence[BandStage] = (
    BandStage("gamma", 40.0, 15.0),
    BandStage("alpha", 10.0, 60.0),
    BandStage("beta", 14.0, 60.0),
    BandStage("theta", 8.0, 60.0),
)

DEFAULT_SUBCYCLE_OUTER: Sequence[BandStage] = (
    BandStage("alpha", 10.0, 18.0),
    BandStage("beta", 14.0, 18.0),
    BandStage("theta", 8.0, 18.0),
)

DEFAULT_SUBCYCLE_MID: Sequence[BandStage] = (
    BandStage("alpha", 10.0, 18.0),
    BandStage("beta", 14.0, 18.0),
    BandStage("theta", 8.0, 18.0),
)


def cxcy(surface: pygame.Surface) -> Tuple[int, int]:
    return surface.get_width() // 2, surface.get_height() // 2
def ring_points(cx: float, cy: float, radius: float, count: int, phase: float = 0.0) -> List[Vec2]:
    return [
        (
            cx + radius * math.cos(2 * math.pi * i / count + phase),
            cy + radius * math.sin(2 * math.pi * i / count + phase),
        )
        for i in range(count)
    ]


def draw_circle(surface: pygame.Surface, color: Color, center: Tuple[int, int], radius: int, width: int = 1, alpha: int | None = None) -> None:
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    r, g, b = color
    col = (r, g, b, alpha) if alpha is not None else (r, g, b)
    pygame.draw.circle(overlay, col, center, radius, width)
    surface.blit(overlay, (0, 0))


def poly_points(x: float, y: float, sides: int, radius: float, rotation: float = 0.0) -> List[Vec2]:
    return [
        (
            x + radius * math.cos(2 * math.pi * i / sides + rotation),
            y + radius * math.sin(2 * math.pi * i / sides + rotation),
        )
        for i in range(sides)
    ]


def quad_bezier(p0: Vec2, p1: Vec2, p2: Vec2, samples: int) -> List[Vec2]:
    points: List[Vec2] = []
    for i in range(samples + 1):
        t = i / float(samples)
        u = 1 - t
        points.append(
            (
                u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
            )
        )
    return points


def angle_of_point(cx: float, cy: float, point: Vec2) -> float:
    return math.atan2(point[1] - cy, point[0] - cx)


# ---------------- Background stack ----------------
def draw_tundra(surface: pygame.Surface, t: float) -> None:
    width, height = surface.get_width(), surface.get_height()
    sky = pygame.Surface((width, height // 2))
    sky.fill((12, 16, 24))
    ground = pygame.Surface((width, height // 2))
    ground.fill((16, 20, 24))
    surface.blit(sky, (0, 0))
    surface.blit(ground, (0, height // 2))

    mountains = pygame.Surface((width, height // 2), pygame.SRCALPHA)
    for i in range(6):
        base_x = int(width * (i / 5))
        peak_height = int(height * 0.16 + 0.06 * height * math.sin(0.7 * i))
        pygame.draw.polygon(
            mountains,
            (150, 160, 170, 24),
            [(base_x - 240, height // 2), (base_x + 30, height // 2 - peak_height), (base_x + 280, height // 2)],
        )
    surface.blit(mountains, (0, 0))

    stars = pygame.Surface((width, height), pygame.SRCALPHA)
    for k in range(70):
        angle = (k * 0.9 + 0.2 * t) % (2 * math.pi)
        radius = (t * 35 + k * 28) % (min(width, height) // 2)
        x = width // 2 + int(radius * math.cos(angle))
        y = height // 2 + int(radius * math.sin(angle) * 0.55)
        pygame.draw.circle(stars, (220, 220, 240, 26), (x, y), 2)
    surface.blit(stars, (0, 0))


def draw_reticle(surface: pygame.Surface, t: float, color: Color) -> None:
    cx, cy = cxcy(surface)
    alpha = 60 + int(30 * math.sin(t * math.pi * 0.8))
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(overlay, (*color, alpha), (cx, cy), 36, 2)
    pygame.draw.line(overlay, (*color, alpha), (cx - 48, cy), (cx + 48, cy), 1)
    pygame.draw.line(overlay, (*color, alpha), (cx, cy - 48), (cx, cy + 48), 1)
    surface.blit(overlay, (0, 0))


def draw_g_wheel(surface: pygame.Surface, t: float, color: Color, strength: float) -> None:
    cx, cy = cxcy(surface)
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for i in range(6):
        radius = int((100 + 70 * i) * (1 + 0.18 * math.sin(t * 0.42) * strength))
        pygame.draw.circle(overlay, (*color, 22), (cx, cy), radius, 1)
    surface.blit(overlay, (0, 0))


def draw_channel_overlay(surface: pygame.Surface, t: float, hz: float, color: Color, radius: int, alpha: int = 28, boost: float = 0.0) -> None:
    cx, cy = cxcy(surface)
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    radius_scaled = int(radius * (1 + 0.10 * math.sin(t * hz * math.tau)))
    alpha_scaled = int(alpha * (1 + 1.5 * boost))
    pygame.draw.circle(overlay, (*color, alpha_scaled), (cx, cy), radius_scaled, 2)
    surface.blit(overlay, (0, 0))


# ---------------- Base rosette ----------------
def draw_base_rings(surface: pygame.Surface, config: WheelConfig) -> None:
    cx, cy = cxcy(surface)
    base_radius = config.base_radius
    for idx in range(3):
        draw_circle(
            surface,
            config.foreground,
            (cx, cy),
            int(base_radius * (0.70 + 0.15 * idx)),
            config.ring_width,
            config.alpha_soft,
        )
    petal_radius = int(base_radius * 0.60)
    node_radius = int(base_radius * 0.36)
    for (x, y) in ring_points(cx, cy, petal_radius, 6, 0.0):
        draw_circle(surface, config.foreground, (int(x), int(y)), node_radius, config.ring_width, config.alpha_soft + 8)
    draw_circle(surface, config.foreground, (cx, cy), node_radius, config.ring_width, config.alpha_soft + 14)

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
    def __init__(self, center_provider: Callable[[], Tuple[int, int]], base_radius: int, color: Color, config: FluidMetatronConfig):
        self.get_center = center_provider
        self.base_radius = int(base_radius * 0.58)
        self.color = color
        self.config = config
        self.cx, self.cy = self.get_center()
        self.pts = metatron_points(self.cx, self.cy, self.base_radius)
        self.segments = all_segments(self.pts)
        self.state = [0.0] * len(self.segments)
        self.target = [0.0] * len(self.segments)
        ray_count = max(1, config.ray_count)
        self.ray_angles = [i * math.tau / ray_count for i in range(ray_count)]
        self.smooth_angles = list(self.ray_angles)

    def refresh_geometry(self) -> None:
        new_cx, new_cy = self.get_center()
        if (new_cx, new_cy) == (self.cx, self.cy):
            return
        dx = new_cx - self.cx
        dy = new_cy - self.cy
        self.cx, self.cy = new_cx, new_cy
        self.pts = [(x + dx, y + dy) for (x, y) in self.pts]
        self.segments = [((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy)) for (a, b) in self.segments]

    def update_rays(self, t: float) -> None:
        ray_count = len(self.ray_angles)
        if ray_count == 0:
            return
        base = t * self.config.ray_sweep_hz * math.tau
        desired = [(base + i * math.tau / ray_count) % (2 * math.pi) for i in range(ray_count)]
        for i in range(ray_count):
            jitter = (random.random() - 0.5) * self.config.ray_micro_jitter
            delta = math.atan2(
                math.sin(desired[i] - self.smooth_angles[i]),
                math.cos(desired[i] - self.smooth_angles[i]),
            )
            self.smooth_angles[i] = (self.smooth_angles[i] + delta * self.config.ray_smooth + jitter) % (2 * math.pi)

    def gate(self, point: Vec2) -> Tuple[bool, float]:
        ray_count = len(self.smooth_angles)
        if ray_count == 0:
            return True, 1.0
        ang = angle_of_point(self.cx, self.cy, point)
        spread = math.radians(self.config.ray_spread_deg)
        dist = min(abs(math.atan2(math.sin(ang - ray), math.cos(ang - ray))) for ray in self.smooth_angles)
        return dist < spread, 1.0 - min(1.0, dist / spread)

    def step_targets(self) -> None:
        self.refresh_geometry()
        for idx, (a, b) in enumerate(self.segments):
            midpoint = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
            ok, weight = self.gate(midpoint)
            dist = ((midpoint[0] - self.cx) ** 2 + (midpoint[1] - self.cy) ** 2) ** 0.5
            falloff = 0.65 + 0.35 * max(0.0, 1.0 - dist / (self.base_radius * 1.4))
            self.target[idx] = weight * falloff if ok else 0.0

    def ease(self, value: float) -> float:
        a = max(0.0, min(1.0, value))
        power = 1 + self.config.seg_ease * 2
        return a**power / (a**power + (1 - a) ** power + 1e-6)

    def update_progress(self, dt: float) -> None:
        for idx in range(len(self.segments)):
            target = self.target[idx]
            current = self.state[idx]
            if target > current:
                current = min(1.0, current + self.config.seg_grow_speed * dt * self.ease(1 - current))
            else:
                current = max(0.0, current - self.config.seg_decay_speed * dt * self.ease(current))
            self.state[idx] = current

    def draw(self, surface: pygame.Surface) -> None:
        base = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        r, g, b = self.color
        for start, end in self.segments:
            pygame.draw.line(base, (r, g, b, 22), start, end, 1)
        surface.blit(base, (0, 0))

        highlight = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        alphas = (
            self.config.seg_soft_alpha,
            int(self.config.seg_soft_alpha * 1.8),
            self.config.seg_glow_alpha,
        )
        for (start, end), progress in zip(self.segments, self.state):
            if progress <= 0:
                continue
            px = start[0] + (end[0] - start[0]) * progress
            py = start[1] + (end[1] - start[1]) * progress
            endpoint = (px, py)
            for width, alpha in zip(self.config.seg_glow_widths, alphas):
                pygame.draw.line(highlight, (255, 180, 180, alpha), start, endpoint, width)
        surface.blit(highlight, (0, 0))

# ---------------- Rings/Glyphs & links ----------------
def draw_ring_icons(
    surface: pygame.Surface,
    points: Sequence[Vec2],
    size: int,
    kinds: Sequence[int],
    glyph_count: int,
    color: Color,
    alpha: int = 108,
    rotations: Sequence[float] | None = None,
    flips: Sequence[int] | None = None,
) -> None:
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    tint = (*color, alpha)
    for idx, (x, y) in enumerate(points):
        glyph = kinds[idx] % glyph_count if glyph_count else 0
        pygame.draw.circle(overlay, tint, (int(x), int(y)), size, 2)
        rotation = rotations[idx] if rotations and idx < len(rotations) else idx * 0.3
        flip = flips[idx] if flips and idx < len(flips) else 1
        if glyph == 0:
            offset = math.pi / 6 if flip < 0 else 0.0
            pygame.draw.polygon(overlay, tint, poly_points(x, y, 3, int(size * 0.9), rotation + offset), 2)
        elif glyph == 1:
            offset = math.pi / 12 if flip < 0 else 0.0
            pygame.draw.polygon(overlay, tint, poly_points(x, y, 6, int(size * 0.9), rotation + offset), 2)
        elif glyph == 2:
            pygame.draw.polygon(overlay, tint, poly_points(x, y, 3, int(size * 0.9), rotation), 2)
            pygame.draw.polygon(
                overlay,
                tint,
                poly_points(x, y, 3, int(size * 0.9), rotation + (math.pi / 3 if flip >= 0 else math.pi / 2)),
                2,
            )
        elif glyph == 3:
            span = size * 0.8
            if flip >= 0:
                pygame.draw.line(overlay, tint, (x - span, y), (x + span, y), 2)
                pygame.draw.line(overlay, tint, (x, y - span), (x, y + span), 2)
            else:
                pygame.draw.line(overlay, tint, (x - span, y - span), (x + span, y + span), 2)
                pygame.draw.line(overlay, tint, (x - span, y + span), (x + span, y - span), 2)
        elif glyph == 4:
            for k in range(6):
                angle = rotation + flip * 2 * math.pi * k / 6
                pygame.draw.circle(overlay, tint, (int(x + size * 0.7 * math.cos(angle)), int(y + size * 0.7 * math.sin(angle))), 2, 2)
        else:
            sweep = math.pi * 0.8
            if flip >= 0:
                start = rotation
                end = rotation + sweep
            else:
                end = rotation
                start = rotation - sweep
            if end < start:
                start, end = end, start
            pygame.draw.arc(overlay, tint, (x - size, y - size, 2 * size, 2 * size), start, end, 2)
    surface.blit(overlay, (0, 0))


def random_glyph_index(glyph_count: int, forbidden: Set[int] | Sequence[int] | None = None) -> int:
    glyph_count = max(1, glyph_count)
    if glyph_count == 1:
        return 0
    banned = {value % glyph_count for value in forbidden or [] if glyph_count > 1}
    choices = [value for value in range(glyph_count) if value not in banned]
    if not choices:
        choices = list(range(glyph_count))
    return random.choice(choices)


def build_glyph_ring(count: int, glyph_count: int) -> Tuple[List[int], List[float], List[int]]:
    glyph_count = max(1, glyph_count)
    kinds: List[int] = []
    rotations: List[float] = []
    flips: List[int] = []
    for idx in range(count):
        forbidden: Set[int] = set()
        if glyph_count > 1 and kinds:
            forbidden.add(kinds[-1])
        if glyph_count > 2 and idx == count - 1 and kinds:
            forbidden.add(kinds[0])
        kind = random_glyph_index(glyph_count, forbidden)
        kinds.append(kind)
        rotations.append(random.random() * math.tau)
        flips.append(1 if idx % 2 == 0 else -1)
    return kinds, rotations, flips


def advance_glyph_ring_slot(
    kinds: List[int], rotations: List[float], flips: List[int], index: int, glyph_count: int
) -> None:
    if not kinds:
        return
    glyph_count = max(1, glyph_count)
    current = kinds[index] if glyph_count > 0 else 0
    neighbours: Set[int] = set()
    if glyph_count > 1:
        neighbours.add(current)
    if glyph_count > 2 and len(kinds) > 1:
        neighbours.add(kinds[(index - 1) % len(kinds)])
        neighbours.add(kinds[(index + 1) % len(kinds)])
    kinds[index] = random_glyph_index(glyph_count, neighbours)
    rotations[index] = random.random() * math.tau
    if flips:
        flips[index] = -flips[index] if flips[index] != 0 else 1


def draw_links(surface: pygame.Surface, links: List[dict], config: WheelConfig, color: Color) -> None:
    now = time.time()
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    cx, cy = cxcy(surface)
    for event in list(links):
        life = (now - event["t0"]) / config.link_ttl
        if life >= 1.0:
            links.remove(event)
            continue
        p0 = event["p_in"]
        p2 = event["p_out"]
        mid = ((p0[0] + p2[0]) / 2.0, (p0[1] + p2[1]) / 2.0)
        ctrl = (mid[0] + (cx - mid[0]) * config.link_inner_pull, mid[1] + (cy - mid[1]) * config.link_inner_pull)
        pts = quad_bezier(p0, ctrl, p2, config.link_samples)
        alpha = int(150 * (1.0 - life))
        for i in range(len(pts) - 1):
            pygame.draw.line(overlay, (*color, alpha), pts[i], pts[i + 1], 2)
    surface.blit(overlay, (0, 0))


def draw_center_pulse(surface: pygame.Surface, t: float, hz: float, config: WheelConfig) -> None:
    cx, cy = cxcy(surface)
    radius = int(104 + 26 * math.sin(t * hz * math.tau))
    alpha = max(0, min(255, int(config.center_alpha + 60 * math.sin(t * hz * math.tau + math.pi / 2))))
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    pygame.draw.circle(overlay, (200, 40, 40, alpha), (cx, cy), max(34, radius))
    surface.blit(overlay, (0, 0))

# ---------------- Band scheduler (same logic as previous) ----------------
BAND_SCHEDULE = DEFAULT_BAND_SCHEDULE
SUBCYCLE_OUTER = DEFAULT_SUBCYCLE_OUTER
SUBCYCLE_MID = DEFAULT_SUBCYCLE_MID


def band_params(name: str) -> Tuple[float, float, float, Tuple[bool, bool, bool]]:
    if name == "gamma":
        inner = 0.35
        mid = 0.35 * 0.9
        outer = -0.35 * 1.05
        ch = (False, True, False)
    elif name == "alpha":
        inner = 0.22
        mid = 0.22 * 0.95
        outer = -0.22 * 1.05
        ch = (True, True, False)
    elif name == "beta":
        inner = 0.27
        mid = 0.27 * 0.95
        outer = -0.27 * 1.05
        ch = (True, False, False)
    else:
        inner = 0.18
        mid = 0.18 * 0.95
        outer = -0.18 * 1.05
        ch = (False, True, True)
    return inner, mid, outer, ch

# ---------------- Main ----------------


@dataclass
class WheelState:
    center_pulse_hz: float
    speed_trim: float
    show_ch_10: bool
    show_ch_25: bool
    show_ch_50: bool
    rays_on: bool = True
    scale_index: int = 0
    scale_menu_open: bool = False


class NeuroWheelApp:
    def __init__(
        self,
        wheel_config: WheelConfig | None = None,
        metatron_config: FluidMetatronConfig | None = None,
        band_schedule: Sequence[BandStage] = BAND_SCHEDULE,
        subcycle_outer: Sequence[BandStage] = SUBCYCLE_OUTER,
        subcycle_mid: Sequence[BandStage] = SUBCYCLE_MID,
        seed: int | None = None,
    ) -> None:
        self.config = wheel_config or WheelConfig()
        self.metatron_config = metatron_config or FluidMetatronConfig()
        self.band_schedule = list(band_schedule)
        self.subcycle_outer = list(subcycle_outer)
        self.subcycle_mid = list(subcycle_mid)
        self.scale_presets = tuple(scale for scale in self.config.scale_presets if scale > 0)
        if not self.scale_presets:
            self.scale_presets = (1.0,)
        self.default_scale_index = max(0, min(self.config.default_scale_index, len(self.scale_presets) - 1))
        self.base_width = self.config.width
        self.base_height = self.config.height
        self.base_radius = self.config.base_radius
        self.base_inner_size = self.config.inner_size
        self.base_mid_size = self.config.mid_size
        self.base_outer_size = self.config.outer_size
        self.base_ring_width = self.config.ring_width
        self.base_font_size = self.config.font_size
        self.base_metatron_glow_widths = tuple(self.metatron_config.seg_glow_widths)
        self.current_scale_index = self.default_scale_index
        self.current_scale = self.scale_presets[self.current_scale_index]
        if seed is not None:
            random.seed(seed)
        pygame.init()
        pygame.display.set_caption("Metatron Neuro Wheel — FLUID Lines & Rays")
        self.clock = pygame.time.Clock()
        self.allow_scaled_flag = True
        self.screen = self.apply_scale(self.current_scale)

    def create_state(self) -> WheelState:
        return WheelState(
            center_pulse_hz=self.config.center_pulse_hz,
            speed_trim=self.config.speed_trim,
            show_ch_10=self.config.show_ch_10,
            show_ch_25=self.config.show_ch_25,
            show_ch_50=self.config.show_ch_50,
            scale_index=self.current_scale_index,
        )

    def clamp_scale_index(self, index: int) -> int:
        return max(0, min(index, len(self.scale_presets) - 1))

    def configure_display(self, width: int, height: int) -> pygame.Surface:
        flags = pygame.RESIZABLE
        if self.allow_scaled_flag:
            try:
                return pygame.display.set_mode((width, height), pygame.SCALED | flags)
            except pygame.error:
                self.allow_scaled_flag = False
        return pygame.display.set_mode((width, height), flags)

    def apply_scale(self, scale: float) -> pygame.Surface:
        scale = max(0.25, scale)
        width = max(self.config.min_width, int(self.base_width * scale))
        height = max(self.config.min_height, int(self.base_height * scale))
        base_radius = max(120, int(self.base_radius * scale))
        self.screen = self.configure_display(width, height)
        self.config.width = width
        self.config.height = height
        self.config.base_radius = base_radius
        self.config.inner_size = max(6, int(self.base_inner_size * scale))
        self.config.mid_size = max(6, int(self.base_mid_size * scale))
        self.config.outer_size = max(6, int(self.base_outer_size * scale))
        self.config.ring_width = max(1, int(self.base_ring_width * scale))
        scaled_glow = tuple(max(1, int(round(glow_width * scale))) for glow_width in self.base_metatron_glow_widths)
        self.metatron_config.seg_glow_widths = scaled_glow
        font_size = max(14, int(self.base_font_size * scale))
        self.font_small = pygame.font.SysFont(self.config.font_family, font_size)
        self.current_scale = scale
        return self.screen

    def build_hud(self, state: WheelState) -> pygame.Surface:
        index = self.clamp_scale_index(state.scale_index)
        scale_percent = int(round(self.scale_presets[index] * 100))
        hud_text = (
            f"ESC quit  R restart  SPACE emergency   +/- pulse {state.center_pulse_hz:.1f}Hz   "
            f"[ / ] speed {state.speed_trim:.2f}   1/2/3 overlays   L rays   M scale {scale_percent}%"
        )
        return self.font_small.render(hud_text, True, (120, 120, 135))

    def build_scale_menu(self, state: WheelState) -> pygame.Surface:
        index = self.clamp_scale_index(state.scale_index)
        padding = 14
        spacing = 6
        header = self.font_small.render("Scale presets", True, (215, 215, 225))
        option_surfaces: List[pygame.Surface] = []
        max_width = header.get_width()
        for idx, scale in enumerate(self.scale_presets):
            percent = int(round(scale * 100))
            width = int(self.base_width * scale)
            height = int(self.base_height * scale)
            prefix = "➤" if idx == index else "  "
            label = f"{prefix} {percent}%  {width}x{height}"
            color = (235, 235, 245) if idx == index else (170, 170, 185)
            surf = self.font_small.render(label, True, color)
            option_surfaces.append(surf)
            max_width = max(max_width, surf.get_width())
        instruction = self.font_small.render("↑/↓ choose  Enter apply  M close", True, (150, 150, 165))
        total_height = (
            header.get_height()
            + len(option_surfaces) * (self.font_small.get_linesize() + spacing)
            + instruction.get_height()
            + padding * 3
        )
        menu_surface = pygame.Surface((max_width + padding * 2, total_height), pygame.SRCALPHA)
        menu_surface.fill((12, 14, 22, 215))
        y = padding
        menu_surface.blit(header, (padding, y))
        y += header.get_height() + spacing
        line_height = self.font_small.get_linesize()
        for idx, surf in enumerate(option_surfaces):
            if idx == index:
                highlight_rect = pygame.Rect(6, y - 2, menu_surface.get_width() - 12, line_height + 4)
                pygame.draw.rect(menu_surface, (60, 70, 95, 160), highlight_rect, border_radius=6)
            menu_surface.blit(surf, (padding, y))
            y += line_height + spacing
        y += spacing
        menu_surface.blit(instruction, (padding, y))
        return menu_surface

    def pause_until_restart(self) -> None:
        self.screen.fill((0, 0, 0))
        pygame.display.flip()
        while True:
            event = pygame.event.wait()
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                if event.key == pygame.K_r:
                    return

    def handle_events(self, state: WheelState) -> bool:
        restart = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if state.scale_menu_open:
                    if event.key in (pygame.K_ESCAPE, pygame.K_m):
                        state.scale_menu_open = False
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        state.scale_index = self.clamp_scale_index(state.scale_index - 1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        state.scale_index = self.clamp_scale_index(state.scale_index + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        state.scale_menu_open = False
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        choice = event.key - pygame.K_1
                        state.scale_index = self.clamp_scale_index(choice)
                    continue
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit(0)
                elif event.key == pygame.K_m:
                    state.scale_menu_open = not state.scale_menu_open
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    state.center_pulse_hz = min(24.0, state.center_pulse_hz + 0.5)
                elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                    state.center_pulse_hz = max(1.0, state.center_pulse_hz - 0.5)
                elif event.key == pygame.K_LEFTBRACKET:
                    state.speed_trim = max(0.6, state.speed_trim - 0.05)
                elif event.key == pygame.K_RIGHTBRACKET:
                    state.speed_trim = min(1.6, state.speed_trim + 0.05)
                elif event.key == pygame.K_1:
                    state.show_ch_10 = not state.show_ch_10
                elif event.key == pygame.K_2:
                    state.show_ch_25 = not state.show_ch_25
                elif event.key == pygame.K_3:
                    state.show_ch_50 = not state.show_ch_50
                elif event.key == pygame.K_l:
                    state.rays_on = not state.rays_on
                elif event.key == pygame.K_SPACE:
                    self.pause_until_restart()
                    restart = True
                elif event.key == pygame.K_r:
                    restart = True
        return restart

    def run_scene(self) -> None:
        state = self.create_state()
        state.scale_index = self.clamp_scale_index(state.scale_index)
        self.apply_scale(self.scale_presets[state.scale_index])
        self.current_scale_index = state.scale_index
        start_time = time.time()
        inner_count = self.config.inner_nodes
        mid_count = self.config.mid_nodes
        outer_count = self.config.outer_nodes
        glyph_kinds = self.config.glyph_kinds
        inner_kinds, inner_rotations, inner_flips = build_glyph_ring(inner_count, glyph_kinds)
        mid_kinds, mid_rotations, mid_flips = build_glyph_ring(mid_count, glyph_kinds)
        outer_kinds, outer_rotations, outer_flips = build_glyph_ring(outer_count, glyph_kinds)
        inner_last = [0.0] * inner_count
        mid_last = [0.0] * mid_count
        outer_last = [0.0] * outer_count
        links: List[dict] = []

        fm = FluidMetatron(lambda: cxcy(self.screen), self.config.base_radius, self.config.foreground, self.metatron_config)

        schedule_index = 0
        sub_phase: str | None = None
        sub_index = 0
        band_start = time.time()
        sub_start = band_start
        burst_until = band_start + self.config.burst_length

        while True:
            dt = self.clock.tick(self.config.fps_cap) / 1000.0
            now = time.time()
            elapsed = now - start_time
            prev_scale_index = state.scale_index
            if self.handle_events(state):
                self.current_scale_index = self.clamp_scale_index(state.scale_index)
                return
            state.scale_index = self.clamp_scale_index(state.scale_index)
            if state.scale_index != prev_scale_index:
                self.apply_scale(self.scale_presets[state.scale_index])
                self.current_scale_index = state.scale_index
                fm = FluidMetatron(
                    lambda: cxcy(self.screen), self.config.base_radius, self.config.foreground, self.metatron_config
                )
                links.clear()
                inner_kinds, inner_rotations, inner_flips = build_glyph_ring(inner_count, glyph_kinds)
                mid_kinds, mid_rotations, mid_flips = build_glyph_ring(mid_count, glyph_kinds)
                outer_kinds, outer_rotations, outer_flips = build_glyph_ring(outer_count, glyph_kinds)
                inner_last = [0.0] * inner_count
                mid_last = [0.0] * mid_count
                outer_last = [0.0] * outer_count

            band_stage = self.band_schedule[schedule_index]
            state.center_pulse_hz = band_stage.frequency
            time_in_band = now - band_start
            burst_boost = max(0.0, min(1.0, (burst_until - now) / self.config.burst_length)) if now < burst_until else 0.0

            if band_stage.name == "theta":
                if sub_phase is None:
                    sub_phase = "outer"
                    sub_index = 0
                    sub_start = now
                sub_list = self.subcycle_outer if sub_phase == "outer" else self.subcycle_mid
                sub_stage = sub_list[sub_index]
                if now - sub_start >= sub_stage.duration:
                    sub_index += 1
                    if sub_index >= len(sub_list):
                        if sub_phase == "outer":
                            sub_phase = "mid"
                            sub_index = 0
                        else:
                            sub_phase = "done"
                    sub_start = now
                base_inner, base_mid, base_outer, channel_mask = band_params("theta")
                if sub_phase == "outer":
                    _, _, base_outer, _ = band_params(sub_stage.name)
                elif sub_phase == "mid":
                    _, base_mid, _, _ = band_params(sub_stage.name)
                inner_hz = base_inner * state.speed_trim
                mid_hz = base_mid * state.speed_trim
                outer_hz = base_outer * state.speed_trim
                ch10, ch25, ch50 = channel_mask
            else:
                base_inner, base_mid, base_outer, channel_mask = band_params(band_stage.name)
                inner_hz = base_inner * state.speed_trim
                mid_hz = base_mid * state.speed_trim
                outer_hz = base_outer * state.speed_trim
                ch10, ch25, ch50 = channel_mask

            if time_in_band >= band_stage.duration and band_stage.name != "theta":
                schedule_index = min(len(self.band_schedule) - 1, schedule_index + 1)
                band_start = now
                burst_until = now + self.config.burst_length
            if band_stage.name == "theta" and sub_phase == "done" and time_in_band >= band_stage.duration:
                schedule_index = 0
                band_start = now
                sub_phase = None
                burst_until = now + self.config.burst_length

            phi_inner = -2 * math.pi * inner_hz * (now - start_time)
            phi_mid = 2 * math.pi * mid_hz * (now - start_time)
            phi_outer = 2 * math.pi * outer_hz * (now - start_time)

            self.screen.fill(self.config.background)
            draw_tundra(self.screen, elapsed)
            draw_g_wheel(self.screen, elapsed, self.config.foreground, self.config.g_visual)
            if state.show_ch_10 and ch10:
                draw_channel_overlay(self.screen, elapsed, 1.0, (200, 200, 200), 100, 24, burst_boost)
            if state.show_ch_25 and ch25:
                draw_channel_overlay(self.screen, elapsed, 10.0, (0, 200, 200), 180, 30, burst_boost)
            if state.show_ch_50 and ch50:
                draw_channel_overlay(self.screen, elapsed, 8.0, (200, 0, 200), 260, 36, burst_boost)

            draw_base_rings(self.screen, self.config)

            if state.rays_on:
                fm.update_rays(elapsed)
            fm.step_targets()
            fm.update_progress(dt)
            fm.draw(self.screen)
            lit_ray_angles = fm.smooth_angles if state.rays_on else []

            cx, cy = cxcy(self.screen)
            inner_radius = int(self.config.base_radius * self.config.inner_radius_ratio)
            mid_radius = int(self.config.base_radius * self.config.mid_radius_ratio)
            outer_radius = int(self.config.base_radius * self.config.outer_radius_ratio)
            inner_pts = ring_points(cx, cy, inner_radius, inner_count, phi_inner)
            mid_pts = ring_points(cx, cy, mid_radius, mid_count, phi_mid)
            outer_pts = ring_points(cx, cy, outer_radius, outer_count, phi_outer)

            draw_ring_icons(
                self.screen,
                inner_pts,
                self.config.inner_size,
                inner_kinds,
                glyph_kinds,
                self.config.foreground,
                alpha=104,
                rotations=inner_rotations,
                flips=inner_flips,
            )
            draw_ring_icons(
                self.screen,
                mid_pts,
                self.config.mid_size,
                mid_kinds,
                glyph_kinds,
                self.config.foreground,
                alpha=98,
                rotations=mid_rotations,
                flips=mid_flips,
            )
            draw_ring_icons(
                self.screen,
                outer_pts,
                self.config.outer_size,
                outer_kinds,
                glyph_kinds,
                self.config.foreground,
                alpha=132,
                rotations=outer_rotations,
                flips=outer_flips,
            )

            def gate_by_rays(point: Vec2) -> bool:
                if not state.rays_on:
                    return True
                if not lit_ray_angles:
                    return True
                ang = angle_of_point(cx, cy, point)
                dist = min(abs(math.atan2(math.sin(ang - ray), math.cos(ang - ray))) for ray in lit_ray_angles)
                return dist < math.radians(self.metatron_config.ray_spread_deg)

            now_time = time.time()
            for oi, (ox, oy) in enumerate(outer_pts):
                outer_angle = math.atan2(oy - cy, ox - cx)
                inner_index = round(((outer_angle - phi_inner) % (2 * math.pi)) / (2 * math.pi / inner_count)) % inner_count
                ix, iy = inner_pts[inner_index]
                inner_angle = math.atan2(iy - cy, ix - cx)
                delta = math.atan2(math.sin(outer_angle - inner_angle), math.cos(outer_angle - inner_angle))
                midpoint = ((ix + ox) / 2, (iy + oy) / 2)
                if (
                    abs(delta) < self.config.handoff_angle_threshold
                    and (now_time - inner_last[inner_index]) > self.config.handoff_cooldown
                    and gate_by_rays(midpoint)
                ):
                    outer_kinds[oi] = inner_kinds[inner_index]
                    outer_rotations[oi] = inner_rotations[inner_index]
                    outer_flips[oi] = -inner_flips[inner_index] if outer_flips else -1
                    advance_glyph_ring_slot(inner_kinds, inner_rotations, inner_flips, inner_index, glyph_kinds)
                    inner_last[inner_index] = now_time
                    links.append({"t0": now_time, "p_in": (ix, iy), "p_out": (ox, oy)})

            for mi, (mx, my) in enumerate(mid_pts):
                mid_angle = math.atan2(my - cy, mx - cx)
                inner_index = round(((mid_angle - phi_inner) % (2 * math.pi)) / (2 * math.pi / inner_count)) % inner_count
                ix, iy = inner_pts[inner_index]
                inner_angle = math.atan2(iy - cy, ix - cx)
                delta = math.atan2(math.sin(mid_angle - inner_angle), math.cos(mid_angle - inner_angle))
                midpoint = ((ix + mx) / 2, (iy + my) / 2)
                if (
                    abs(delta) < self.config.handoff_angle_threshold
                    and (now_time - inner_last[inner_index]) > self.config.handoff_cooldown
                    and gate_by_rays(midpoint)
                ):
                    mid_kinds[mi] = inner_kinds[inner_index]
                    mid_rotations[mi] = inner_rotations[inner_index]
                    mid_flips[mi] = -inner_flips[inner_index] if mid_flips else -1
                    advance_glyph_ring_slot(inner_kinds, inner_rotations, inner_flips, inner_index, glyph_kinds)
                    inner_last[inner_index] = now_time
                    links.append({"t0": now_time, "p_in": (ix, iy), "p_out": (mx, my)})

            draw_links(self.screen, links, self.config, self.config.foreground)
            draw_center_pulse(self.screen, elapsed, state.center_pulse_hz, self.config)
            draw_reticle(self.screen, elapsed, self.config.foreground)

            hud_surface = self.build_hud(state)
            band_surface = self.font_small.render(
                f"{self.band_schedule[schedule_index].name.upper()}   speed x{state.speed_trim:.2f}",
                True,
                (120, 120, 135),
            )
            self.screen.blit(hud_surface, (16, 16))
            self.screen.blit(band_surface, (16, self.screen.get_height() - 36))
            if state.scale_menu_open:
                menu_surface = self.build_scale_menu(state)
                margin = 16
                self.screen.blit(
                    menu_surface,
                    (self.screen.get_width() - menu_surface.get_width() - margin, margin),
                )
            pygame.display.flip()

            if elapsed >= self.config.scene_seconds:
                break

        self.current_scale_index = self.clamp_scale_index(state.scale_index)

    def run_forever(self) -> None:
        while True:
            self.run_scene()


def main() -> None:
    app = NeuroWheelApp()
    app.run_forever()


if __name__ == "__main__":
    main()
