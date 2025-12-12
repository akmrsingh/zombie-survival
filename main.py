#!/usr/bin/env python3
"""
Zombie Survival: Class-Based Defense Game
Features: 4 classes, realistic weapons, waves, bunker, local & online multiplayer
"""

import pygame
import math
import random
import asyncio
import sys

# Conditional imports for desktop vs web
try:
    import socket
    import threading
    import pickle
    NETWORK_AVAILABLE = True
except ImportError:
    NETWORK_AVAILABLE = False

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 100, 255)
YELLOW = (255, 255, 0)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
BROWN = (139, 69, 19)
DARK_GREEN = (0, 100, 0)
LIGHT_BLUE = (135, 206, 235)
DARK_RED = (139, 0, 0)
ZOMBIE_GREEN = (50, 120, 50)

# Detect touch/mobile
IS_MOBILE = False
try:
    # Check if running in browser (Pygbag)
    import platform
    if platform.system() == 'Emscripten':
        IS_MOBILE = True
except:
    pass

# Game States
class GameState(Enum):
    MENU = 1
    CLASS_SELECT = 2
    PLAYING = 3
    PAUSED = 4
    GAME_OVER = 5
    WAVE_COMPLETE = 6
    MULTIPLAYER_LOBBY = 7
    HOST_GAME = 8
    JOIN_GAME = 9

# Player Classes
class PlayerClass(Enum):
    BUILDER = 1
    RANGER = 2
    HEALER = 3
    TANK = 4
    TRAITOR = 5  # Betrays team, allied with zombies

# Desert colors
SAND = (210, 180, 140)
DARK_SAND = (180, 150, 110)
LIGHT_SAND = (230, 210, 170)

# Weapon Types - Realistic Stats
@dataclass
class WeaponStats:
    name: str
    damage: int
    fire_rate: float  # rounds per minute converted to shots/sec
    reload_time: float  # seconds (realistic reload times)
    mag_size: int
    max_ammo: int
    bullet_speed: float  # meters/sec scaled for game
    spread: float  # MOA (minutes of angle) accuracy
    bullet_count: int = 1
    explosive: bool = False
    explosion_radius: float = 0
    range: float = 800  # effective range in game units
    recoil: float = 1.0  # recoil intensity (affects accuracy after shots)
    penetration: int = 1  # how many enemies bullet can hit
    caliber: str = "9mm"  # bullet type for display

# Realistic weapon definitions based on real firearms
WEAPONS = {
    # === PISTOLS ===
    # Heavy pistol - large caliber, 7+1 rounds
    "pistol": WeaponStats(
        name="Heavy Pistol",
        damage=35,  # Large caliber hits hard
        fire_rate=2.5,  # semi-auto
        reload_time=2.1,  # mag change + chamber
        mag_size=7,
        max_ammo=49,  # 7 mags
        bullet_speed=25,
        spread=2.5,
        recoil=2.5,  # heavy recoil
        caliber="Large",
        range=500
    ),

    # Standard pistol - 17+1 rounds
    "glock": WeaponStats(
        name="Pistol",
        damage=25,
        fire_rate=3.5,  # faster follow-up shots
        reload_time=1.8,
        mag_size=17,
        max_ammo=85,
        bullet_speed=28,
        spread=2.0,
        recoil=1.5,  # lighter recoil
        caliber="Standard",
        range=500
    ),

    # === RIFLES ===
    # Assault rifle - 30 rounds, full auto
    "rifle": WeaponStats(
        name="Assault Rifle",
        damage=40,
        fire_rate=12.5,  # 750 RPM full auto
        reload_time=2.5,  # tactical reload
        mag_size=30,
        max_ammo=150,
        bullet_speed=45,
        spread=1.5,
        recoil=2.0,
        penetration=2,  # can hit 2 enemies
        caliber="Rifle",
        range=800
    ),

    # Heavy assault rifle - harder hitting but less accurate
    "ak47": WeaponStats(
        name="Heavy Rifle",
        damage=48,  # hits harder
        fire_rate=10.0,  # 600 RPM
        reload_time=2.8,
        mag_size=30,
        max_ammo=120,
        bullet_speed=40,
        spread=3.5,  # less accurate
        recoil=3.5,  # heavy recoil
        penetration=2,
        caliber="Heavy Rifle",
        range=700
    ),

    # === SNIPER RIFLES ===
    # Anti-material rifle - devastating power
    "sniper": WeaponStats(
        name="Sniper Rifle",
        damage=200,  # Devastating power
        fire_rate=0.5,  # semi-auto, slow
        reload_time=4.0,  # heavy mag
        mag_size=10,
        max_ammo=30,
        bullet_speed=60,
        spread=0.3,  # very accurate
        recoil=5.0,  # massive recoil
        penetration=3,  # can hit 3 enemies
        caliber="Anti-Material",
        range=1500
    ),

    # Marksman rifle
    "svd": WeaponStats(
        name="Marksman Rifle",
        damage=90,
        fire_rate=1.0,
        reload_time=3.0,
        mag_size=10,
        max_ammo=50,
        bullet_speed=50,
        spread=0.8,
        recoil=3.0,
        penetration=2,
        caliber="Marksman",
        range=1200
    ),

    # === SHOTGUNS ===
    # Pump shotgun - 12 gauge
    "shotgun": WeaponStats(
        name="Pump Shotgun",
        damage=18,  # per pellet, 8 pellets = 144 max
        fire_rate=1.0,  # pump action
        reload_time=0.5,  # per shell
        mag_size=8,
        max_ammo=32,
        bullet_speed=20,
        spread=12,  # wide spread
        bullet_count=8,  # 8 pellets
        recoil=4.0,
        caliber="Buckshot",
        range=300
    ),

    # Auto shotgun
    "spas12": WeaponStats(
        name="Auto Shotgun",
        damage=15,
        fire_rate=2.5,  # semi-auto faster
        reload_time=3.5,
        mag_size=8,
        max_ammo=40,
        bullet_speed=18,
        spread=14,
        bullet_count=9,
        recoil=3.5,
        caliber="Buckshot",
        range=250
    ),

    # === SMGs ===
    # Tactical SMG - accurate
    "smg": WeaponStats(
        name="SMG",
        damage=22,
        fire_rate=13.3,  # 800 RPM
        reload_time=2.0,
        mag_size=30,
        max_ammo=180,
        bullet_speed=30,
        spread=3.0,
        recoil=1.2,  # low recoil
        caliber="Compact",
        range=400
    ),

    # PDW - high capacity
    "p90": WeaponStats(
        name="PDW",
        damage=20,
        fire_rate=15.0,  # 900 RPM
        reload_time=2.3,
        mag_size=50,
        max_ammo=200,
        bullet_speed=35,
        spread=2.5,
        recoil=1.0,  # very low recoil
        penetration=2,  # armor piercing
        caliber="AP Compact",
        range=450
    ),

    # === HEAVY WEAPONS ===
    # Rocket launcher
    "rpg": WeaponStats(
        name="Rocket Launcher",
        damage=150,
        fire_rate=0.3,  # slow reload
        reload_time=5.0,
        mag_size=1,
        max_ammo=8,
        bullet_speed=15,  # rockets are slower
        spread=2.0,
        explosive=True,
        explosion_radius=120,
        recoil=6.0,
        caliber="Rocket",
        range=600
    ),

    # Grenade launcher
    "grenade_launcher": WeaponStats(
        name="Grenade Launcher",
        damage=100,
        fire_rate=1.5,
        reload_time=4.5,
        mag_size=6,
        max_ammo=24,
        bullet_speed=12,
        spread=3.0,
        explosive=True,
        explosion_radius=90,
        recoil=4.0,
        caliber="Grenade",
        range=500
    ),

    # Rotary cannon
    "minigun": WeaponStats(
        name="Minigun",
        damage=30,
        fire_rate=50.0,  # 3000 RPM
        reload_time=6.0,  # belt fed, long reload
        mag_size=200,
        max_ammo=600,
        bullet_speed=42,
        spread=6.0,  # less accurate due to spin-up
        recoil=0.5,  # mounted, low felt recoil
        penetration=2,
        caliber="Heavy",
        range=700
    ),

    # === SPECIAL WEAPONS ===
    # Nail Gun - Builder tool
    "nail_gun": WeaponStats(
        name="Pneumatic Nail Gun",
        damage=12,
        fire_rate=6.0,
        reload_time=1.5,
        mag_size=50,
        max_ammo=250,
        bullet_speed=18,
        spread=6.0,
        recoil=0.5,
        caliber="3.5in Nail",
        range=200
    ),

    # Tranquilizer Pistol
    "tranq_pistol": WeaponStats(
        name="Tranq Pistol",
        damage=18,
        fire_rate=1.5,
        reload_time=2.0,
        mag_size=8,
        max_ammo=40,
        bullet_speed=15,
        spread=3.0,
        recoil=1.0,
        caliber="Tranq Dart",
        range=350
    ),

    # Desert Eagle - .50 AE, hand cannon
    "deagle": WeaponStats(
        name="Desert Eagle .50",
        damage=55,
        fire_rate=1.8,
        reload_time=2.3,
        mag_size=7,
        max_ammo=35,
        bullet_speed=30,
        spread=2.0,
        recoil=5.0,  # massive recoil
        penetration=2,
        caliber=".50 AE",
        range=400
    ),

    # Combat Knife - melee, instant kill on regular zombies
    "knife": WeaponStats(
        name="Combat Knife",
        damage=9999,  # Instant kill (except bosses)
        fire_rate=2.0,  # Slash rate
        reload_time=0,  # No reload
        mag_size=999,  # Unlimited
        max_ammo=999,
        bullet_speed=0,  # Melee - no bullet
        spread=0,
        recoil=0,
        caliber="Melee",
        range=50  # Very short range
    ),
}


class VirtualJoystick:
    """Virtual joystick for touch controls."""
    def __init__(self, x, y, radius=80):
        self.base_x = x
        self.base_y = y
        self.radius = radius
        self.knob_radius = radius // 2
        self.knob_x = x
        self.knob_y = y
        self.active = False
        self.touch_id = None

    def handle_touch_down(self, touch_id, x, y):
        dist = math.sqrt((x - self.base_x)**2 + (y - self.base_y)**2)
        if dist < self.radius * 1.5:
            self.active = True
            self.touch_id = touch_id
            self.update_knob(x, y)
            return True
        return False

    def handle_touch_move(self, touch_id, x, y):
        if self.active and self.touch_id == touch_id:
            self.update_knob(x, y)
            return True
        return False

    def handle_touch_up(self, touch_id):
        if self.touch_id == touch_id:
            self.active = False
            self.touch_id = None
            self.knob_x = self.base_x
            self.knob_y = self.base_y
            return True
        return False

    def update_knob(self, x, y):
        dx = x - self.base_x
        dy = y - self.base_y
        dist = math.sqrt(dx**2 + dy**2)
        if dist > self.radius:
            dx = dx / dist * self.radius
            dy = dy / dist * self.radius
        self.knob_x = self.base_x + dx
        self.knob_y = self.base_y + dy

    def get_direction(self):
        dx = (self.knob_x - self.base_x) / self.radius
        dy = (self.knob_y - self.base_y) / self.radius
        return dx, dy

    def draw(self, screen):
        # Draw base circle
        pygame.draw.circle(screen, (100, 100, 100, 128), (int(self.base_x), int(self.base_y)), self.radius, 3)
        # Draw knob
        pygame.draw.circle(screen, (200, 200, 200), (int(self.knob_x), int(self.knob_y)), self.knob_radius)
        pygame.draw.circle(screen, WHITE, (int(self.knob_x), int(self.knob_y)), self.knob_radius, 2)


class TouchButton:
    """Touch button for mobile controls."""
    def __init__(self, x, y, radius, label, color=GRAY):
        self.x = x
        self.y = y
        self.radius = radius
        self.label = label
        self.color = color
        self.pressed = False
        self.touch_id = None

    def handle_touch_down(self, touch_id, x, y):
        dist = math.sqrt((x - self.x)**2 + (y - self.y)**2)
        if dist < self.radius:
            self.pressed = True
            self.touch_id = touch_id
            return True
        return False

    def handle_touch_up(self, touch_id):
        if self.touch_id == touch_id:
            self.pressed = False
            self.touch_id = None
            return True
        return False

    def draw(self, screen, font):
        color = WHITE if self.pressed else self.color
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 3)
        text = font.render(self.label, True, BLACK if self.pressed else WHITE)
        screen.blit(text, (self.x - text.get_width()//2, self.y - text.get_height()//2))


class Particle:
    """Particle effect for explosions, blood, etc."""
    def __init__(self, x, y, color, velocity, lifetime, size=3):
        self.x = x
        self.y = y
        self.color = color
        self.vx, self.vy = velocity
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.size = size

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 200 * dt  # gravity
        self.lifetime -= dt
        return self.lifetime > 0

    def draw(self, screen, camera_offset):
        alpha = self.lifetime / self.max_lifetime
        size = int(self.size * alpha)
        if size > 0:
            pygame.draw.circle(screen, self.color,
                             (int(self.x - camera_offset[0]), int(self.y - camera_offset[1])), size)


class Bullet:
    """Projectile class for all weapons with realistic ballistics."""
    def __init__(self, x, y, angle, stats: WeaponStats, owner_id):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = stats.bullet_speed * 60
        self.damage = stats.damage
        self.explosive = stats.explosive
        self.explosion_radius = stats.explosion_radius
        self.range = stats.range
        self.distance_traveled = 0
        self.owner_id = owner_id
        self.vx = math.cos(angle) * self.speed
        self.vy = math.sin(angle) * self.speed
        self.active = True
        self.penetration = stats.penetration  # How many enemies can hit
        self.hits = 0  # Track hits for penetration
        self.caliber = stats.caliber
        # Bullet drop for realism (gravity effect)
        self.gravity = 50 if not stats.explosive else 80  # Rockets drop more

    def update(self, dt):
        move_dist = self.speed * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        # Apply bullet drop (gravity)
        self.vy += self.gravity * dt
        self.distance_traveled += move_dist
        # Damage falloff at range
        if self.distance_traveled > self.range:
            self.active = False
        return self.active

    def hit_target(self):
        """Called when bullet hits an enemy. Returns True if bullet should continue."""
        self.hits += 1
        self.damage *= 0.7  # Damage reduction per penetration
        return self.hits < self.penetration

    def draw(self, screen, camera_offset):
        draw_x = int(self.x - camera_offset[0])
        draw_y = int(self.y - camera_offset[1])

        # Different bullet visuals based on caliber
        if self.explosive:
            # Rocket/grenade - larger, red-orange
            pygame.draw.circle(screen, RED, (draw_x, draw_y), 6)
            pygame.draw.circle(screen, ORANGE, (draw_x, draw_y), 4)
        elif ".50" in self.caliber or "7.62" in self.caliber:
            # Large caliber - bigger bullet
            pygame.draw.circle(screen, YELLOW, (draw_x, draw_y), 5)
        else:
            # Standard bullet
            pygame.draw.circle(screen, YELLOW, (draw_x, draw_y), 3)

        # Trail effect - longer for faster bullets
        trail_length = 0.03 if self.speed > 2000 else 0.02
        trail_x = self.x - self.vx * trail_length
        trail_y = self.y - self.vy * trail_length
        trail_color = RED if self.explosive else ORANGE
        pygame.draw.line(screen, trail_color,
                        (int(trail_x - camera_offset[0]), int(trail_y - camera_offset[1])),
                        (draw_x, draw_y), 2)


class Wall:
    """Buildable wall for Builder class."""
    def __init__(self, x, y, width=320, height=80, health=400):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.health = health
        self.max_health = health
        self.active = True

    def take_damage(self, damage):
        self.health -= damage
        if self.health <= 0:
            self.active = False

    def get_rect(self):
        return pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)

    def draw(self, screen, camera_offset):
        rect = self.get_rect()
        draw_rect = rect.move(-camera_offset[0], -camera_offset[1])

        # Health-based color
        health_ratio = self.health / self.max_health
        color = (int(139 * health_ratio), int(69 * health_ratio), int(19 * health_ratio))
        pygame.draw.rect(screen, color, draw_rect)
        pygame.draw.rect(screen, DARK_GRAY, draw_rect, 2)

        # Health bar
        if self.health < self.max_health:
            bar_width = self.width * health_ratio
            pygame.draw.rect(screen, RED, (draw_rect.x, draw_rect.y - 8, self.width, 5))
            pygame.draw.rect(screen, GREEN, (draw_rect.x, draw_rect.y - 8, bar_width, 5))


class HealZone:
    """Healing area created by Healer class."""
    def __init__(self, x, y, radius=100, duration=10, heal_rate=20):
        self.x = x
        self.y = y
        self.radius = radius
        self.duration = duration
        self.heal_rate = heal_rate  # HP per second
        self.active = True

    def update(self, dt):
        self.duration -= dt
        if self.duration <= 0:
            self.active = False
        return self.active

    def draw(self, screen, camera_offset):
        alpha = min(1.0, self.duration / 3)
        # Draw healing zone
        surface = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surface, (0, 255, 0, int(50 * alpha)), (self.radius, self.radius), self.radius)
        pygame.draw.circle(surface, (0, 255, 0, int(100 * alpha)), (self.radius, self.radius), self.radius, 3)
        screen.blit(surface, (self.x - self.radius - camera_offset[0], self.y - self.radius - camera_offset[1]))


class Zombie:
    """Enemy zombie with different types."""
    def __init__(self, x, y, zombie_type="normal", wave=1, king_stage=1):
        self.x = x
        self.y = y
        self.zombie_type = zombie_type
        self.wave = wave
        self.king_stage = king_stage  # For Zombie King boss

        # Random color variation for realism
        def vary_color(base_color, variance=20):
            return tuple(max(0, min(255, c + random.randint(-variance, variance))) for c in base_color)

        # Type-specific stats with realistic zombie colors
        if zombie_type == "normal":
            self.health = 50 + wave * 10
            self.speed = 80 + wave * 2
            self.damage = 10 + wave
            self.size = 20
            # Grayish-green rotting flesh tones
            base_colors = [(85, 107, 85), (70, 90, 70), (95, 115, 80), (80, 100, 75)]
            self.skin_color = vary_color(random.choice(base_colors), 15)
            self.detail_color = vary_color((60, 75, 55), 10)
            self.wound_color = (120, 50, 50)  # Dark red wounds
        elif zombie_type == "runner":
            self.health = 30 + wave * 5
            self.speed = 150 + wave * 5
            self.damage = 8 + wave
            self.size = 16
            # Pale, freshly turned - more skin-like
            base_colors = [(160, 140, 130), (145, 130, 120), (155, 145, 135), (140, 125, 115)]
            self.skin_color = vary_color(random.choice(base_colors), 15)
            self.detail_color = vary_color((100, 85, 80), 10)
            self.wound_color = (180, 70, 70)  # Fresher blood
        elif zombie_type == "tank":
            self.health = 200 + wave * 30
            self.speed = 40 + wave
            self.damage = 25 + wave * 2
            self.size = 35
            # Dark, bloated, heavily decayed
            base_colors = [(50, 65, 50), (45, 55, 45), (55, 70, 55), (40, 50, 40)]
            self.skin_color = vary_color(random.choice(base_colors), 10)
            self.detail_color = vary_color((30, 40, 30), 8)
            self.wound_color = (90, 40, 40)  # Old dried blood
        elif zombie_type == "spitter":
            self.health = 40 + wave * 8
            self.speed = 60 + wave * 2
            self.damage = 15 + wave
            self.size = 22
            # Toxic green/yellow - infected with acid
            base_colors = [(100, 130, 50), (90, 140, 45), (110, 135, 55), (95, 125, 40)]
            self.skin_color = vary_color(random.choice(base_colors), 15)
            self.detail_color = vary_color((70, 100, 30), 10)
            self.wound_color = (150, 180, 50)  # Toxic ooze
            self.spit_cooldown = 0
            self.spit_range = 300
        elif zombie_type == "crawler":
            # New type: crawling zombie, low and fast
            self.health = 25 + wave * 5
            self.speed = 100 + wave * 3
            self.damage = 12 + wave
            self.size = 14
            base_colors = [(75, 85, 75), (65, 80, 70), (80, 90, 75)]
            self.skin_color = vary_color(random.choice(base_colors), 12)
            self.detail_color = vary_color((50, 60, 45), 8)
            self.wound_color = (100, 45, 45)
        elif zombie_type == "bloater":
            # New type: explodes on death
            self.health = 80 + wave * 15
            self.speed = 35 + wave
            self.damage = 20 + wave
            self.size = 30
            # Swollen, purple-ish diseased look
            base_colors = [(90, 70, 100), (85, 65, 95), (95, 75, 105)]
            self.skin_color = vary_color(random.choice(base_colors), 12)
            self.detail_color = vary_color((60, 45, 70), 10)
            self.wound_color = (130, 90, 140)  # Purple ooze
        elif zombie_type == "radioactive":
            # Radioactive zombie - glows green, damages nearby players
            self.health = 60 + wave * 12
            self.speed = 70 + wave * 2
            self.damage = 18 + wave
            self.size = 24
            self.radiation_radius = 80  # Damages players in this radius
            self.radiation_damage = 5  # Damage per second to nearby players
            # Glowing green radioactive look
            base_colors = [(50, 255, 50), (40, 230, 40), (60, 240, 60)]
            self.skin_color = vary_color(random.choice(base_colors), 20)
            self.detail_color = vary_color((30, 180, 30), 15)
            self.wound_color = (100, 255, 100)  # Glowing green wounds
            self.glow_pulse = 0  # For pulsing glow effect
        elif zombie_type == "cage_walker":
            # Cage Walker - boss zombie, very powerful, commands other zombies
            self.health = 500 + wave * 50
            self.speed = 50 + wave
            self.damage = 50 + wave * 3  # Massive damage
            self.size = 45
            self.is_boss = True
            self.command_radius = 300  # Radius to command other zombies
            self.roar_cooldown = 0  # Cooldown for commanding zombies
            # Dark armored look with cage-like patterns
            base_colors = [(40, 40, 50), (35, 35, 45), (45, 45, 55)]
            self.skin_color = vary_color(random.choice(base_colors), 10)
            self.detail_color = vary_color((60, 60, 80), 10)
            self.wound_color = (80, 20, 20)  # Dark blood
            self.cage_color = (100, 100, 120)  # Metal cage color
        elif zombie_type == "speed":
            # Speed zombie - very fast, medium sized
            self.health = 35 + wave * 6
            self.speed = 200 + wave * 5  # Very fast!
            self.damage = 10 + wave
            self.size = 18
            # Lean, athletic zombie
            base_colors = [(130, 115, 100), (120, 105, 95), (140, 125, 110)]
            self.skin_color = vary_color(random.choice(base_colors), 15)
            self.detail_color = vary_color((90, 75, 65), 10)
            self.wound_color = (160, 60, 60)
        elif zombie_type == "zombie_king":
            # ZOMBIE KING - Ultimate boss with stages
            # Health and damage scale with stage
            stage_multiplier = king_stage
            self.health = 1000 * stage_multiplier + wave * 100
            self.speed = 60 + stage_multiplier * 5
            self.damage = 75 * stage_multiplier  # Massive damage
            self.size = 60 + stage_multiplier * 5  # Gets bigger each stage
            self.is_boss = True
            self.king_stage = king_stage
            self.slam_cooldown = 0  # Area attack cooldown
            self.slam_radius = 150 + stage_multiplier * 20
            self.roar_cooldown = 0
            self.spawn_cooldown = 0  # Can spawn minions
            # Royal dark purple/black colors
            base_colors = [(60, 30, 80), (50, 25, 70), (70, 35, 90)]
            self.skin_color = vary_color(random.choice(base_colors), 10)
            self.detail_color = vary_color((40, 20, 50), 8)
            self.wound_color = (120, 40, 120)  # Purple blood
            self.crown_color = (200, 170, 50)  # Golden crown
        else:
            # Default fallback
            self.health = 50 + wave * 10
            self.speed = 80 + wave * 2
            self.damage = 10 + wave
            self.size = 20
            self.skin_color = (85, 107, 85)
            self.detail_color = (60, 75, 55)
            self.wound_color = (120, 50, 50)

        self.max_health = self.health
        self.active = True
        self.attack_cooldown = 0
        self.target = None
        self.angle = 0
        self.knockback_vx = 0
        self.knockback_vy = 0

    def update(self, dt, players, walls, bunker=None, all_zombies=None):
        # Apply knockback
        if abs(self.knockback_vx) > 1 or abs(self.knockback_vy) > 1:
            self.x += self.knockback_vx * dt
            self.y += self.knockback_vy * dt
            self.knockback_vx *= 0.9
            self.knockback_vy *= 0.9

        # Radioactive zombie - update glow and damage nearby players
        if self.zombie_type == "radioactive":
            self.glow_pulse = (self.glow_pulse + dt * 3) % (math.pi * 2)
            # Damage nearby players with radiation
            for player in players:
                if player.health > 0:
                    dist = math.sqrt((player.x - self.x)**2 + (player.y - self.y)**2)
                    if dist < self.radiation_radius:
                        player.take_damage(self.radiation_damage * dt)

        # Cage Walker - command nearby zombies to attack bunker
        if self.zombie_type == "cage_walker" and all_zombies and bunker:
            self.roar_cooldown -= dt
            if self.roar_cooldown <= 0:
                # Command nearby zombies to target bunker
                for zombie in all_zombies:
                    if zombie != self and zombie.active:
                        dist = math.sqrt((zombie.x - self.x)**2 + (zombie.y - self.y)**2)
                        if dist < self.command_radius:
                            zombie.target_bunker = True
                self.roar_cooldown = 5.0  # Roar every 5 seconds

        # Zombie King - special abilities
        if self.zombie_type == "zombie_king" and all_zombies:
            # Ground slam attack
            self.slam_cooldown -= dt
            if self.slam_cooldown <= 0:
                # Area damage to all nearby players
                for player in players:
                    if player.health > 0 and not getattr(player, 'is_traitor', False):
                        dist = math.sqrt((player.x - self.x)**2 + (player.y - self.y)**2)
                        if dist < self.slam_radius:
                            player.take_damage(self.damage * 0.5)  # 50% of normal damage
                self.slam_cooldown = 4.0  # Slam every 4 seconds

            # Command all zombies to attack
            self.roar_cooldown -= dt
            if self.roar_cooldown <= 0:
                for zombie in all_zombies:
                    if zombie != self and zombie.active:
                        zombie.target_bunker = True
                self.roar_cooldown = 8.0  # Roar every 8 seconds

        # Find nearest target (player, wall, or bunker)
        nearest_dist = float('inf')
        nearest_target = None
        target_type = None

        # Check if commanded to attack bunker (priority target)
        should_target_bunker = getattr(self, 'target_bunker', False) or self.zombie_type == "cage_walker"

        if should_target_bunker and bunker and bunker.health > 0:
            # Commanded zombies prioritize bunker
            dist = math.sqrt((bunker.x - self.x)**2 + (bunker.y - self.y)**2)
            nearest_dist = dist
            nearest_target = bunker
            target_type = "bunker"
        else:
            # Normal zombies: find nearest player first (ignore traitors!)
            for player in players:
                if player.health > 0 and not getattr(player, 'is_traitor', False):
                    dist = math.sqrt((player.x - self.x)**2 + (player.y - self.y)**2)
                    if dist < nearest_dist:
                        nearest_dist = dist
                        nearest_target = player
                        target_type = "player"

            # If no player nearby (within 400 units), target bunker instead
            if bunker and bunker.health > 0 and (nearest_target is None or nearest_dist > 400):
                bunker_dist = math.sqrt((bunker.x - self.x)**2 + (bunker.y - self.y)**2)
                if nearest_target is None or bunker_dist < nearest_dist:
                    nearest_dist = bunker_dist
                    nearest_target = bunker
                    target_type = "bunker"

        # Check walls in path (walls block path to target)
        for wall in walls:
            if wall.active:
                dist = math.sqrt((wall.x - self.x)**2 + (wall.y - self.y)**2)
                if dist < nearest_dist and dist < 200:
                    nearest_dist = dist
                    nearest_target = wall
                    target_type = "wall"

        self.target = nearest_target

        if nearest_target:
            # Calculate angle to target
            dx = nearest_target.x - self.x
            dy = nearest_target.y - self.y
            self.angle = math.atan2(dy, dx)

            # Move towards target
            if target_type == "player" and nearest_dist > 30:
                self.x += math.cos(self.angle) * self.speed * dt
                self.y += math.sin(self.angle) * self.speed * dt
            elif target_type == "wall" and nearest_dist > 50:
                self.x += math.cos(self.angle) * self.speed * dt
                self.y += math.sin(self.angle) * self.speed * dt
            elif target_type == "bunker" and nearest_dist > 80:
                self.x += math.cos(self.angle) * self.speed * dt
                self.y += math.sin(self.angle) * self.speed * dt

            # Attack
            self.attack_cooldown -= dt
            if self.attack_cooldown <= 0:
                if target_type == "player" and nearest_dist < 40:
                    nearest_target.take_damage(self.damage)
                    self.attack_cooldown = 1.0
                elif target_type == "bunker" and nearest_dist < 100:
                    nearest_target.take_damage(self.damage)
                    self.attack_cooldown = 1.5
                elif target_type == "wall" and nearest_dist < 60:
                    nearest_target.take_damage(self.damage * 2)
                    self.attack_cooldown = 0.5

        return self.active

    def take_damage(self, damage, knockback_angle=None):
        self.health -= damage
        if knockback_angle is not None:
            knockback_force = min(damage * 3, 200)
            self.knockback_vx = math.cos(knockback_angle) * knockback_force
            self.knockback_vy = math.sin(knockback_angle) * knockback_force
        if self.health <= 0:
            self.active = False
            return True  # Killed
        return False

    def draw(self, screen, camera_offset):
        draw_x = int(self.x - camera_offset[0])
        draw_y = int(self.y - camera_offset[1])

        # Body - main shape
        pygame.draw.circle(screen, self.skin_color, (draw_x, draw_y), self.size)

        # Body details/shading
        pygame.draw.circle(screen, self.detail_color, (draw_x, draw_y), self.size, 3)

        # Wound marks (random based on damage taken)
        health_ratio = self.health / self.max_health
        if health_ratio < 0.8:
            # Add wound details as health decreases
            wound_size = int(self.size * 0.3 * (1 - health_ratio))
            wound_x = draw_x + int(self.size * 0.3)
            wound_y = draw_y - int(self.size * 0.2)
            pygame.draw.circle(screen, self.wound_color, (wound_x, wound_y), max(2, wound_size))

        if health_ratio < 0.5:
            wound_x2 = draw_x - int(self.size * 0.4)
            wound_y2 = draw_y + int(self.size * 0.3)
            pygame.draw.circle(screen, self.wound_color, (wound_x2, wound_y2), max(2, wound_size))

        # Type-specific visual features
        if self.zombie_type == "tank":
            # Muscular arms
            arm_angle1 = self.angle + 0.5
            arm_angle2 = self.angle - 0.5
            arm_x1 = draw_x + int(math.cos(arm_angle1) * self.size * 0.8)
            arm_y1 = draw_y + int(math.sin(arm_angle1) * self.size * 0.8)
            arm_x2 = draw_x + int(math.cos(arm_angle2) * self.size * 0.8)
            arm_y2 = draw_y + int(math.sin(arm_angle2) * self.size * 0.8)
            pygame.draw.circle(screen, self.skin_color, (arm_x1, arm_y1), 10)
            pygame.draw.circle(screen, self.skin_color, (arm_x2, arm_y2), 10)

        elif self.zombie_type == "spitter":
            # Glowing toxic mouth
            mouth_x = draw_x + int(math.cos(self.angle) * self.size * 0.5)
            mouth_y = draw_y + int(math.sin(self.angle) * self.size * 0.5)
            pygame.draw.circle(screen, (150, 200, 50), (mouth_x, mouth_y), 6)
            pygame.draw.circle(screen, (180, 230, 80), (mouth_x, mouth_y), 3)

        elif self.zombie_type == "bloater":
            # Bloated bumps
            for i in range(3):
                bump_angle = self.angle + i * 2.1
                bump_x = draw_x + int(math.cos(bump_angle) * self.size * 0.6)
                bump_y = draw_y + int(math.sin(bump_angle) * self.size * 0.6)
                pygame.draw.circle(screen, self.wound_color, (bump_x, bump_y), 5)

        elif self.zombie_type == "crawler":
            # Lower profile, elongated
            pygame.draw.ellipse(screen, self.skin_color,
                              (draw_x - self.size, draw_y - self.size//2, self.size * 2, self.size))

        elif self.zombie_type == "radioactive":
            # Pulsing radioactive glow
            glow_intensity = int(50 + 30 * math.sin(self.glow_pulse))
            glow_radius = self.size + 10 + int(5 * math.sin(self.glow_pulse))
            # Draw glow effect
            for r in range(3):
                glow_color = (0, glow_intensity + r * 30, 0)
                pygame.draw.circle(screen, glow_color, (draw_x, draw_y), glow_radius - r * 5, 2)
            # Radiation symbol
            pygame.draw.circle(screen, (255, 255, 0), (draw_x, draw_y - self.size//2), 5)

        elif self.zombie_type == "cage_walker":
            # Large armored boss with cage-like pattern
            # Draw cage bars over body
            for i in range(4):
                bar_angle = i * math.pi / 2
                x1 = draw_x + int(math.cos(bar_angle) * self.size * 0.3)
                y1 = draw_y + int(math.sin(bar_angle) * self.size * 0.3)
                x2 = draw_x + int(math.cos(bar_angle) * self.size)
                y2 = draw_y + int(math.sin(bar_angle) * self.size)
                pygame.draw.line(screen, self.cage_color, (x1, y1), (x2, y2), 3)
            # Cross bars
            pygame.draw.circle(screen, self.cage_color, (draw_x, draw_y), self.size - 10, 2)
            # Boss indicator - skull crown
            pygame.draw.polygon(screen, (200, 200, 50), [
                (draw_x - 15, draw_y - self.size - 5),
                (draw_x, draw_y - self.size - 20),
                (draw_x + 15, draw_y - self.size - 5)
            ])

        # Eyes (facing direction) - different for each type
        eye_offset = self.size * 0.4
        eye_x = draw_x + math.cos(self.angle) * eye_offset
        eye_y = draw_y + math.sin(self.angle) * eye_offset

        if self.zombie_type == "runner":
            # Wide, frantic eyes
            pygame.draw.circle(screen, (255, 200, 200), (int(eye_x - 5), int(eye_y)), 5)
            pygame.draw.circle(screen, (255, 200, 200), (int(eye_x + 5), int(eye_y)), 5)
            pygame.draw.circle(screen, RED, (int(eye_x - 5), int(eye_y)), 2)
            pygame.draw.circle(screen, RED, (int(eye_x + 5), int(eye_y)), 2)
        elif self.zombie_type == "tank":
            # Small, angry eyes
            pygame.draw.circle(screen, (200, 50, 50), (int(eye_x - 6), int(eye_y)), 4)
            pygame.draw.circle(screen, (200, 50, 50), (int(eye_x + 6), int(eye_y)), 4)
        elif self.zombie_type == "spitter":
            # Glowing yellow eyes
            pygame.draw.circle(screen, (200, 220, 50), (int(eye_x - 4), int(eye_y)), 4)
            pygame.draw.circle(screen, (200, 220, 50), (int(eye_x + 4), int(eye_y)), 4)
        elif self.zombie_type == "bloater":
            # Milky, dead eyes
            pygame.draw.circle(screen, (180, 180, 190), (int(eye_x - 5), int(eye_y)), 5)
            pygame.draw.circle(screen, (180, 180, 190), (int(eye_x + 5), int(eye_y)), 5)
        elif self.zombie_type == "radioactive":
            # Glowing bright green eyes
            pygame.draw.circle(screen, (150, 255, 150), (int(eye_x - 5), int(eye_y)), 5)
            pygame.draw.circle(screen, (150, 255, 150), (int(eye_x + 5), int(eye_y)), 5)
            pygame.draw.circle(screen, (50, 255, 50), (int(eye_x - 5), int(eye_y)), 3)
            pygame.draw.circle(screen, (50, 255, 50), (int(eye_x + 5), int(eye_y)), 3)
        elif self.zombie_type == "cage_walker":
            # Burning orange/red eyes - boss
            pygame.draw.circle(screen, (255, 150, 50), (int(eye_x - 8), int(eye_y)), 7)
            pygame.draw.circle(screen, (255, 150, 50), (int(eye_x + 8), int(eye_y)), 7)
            pygame.draw.circle(screen, (255, 50, 0), (int(eye_x - 8), int(eye_y)), 4)
            pygame.draw.circle(screen, (255, 50, 0), (int(eye_x + 8), int(eye_y)), 4)
        else:
            # Normal red eyes
            pygame.draw.circle(screen, (200, 60, 60), (int(eye_x - 4), int(eye_y)), 4)
            pygame.draw.circle(screen, (200, 60, 60), (int(eye_x + 4), int(eye_y)), 4)

        # Health bar
        if self.health < self.max_health:
            bar_width = self.size * 2
            pygame.draw.rect(screen, (80, 20, 20), (draw_x - bar_width//2, draw_y - self.size - 10, bar_width, 5))
            pygame.draw.rect(screen, (50, 180, 50), (draw_x - bar_width//2, draw_y - self.size - 10, int(bar_width * health_ratio), 5))


class Player:
    """Player class with class-specific abilities."""
    def __init__(self, x, y, player_id=0, player_class=PlayerClass.RANGER):
        self.x = x
        self.y = y
        self.player_id = player_id
        self.player_class = player_class
        self.angle = 0
        self.size = 25

        # Class-specific stats
        self.setup_class(player_class)

        # Combat
        self.current_weapon_index = 0
        self.current_ammo = self.weapons[0].mag_size if self.weapons else 0
        self.reserve_ammo = self.weapons[0].max_ammo if self.weapons else 0
        self.fire_cooldown = 0
        self.reload_timer = 0
        self.reload_time_max = 0  # Store max reload time for animation
        self.is_reloading = False
        self.recoil_offset = 0  # Current recoil affecting accuracy
        self.screen_shake = 0  # Visual feedback for heavy weapons
        self.muzzle_flash_timer = 0  # Muzzle flash effect
        self.shell_casings = []  # Ejected shell casings
        self.gun_kick = 0  # Visual gun kickback
        self.reload_anim_angle = 0  # Gun rotation during reload
        self.recoil_angle = 0  # Visual angle kick when shooting

        # Movement
        self.vx = 0
        self.vy = 0

        # Abilities
        self.ability_cooldown = 0
        self.walls_built = []
        self.heal_zones = []
        self.speed_boost_timer = 0  # For Ranger speed boost

        # Input state
        self.keys_pressed = set()
        self.mouse_pos = (0, 0)
        self.mouse_buttons = [False, False, False]
        self.auto_aim = False  # For P2+ who can't use mouse
        self.auto_shoot = False  # P2 auto-shoots at enemies
        self.unlimited_ammo = False  # For testing
        self.invincible = False  # For testing

        # HP Regeneration
        self.regen_timer = 0  # Timer for HP regen

        # Healer items
        self.bandages = 0  # Heals other players, 1 use each
        self.medkits = 0   # Heals to full, 3 uses

        # Builder rotation
        self.block_rotation = 0  # 0, 90, 180, 270 degrees
        self.show_block_preview = False  # Show placement preview

        # Traitor specific
        self.is_traitor = False
        self.zombie_spawn_cooldown = 0

    def setup_class(self, player_class):
        self.player_class = player_class

        if player_class == PlayerClass.BUILDER:
            self.max_health = 120
            self.speed = 200
            # Builder: Nail gun + sidearm + knife
            self.weapons = [WEAPONS["nail_gun"], WEAPONS["glock"], WEAPONS["knife"]]
            self.color = ORANGE
            self.ability_max_cooldown = 3  # Wall building cooldown
            self.max_walls = 10

        elif player_class == PlayerClass.RANGER:
            self.max_health = 100
            self.speed = 220
            # Ranger: Full weapon arsenal + knife
            self.weapons = [
                WEAPONS["rifle"],      # Assault Rifle - Primary
                WEAPONS["ak47"],       # Heavy Rifle
                WEAPONS["shotgun"],    # Shotgun
                WEAPONS["sniper"],     # Sniper Rifle
                WEAPONS["pistol"],     # Pistol backup
                WEAPONS["knife"],      # Combat Knife
            ]
            self.color = GREEN
            self.ability_max_cooldown = 15  # Speed boost

        elif player_class == PlayerClass.HEALER:
            self.max_health = 90
            self.speed = 210
            # Healer: SMGs and pistol + knife
            self.weapons = [
                WEAPONS["smg"],        # SMG
                WEAPONS["p90"],        # PDW
                WEAPONS["tranq_pistol"],
                WEAPONS["knife"],      # Combat Knife
            ]
            self.color = LIGHT_BLUE
            self.ability_max_cooldown = 12  # Heal zone
            # Healer items
            self.bandages = 5  # Heals other players 30 HP, 1 use each
            self.medkits = 3   # Heals to full, 3 uses total

        elif player_class == PlayerClass.TANK:
            self.max_health = 180
            self.speed = 140
            # Tank: Heavy weapons + Desert Eagle + Knife
            self.weapons = [
                WEAPONS["minigun"],         # Minigun
                WEAPONS["rpg"],             # Rocket Launcher
                WEAPONS["grenade_launcher"], # Grenade Launcher
                WEAPONS["spas12"],          # Auto Shotgun
                WEAPONS["deagle"],          # Desert Eagle backup
                WEAPONS["knife"],           # Combat Knife
            ]
            self.color = RED
            self.ability_max_cooldown = 20  # Ground slam

        elif player_class == PlayerClass.TRAITOR:
            self.max_health = 100
            self.speed = 200
            # Traitor: Basic weapons, allied with zombies + Knife
            self.weapons = [
                WEAPONS["pistol"],     # Basic pistol
                WEAPONS["smg"],        # SMG
                WEAPONS["knife"],      # Combat Knife
            ]
            self.color = PURPLE
            self.ability_max_cooldown = 8  # Spawn zombie cooldown
            self.is_traitor = True

        self.health = self.max_health
        self.current_weapon_index = 0
        self.current_ammo = self.weapons[0].mag_size
        self.reserve_ammo = self.weapons[0].max_ammo

    @property
    def current_weapon(self):
        return self.weapons[self.current_weapon_index]

    def take_damage(self, damage):
        if self.invincible:
            return  # No damage when invincible
        self.health -= damage
        if self.health < 0:
            self.health = 0

    def heal(self, amount):
        self.health = min(self.health + amount, self.max_health)

    def switch_weapon(self, direction):
        self.current_weapon_index = (self.current_weapon_index + direction) % len(self.weapons)
        self.current_ammo = self.current_weapon.mag_size
        self.reserve_ammo = self.current_weapon.max_ammo
        self.is_reloading = False
        self.reload_timer = 0

    def update(self, dt, game_world):
        # Dead players can't move or do anything
        if self.health <= 0:
            return

        # HP Regeneration - 1 HP every 3 seconds (not for traitors)
        if not self.is_traitor and self.health > 0 and self.health < self.max_health:
            self.regen_timer += dt
            if self.regen_timer >= 3.0:
                self.regen_timer = 0
                self.heal(1)

        # Movement
        move_x = 0
        move_y = 0

        # Each player has their own keys based on player_id
        # P1 (id=0): WASD/Arrows, P2 (id=1): IJKL, P3 (id=2): TFGH
        if self.player_id == 0:
            # Player 1: WASD or Arrow keys
            if pygame.K_w in self.keys_pressed or pygame.K_UP in self.keys_pressed:
                move_y -= 1
            if pygame.K_s in self.keys_pressed or pygame.K_DOWN in self.keys_pressed:
                move_y += 1
            if pygame.K_a in self.keys_pressed or pygame.K_LEFT in self.keys_pressed:
                move_x -= 1
            if pygame.K_d in self.keys_pressed or pygame.K_RIGHT in self.keys_pressed:
                move_x += 1
        elif self.player_id == 1:
            # Player 2: IJKL keys
            if pygame.K_i in self.keys_pressed:
                move_y -= 1
            if pygame.K_k in self.keys_pressed:
                move_y += 1
            if pygame.K_j in self.keys_pressed:
                move_x -= 1
            if pygame.K_l in self.keys_pressed:
                move_x += 1
        elif self.player_id == 2:
            # Player 3: TFGH keys
            if pygame.K_t in self.keys_pressed:
                move_y -= 1
            if pygame.K_g in self.keys_pressed:
                move_y += 1
            if pygame.K_f in self.keys_pressed:
                move_x -= 1
            if pygame.K_h in self.keys_pressed:
                move_x += 1

        # Normalize diagonal movement
        if move_x != 0 and move_y != 0:
            move_x *= 0.707
            move_y *= 0.707

        # Apply speed boost for Ranger
        current_speed = self.speed
        if self.speed_boost_timer > 0:
            current_speed = self.speed * 1.5  # 50% speed boost
            self.speed_boost_timer -= dt

        # Sprint with Shift key (40% faster)
        if pygame.K_LSHIFT in self.keys_pressed or pygame.K_RSHIFT in self.keys_pressed:
            current_speed *= 1.4

        self.x += move_x * current_speed * dt
        self.y += move_y * current_speed * dt

        # Keep in bounds
        self.x = max(self.size, min(game_world.width - self.size, self.x))
        self.y = max(self.size, min(game_world.height - self.size, self.y))

        # Aim: Player 1 uses mouse, Player 2 uses 8/9, Player 3 uses 6/7
        if self.player_id == 0:
            # Player 1: Mouse aim
            screen_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            dx = self.mouse_pos[0] - screen_center[0]
            dy = self.mouse_pos[1] - screen_center[1]
            self.angle = math.atan2(dy, dx)
        elif self.player_id == 1:
            # Player 2: Manual aim with 8/9 keys (continuous rotation while held)
            aim_speed = 3.0  # Radians per second
            if pygame.K_8 in self.keys_pressed:
                self.angle -= aim_speed * dt  # Rotate left
            if pygame.K_9 in self.keys_pressed:
                self.angle += aim_speed * dt  # Rotate right
        elif self.player_id == 2:
            # Player 3: Auto-aim at nearest zombie
            if self.auto_aim and game_world.zombies:
                nearest_zombie = None
                nearest_dist = float('inf')
                shooting_range = self.current_weapon.range  # Use weapon range
                for zombie in game_world.zombies:
                    dist = math.sqrt((zombie.x - self.x)**2 + (zombie.y - self.y)**2)
                    if dist < nearest_dist:
                        nearest_dist = dist
                        nearest_zombie = zombie
                if nearest_zombie:
                    dx = nearest_zombie.x - self.x
                    dy = nearest_zombie.y - self.y
                    self.angle = math.atan2(dy, dx)
                    # Only auto-fire if zombie is in shooting range
                    if nearest_dist <= shooting_range:
                        self.mouse_buttons[0] = True
                    else:
                        self.mouse_buttons[0] = False
                else:
                    # No zombie found, stop firing
                    self.mouse_buttons[0] = False
            else:
                # No zombies, stop firing
                if self.auto_aim:
                    self.mouse_buttons[0] = False
                # Manual aim with 6/7 keys (continuous rotation while held)
                aim_speed = 3.0  # Radians per second
                if pygame.K_6 in self.keys_pressed:
                    self.angle -= aim_speed * dt  # Rotate left
                if pygame.K_7 in self.keys_pressed:
                    self.angle += aim_speed * dt  # Rotate right

        # Cooldowns
        self.fire_cooldown -= dt
        self.ability_cooldown -= dt

        # Recoil recovery (accuracy returns to normal over time)
        if self.recoil_offset > 0:
            self.recoil_offset = max(0, self.recoil_offset - 15 * dt)

        # Screen shake decay
        if self.screen_shake > 0:
            self.screen_shake = max(0, self.screen_shake - 20 * dt)

        # Muzzle flash decay
        if self.muzzle_flash_timer > 0:
            self.muzzle_flash_timer -= dt

        # Gun kick recovery (gun returns to position)
        if self.gun_kick > 0:
            self.gun_kick = max(0, self.gun_kick - 80 * dt)

        # Recoil angle recovery (aim returns to original position)
        if self.recoil_angle != 0:
            # Smooth return to 0
            self.recoil_angle *= 0.85  # Decay
            if abs(self.recoil_angle) < 0.5:
                self.recoil_angle = 0

        # Update shell casings
        for shell in self.shell_casings[:]:
            shell['x'] += shell['vx'] * dt
            shell['y'] += shell['vy'] * dt
            shell['vy'] += 300 * dt  # Gravity
            shell['rotation'] += shell['rot_speed'] * dt
            shell['lifetime'] -= dt
            if shell['lifetime'] <= 0:
                self.shell_casings.remove(shell)

        # Reloading with animation
        if self.is_reloading:
            self.reload_timer -= dt
            # Calculate reload animation (gun rotates down and back up)
            if self.reload_time_max > 0:
                progress = 1 - (self.reload_timer / self.reload_time_max)
                # Smooth animation: rotate down first half, rotate back up second half
                if progress < 0.5:
                    self.reload_anim_angle = progress * 2 * 45  # 0 to 45 degrees
                else:
                    self.reload_anim_angle = (1 - progress) * 2 * 45  # 45 to 0 degrees
            if self.reload_timer <= 0:
                ammo_needed = self.current_weapon.mag_size - self.current_ammo
                ammo_to_add = min(ammo_needed, self.reserve_ammo)
                self.current_ammo += ammo_to_add
                self.reserve_ammo -= ammo_to_add
                self.is_reloading = False
                self.reload_anim_angle = 0

        # Shooting (mouse or auto-shoot for P2)
        shooting = self.mouse_buttons[0] or self.auto_shoot
        if shooting and self.fire_cooldown <= 0 and not self.is_reloading:
            if self.current_ammo > 0:
                self.shoot(game_world)

        # Update heal zones
        for zone in self.heal_zones[:]:
            if not zone.update(dt):
                self.heal_zones.remove(zone)

    def shoot(self, game_world):
        # Dead players can't shoot
        if self.health <= 0:
            return

        weapon = self.current_weapon
        self.fire_cooldown = 1.0 / weapon.fire_rate

        # Check if this is a melee weapon (knife)
        if 'knife' in weapon.name.lower() or weapon.bullet_speed == 0:
            # MELEE ATTACK - knife slash
            self.gun_kick = 8  # Slash animation

            # Find zombies in melee range
            melee_range = 60
            slash_x = self.x + math.cos(self.angle) * melee_range
            slash_y = self.y + math.sin(self.angle) * melee_range

            for zombie in game_world.zombies[:]:
                dist = math.sqrt((zombie.x - slash_x)**2 + (zombie.y - slash_y)**2)
                if dist < 50:  # Hit range
                    # Calculate knife damage based on zombie type
                    if zombie.zombie_type == "tank":
                        # 3 shots to kill
                        knife_damage = zombie.max_health / 3
                    elif zombie.zombie_type == "spitter":
                        # 5 shots to kill
                        knife_damage = zombie.max_health / 5
                    elif zombie.zombie_type == "radioactive":
                        # 6 shots to kill (green glowing)
                        knife_damage = zombie.max_health / 6
                    elif zombie.zombie_type == "cage_walker":
                        # 60 shots to kill
                        knife_damage = zombie.max_health / 60
                    elif zombie.zombie_type == "zombie_king":
                        # Shots based on king stage
                        stage = getattr(zombie, 'king_stage', 1)
                        if stage == 1:
                            knife_damage = zombie.max_health / 100
                        elif stage == 2:
                            knife_damage = zombie.max_health / 1000
                        elif stage == 3:
                            knife_damage = zombie.max_health / 10000
                        elif stage == 4:
                            knife_damage = zombie.max_health / 100000
                        elif stage == 5:
                            knife_damage = zombie.max_health / 1000000
                        elif stage == 6:
                            knife_damage = zombie.max_health / 10000000
                        elif stage == 7:
                            knife_damage = zombie.max_health / 100000000
                        elif stage == 8:
                            knife_damage = zombie.max_health / 1000000000
                        elif stage == 9:
                            knife_damage = zombie.max_health / 10000000000
                        else:  # stage 10+
                            knife_damage = zombie.max_health / 100000000000
                    else:
                        # Instant kill regular zombies (normal, runner, crawler, bloater, etc.)
                        knife_damage = 9999

                    zombie.take_damage(knife_damage, self.angle)
                    if zombie.health <= 0:
                        game_world.kills += 1
                        game_world.score += 100

            # Slash particles (white/silver)
            for _ in range(8):
                angle = self.angle + random.uniform(-0.8, 0.8)
                speed = random.uniform(150, 300)
                game_world.particles.append(Particle(
                    slash_x, slash_y, (200, 200, 220),
                    (math.cos(angle) * speed, math.sin(angle) * speed),
                    random.uniform(0.1, 0.2), 3
                ))
            return  # Don't shoot bullets for melee

        # Regular gun shooting
        if not self.unlimited_ammo:
            self.current_ammo -= 1

        # Apply recoil to spread - accuracy degrades with rapid fire
        effective_spread = weapon.spread + self.recoil_offset

        # Add recoil from this shot (accumulates with rapid fire)
        self.recoil_offset = min(self.recoil_offset + weapon.recoil, weapon.spread * 3)

        # Gun kick visual effect (gun moves back then returns)
        self.gun_kick = min(weapon.recoil * 4, 20)

        # Recoil angle kick (aim jumps up/back)
        self.recoil_angle -= weapon.recoil * 3  # Negative = kicks up/back

        # Muzzle flash effect
        self.muzzle_flash_timer = 0.05  # Flash lasts 50ms

        # Screen shake for all weapons (scaled by recoil)
        self.screen_shake = min(weapon.recoil * 1.5, 10)

        # Create bullets
        for _ in range(weapon.bullet_count):
            spread = math.radians(random.uniform(-effective_spread, effective_spread))
            bullet_angle = self.angle + spread

            # Bullet starts at gun position
            gun_dist = self.size + 10
            bx = self.x + math.cos(self.angle) * gun_dist
            by = self.y + math.sin(self.angle) * gun_dist

            bullet = Bullet(bx, by, bullet_angle, weapon, self.player_id)
            game_world.bullets.append(bullet)

        # Muzzle flash particles (more intense)
        flash_intensity = min(weapon.damage / 30, 3)  # Bigger guns = bigger flash
        for _ in range(int(5 * flash_intensity)):
            angle = self.angle + random.uniform(-0.5, 0.5)
            speed = random.uniform(100, 300) * flash_intensity
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice([YELLOW, ORANGE, (255, 200, 100)])
            game_world.particles.append(Particle(
                self.x + math.cos(self.angle) * (self.size + 15),
                self.y + math.sin(self.angle) * (self.size + 15),
                color, (vx, vy), random.uniform(0.05, 0.15), random.randint(3, 6)
            ))

        # Shell casing ejection (not for rockets/grenades)
        if not weapon.explosive:
            shell_angle = self.angle + math.pi/2 + random.uniform(-0.3, 0.3)  # Eject to the side
            shell_speed = random.uniform(80, 150)
            self.shell_casings.append({
                'x': self.x + math.cos(self.angle) * self.size,
                'y': self.y + math.sin(self.angle) * self.size,
                'vx': math.cos(shell_angle) * shell_speed,
                'vy': math.sin(shell_angle) * shell_speed + random.uniform(-50, 0),
                'rotation': random.uniform(0, 360),
                'rot_speed': random.uniform(-500, 500),
                'lifetime': 1.0,
                'size': 4 if 'pistol' in weapon.name.lower() or 'smg' in weapon.name.lower() else 6
            })

        # Auto-reload when empty
        if self.current_ammo <= 0 and self.reserve_ammo > 0:
            self.start_reload()

    def start_reload(self):
        if not self.is_reloading and self.reserve_ammo > 0 and self.current_ammo < self.current_weapon.mag_size:
            self.is_reloading = True
            self.reload_timer = self.current_weapon.reload_time
            self.reload_time_max = self.current_weapon.reload_time

    def use_ability(self, game_world):
        # Dead players can't use abilities
        if self.health <= 0:
            return

        if self.ability_cooldown > 0:
            return

        if self.player_class == PlayerClass.BUILDER:
            # Build wall with rotation
            if len([w for w in game_world.walls if w.active]) < self.max_walls:
                wall_x = self.x + math.cos(self.angle) * 80
                wall_y = self.y + math.sin(self.angle) * 80
                # Apply rotation to wall dimensions
                if self.block_rotation == 0 or self.block_rotation == 180:
                    wall = Wall(wall_x, wall_y, width=320, height=80)
                else:  # 90 or 270 degrees - swap width/height
                    wall = Wall(wall_x, wall_y, width=80, height=320)
                game_world.walls.append(wall)
                self.walls_built.append(wall)
                self.ability_cooldown = self.ability_max_cooldown
                # Hide blueprint preview after placing
                self.show_block_preview = False

        elif self.player_class == PlayerClass.RANGER:
            # Speed boost - 50% faster for 5 seconds
            self.speed_boost_timer = 5.0
            self.ability_cooldown = self.ability_max_cooldown

        elif self.player_class == PlayerClass.HEALER:
            # Create heal zone
            zone = HealZone(self.x, self.y)
            self.heal_zones.append(zone)
            game_world.heal_zones.append(zone)
            self.ability_cooldown = self.ability_max_cooldown

        elif self.player_class == PlayerClass.TANK:
            # Ground slam - damages nearby zombies
            for zombie in game_world.zombies:
                dist = math.sqrt((zombie.x - self.x)**2 + (zombie.y - self.y)**2)
                if dist < 150:
                    damage = 100 * (1 - dist / 150)
                    angle = math.atan2(zombie.y - self.y, zombie.x - self.x)
                    zombie.take_damage(damage, angle)

            # Slam particles
            for _ in range(30):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(200, 400)
                game_world.particles.append(Particle(
                    self.x, self.y, ORANGE,
                    (math.cos(angle) * speed, math.sin(angle) * speed),
                    random.uniform(0.3, 0.6), 6
                ))
            self.ability_cooldown = self.ability_max_cooldown

        elif self.player_class == PlayerClass.TRAITOR:
            # Spawn a speed zombie to fight for you
            spawn_x = self.x + math.cos(self.angle) * 50
            spawn_y = self.y + math.sin(self.angle) * 50
            zombie = Zombie(spawn_x, spawn_y, "speed", game_world.current_wave)
            game_world.zombies.append(zombie)
            self.ability_cooldown = self.ability_max_cooldown
            # Purple particle effect
            for _ in range(15):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(100, 200)
                game_world.particles.append(Particle(
                    spawn_x, spawn_y, PURPLE,
                    (math.cos(angle) * speed, math.sin(angle) * speed),
                    random.uniform(0.2, 0.4), 5
                ))

    def rotate_block(self):
        """Rotate block placement direction for Builder."""
        if self.player_class == PlayerClass.BUILDER:
            self.block_rotation = (self.block_rotation + 90) % 360
            # Keep preview showing while rotating

    def draw(self, screen, camera_offset, is_local=True):
        draw_x = int(self.x - camera_offset[0])
        draw_y = int(self.y - camera_offset[1])

        # Speed boost visual effect (glowing ring)
        if self.speed_boost_timer > 0:
            pygame.draw.circle(screen, YELLOW, (draw_x, draw_y), self.size + 8, 3)
            pygame.draw.circle(screen, ORANGE, (draw_x, draw_y), self.size + 5, 2)

        # Body
        pygame.draw.circle(screen, self.color, (draw_x, draw_y), self.size)
        pygame.draw.circle(screen, WHITE, (draw_x, draw_y), self.size, 2)

        # Class indicator
        if self.player_class == PlayerClass.BUILDER:
            # Hammer icon
            pygame.draw.rect(screen, BROWN, (draw_x - 5, draw_y - 8, 10, 16))
        elif self.player_class == PlayerClass.RANGER:
            # Crosshair
            pygame.draw.line(screen, WHITE, (draw_x - 8, draw_y), (draw_x + 8, draw_y), 2)
            pygame.draw.line(screen, WHITE, (draw_x, draw_y - 8), (draw_x, draw_y + 8), 2)
        elif self.player_class == PlayerClass.HEALER:
            # Cross
            pygame.draw.rect(screen, WHITE, (draw_x - 8, draw_y - 3, 16, 6))
            pygame.draw.rect(screen, WHITE, (draw_x - 3, draw_y - 8, 6, 16))
        elif self.player_class == PlayerClass.TANK:
            # Explosion symbol
            pygame.draw.polygon(screen, YELLOW, [
                (draw_x, draw_y - 10), (draw_x + 5, draw_y - 3),
                (draw_x + 10, draw_y - 5), (draw_x + 5, draw_y),
                (draw_x + 8, draw_y + 8), (draw_x, draw_y + 4),
                (draw_x - 8, draw_y + 8), (draw_x - 5, draw_y),
                (draw_x - 10, draw_y - 5), (draw_x - 5, draw_y - 3)
            ])
        elif self.player_class == PlayerClass.TRAITOR:
            # Skull icon (traitor)
            pygame.draw.circle(screen, WHITE, (draw_x, draw_y - 2), 6)  # Skull
            pygame.draw.circle(screen, DARK_GRAY, (draw_x - 2, draw_y - 3), 2)  # Left eye
            pygame.draw.circle(screen, DARK_GRAY, (draw_x + 2, draw_y - 3), 2)  # Right eye
            pygame.draw.line(screen, DARK_GRAY, (draw_x - 2, draw_y + 2), (draw_x + 2, draw_y + 2), 1)  # Teeth

        # Builder block preview
        if self.player_class == PlayerClass.BUILDER and self.show_block_preview:
            preview_x = int(self.x + math.cos(self.angle) * 80 - camera_offset[0])
            preview_y = int(self.y + math.sin(self.angle) * 80 - camera_offset[1])
            if self.block_rotation == 0 or self.block_rotation == 180:
                preview_w, preview_h = 320, 80
            else:
                preview_w, preview_h = 80, 320
            # Blue highlight preview
            preview_surface = pygame.Surface((preview_w, preview_h), pygame.SRCALPHA)
            preview_surface.fill((0, 100, 255, 100))  # Semi-transparent blue
            screen.blit(preview_surface, (preview_x - preview_w//2, preview_y - preview_h//2))
            pygame.draw.rect(screen, BLUE, (preview_x - preview_w//2, preview_y - preview_h//2, preview_w, preview_h), 2)

        # Draw shell casings
        for shell in self.shell_casings:
            shell_x = int(shell['x'] - camera_offset[0])
            shell_y = int(shell['y'] - camera_offset[1])
            # Draw shell as small rectangle
            shell_color = (180, 140, 60)  # Brass color
            pygame.draw.circle(screen, shell_color, (shell_x, shell_y), shell['size'] // 2)

        # Draw realistic gun based on weapon type
        weapon = self.current_weapon
        kick = self.gun_kick

        # Gun angle with reload animation and recoil kick
        gun_angle = self.angle + math.radians(self.reload_anim_angle + self.recoil_angle)

        # Gun position (attached to player)
        gun_x = draw_x + math.cos(gun_angle) * (self.size - kick * 0.3)
        gun_y = draw_y + math.sin(gun_angle) * (self.size - kick * 0.3)

        # Rotate gun graphics based on angle
        cos_a = math.cos(gun_angle)
        sin_a = math.sin(gun_angle)

        # Perpendicular for gun height
        perp_x = -sin_a
        perp_y = cos_a

        # Gun colors
        gun_black = (30, 30, 30)
        gun_dark = (50, 50, 50)
        gun_gray = (70, 70, 70)
        gun_brown = (90, 60, 40)  # Wood/grip

        # Determine gun type and draw appropriate shape
        weapon_name = weapon.name.lower()

        if 'pistol' in weapon_name or 'deagle' in weapon_name:
            # PISTOL - compact with grip
            barrel_len = 18 - kick
            # Barrel
            barrel_end_x = gun_x + cos_a * barrel_len
            barrel_end_y = gun_y + sin_a * barrel_len
            pygame.draw.line(screen, gun_black, (int(gun_x), int(gun_y)), (int(barrel_end_x), int(barrel_end_y)), 6)
            # Slide (top part)
            pygame.draw.line(screen, gun_dark, (int(gun_x - cos_a*5), int(gun_y - sin_a*5)), (int(barrel_end_x), int(barrel_end_y)), 8)
            # Grip (angled down)
            grip_x = gun_x - cos_a * 3 + perp_x * 8
            grip_y = gun_y - sin_a * 3 + perp_y * 8
            pygame.draw.line(screen, gun_brown, (int(gun_x - cos_a*3), int(gun_y - sin_a*3)), (int(grip_x), int(grip_y)), 6)

        elif 'rifle' in weapon_name or 'assault' in weapon_name or 'heavy rifle' in weapon_name:
            # ASSAULT RIFLE - long barrel, stock, magazine
            barrel_len = 35 - kick
            barrel_end_x = gun_x + cos_a * barrel_len
            barrel_end_y = gun_y + sin_a * barrel_len
            # Main body
            pygame.draw.line(screen, gun_black, (int(gun_x - cos_a*10), int(gun_y - sin_a*10)), (int(barrel_end_x), int(barrel_end_y)), 7)
            # Upper rail
            pygame.draw.line(screen, gun_gray, (int(gun_x - cos_a*5), int(gun_y - sin_a*5 - perp_y*2)), (int(gun_x + cos_a*15), int(gun_y + sin_a*15 - perp_y*2)), 3)
            # Magazine
            mag_x = gun_x + cos_a * 5
            mag_y = gun_y + sin_a * 5
            pygame.draw.line(screen, gun_dark, (int(mag_x), int(mag_y)), (int(mag_x + perp_x*12), int(mag_y + perp_y*12)), 5)
            # Stock
            stock_x = gun_x - cos_a * 15
            stock_y = gun_y - sin_a * 15
            pygame.draw.line(screen, gun_brown, (int(gun_x - cos_a*10), int(gun_y - sin_a*10)), (int(stock_x), int(stock_y)), 6)

        elif 'sniper' in weapon_name or 'marksman' in weapon_name:
            # SNIPER RIFLE - very long, scope
            barrel_len = 45 - kick
            barrel_end_x = gun_x + cos_a * barrel_len
            barrel_end_y = gun_y + sin_a * barrel_len
            # Long barrel
            pygame.draw.line(screen, gun_black, (int(gun_x - cos_a*12), int(gun_y - sin_a*12)), (int(barrel_end_x), int(barrel_end_y)), 5)
            # Scope
            scope_x = gun_x + cos_a * 8
            scope_y = gun_y + sin_a * 8 - perp_y * 5
            pygame.draw.circle(screen, gun_gray, (int(scope_x), int(scope_y)), 4)
            pygame.draw.circle(screen, (100, 150, 200), (int(scope_x), int(scope_y)), 2)  # Lens
            # Stock
            pygame.draw.line(screen, gun_brown, (int(gun_x - cos_a*12), int(gun_y - sin_a*12)), (int(gun_x - cos_a*22), int(gun_y - sin_a*22)), 7)

        elif 'shotgun' in weapon_name:
            # SHOTGUN - thick barrel, pump
            barrel_len = 30 - kick
            barrel_end_x = gun_x + cos_a * barrel_len
            barrel_end_y = gun_y + sin_a * barrel_len
            # Thick barrel
            pygame.draw.line(screen, gun_black, (int(gun_x), int(gun_y)), (int(barrel_end_x), int(barrel_end_y)), 9)
            # Pump grip
            pump_x = gun_x + cos_a * 12
            pump_y = gun_y + sin_a * 12
            pygame.draw.line(screen, gun_brown, (int(pump_x - perp_x*4), int(pump_y - perp_y*4)), (int(pump_x + perp_x*6), int(pump_y + perp_y*6)), 6)
            # Stock
            pygame.draw.line(screen, gun_brown, (int(gun_x - cos_a*5), int(gun_y - sin_a*5)), (int(gun_x - cos_a*18), int(gun_y - sin_a*18)), 7)

        elif 'smg' in weapon_name or 'pdw' in weapon_name:
            # SMG - compact, magazine in front
            barrel_len = 22 - kick
            barrel_end_x = gun_x + cos_a * barrel_len
            barrel_end_y = gun_y + sin_a * barrel_len
            # Body
            pygame.draw.line(screen, gun_black, (int(gun_x - cos_a*8), int(gun_y - sin_a*8)), (int(barrel_end_x), int(barrel_end_y)), 6)
            # Magazine (in grip)
            mag_x = gun_x
            mag_y = gun_y
            pygame.draw.line(screen, gun_dark, (int(mag_x), int(mag_y)), (int(mag_x + perp_x*10), int(mag_y + perp_y*10)), 5)
            # Folding stock
            pygame.draw.line(screen, gun_gray, (int(gun_x - cos_a*8), int(gun_y - sin_a*8)), (int(gun_x - cos_a*14), int(gun_y - sin_a*14)), 4)

        elif 'minigun' in weapon_name or 'cyclone' in weapon_name:
            # MINIGUN - multiple barrels, huge
            barrel_len = 40 - kick
            barrel_end_x = gun_x + cos_a * barrel_len
            barrel_end_y = gun_y + sin_a * barrel_len
            # Multiple barrels
            for i in range(-2, 3):
                offset = i * 3
                pygame.draw.line(screen, gun_black,
                    (int(gun_x + perp_x*offset), int(gun_y + perp_y*offset)),
                    (int(barrel_end_x + perp_x*offset), int(barrel_end_y + perp_y*offset)), 3)
            # Housing
            pygame.draw.circle(screen, gun_dark, (int(gun_x), int(gun_y)), 10)
            # Ammo box
            pygame.draw.rect(screen, gun_gray, (int(gun_x - cos_a*15 - 8), int(gun_y - sin_a*15 - 8), 16, 16))

        elif 'rocket' in weapon_name or 'rpg' in weapon_name:
            # ROCKET LAUNCHER - tube
            barrel_len = 38 - kick
            barrel_end_x = gun_x + cos_a * barrel_len
            barrel_end_y = gun_y + sin_a * barrel_len
            # Tube
            pygame.draw.line(screen, (60, 80, 60), (int(gun_x - cos_a*10), int(gun_y - sin_a*10)), (int(barrel_end_x), int(barrel_end_y)), 12)
            pygame.draw.line(screen, (80, 100, 80), (int(gun_x - cos_a*10), int(gun_y - sin_a*10)), (int(barrel_end_x), int(barrel_end_y)), 8)
            # Sight
            pygame.draw.line(screen, gun_black, (int(gun_x + cos_a*5 - perp_x*8), int(gun_y + sin_a*5 - perp_y*8)), (int(gun_x + cos_a*5 - perp_x*14), int(gun_y + sin_a*5 - perp_y*14)), 3)
            # Grip
            pygame.draw.line(screen, gun_brown, (int(gun_x), int(gun_y)), (int(gun_x + perp_x*10), int(gun_y + perp_y*10)), 5)

        elif 'grenade' in weapon_name or 'launcher' in weapon_name:
            # GRENADE LAUNCHER - drum magazine
            barrel_len = 28 - kick
            barrel_end_x = gun_x + cos_a * barrel_len
            barrel_end_y = gun_y + sin_a * barrel_len
            # Barrel
            pygame.draw.line(screen, gun_black, (int(gun_x), int(gun_y)), (int(barrel_end_x), int(barrel_end_y)), 10)
            # Drum magazine
            drum_x = gun_x + cos_a * 8 + perp_x * 8
            drum_y = gun_y + sin_a * 8 + perp_y * 8
            pygame.draw.circle(screen, gun_dark, (int(drum_x), int(drum_y)), 8)
            pygame.draw.circle(screen, gun_gray, (int(drum_x), int(drum_y)), 5)
            # Stock
            pygame.draw.line(screen, gun_brown, (int(gun_x - cos_a*5), int(gun_y - sin_a*5)), (int(gun_x - cos_a*15), int(gun_y - sin_a*15)), 6)

        elif 'knife' in weapon_name:
            # COMBAT KNIFE - blade with handle
            blade_len = 25 - kick
            blade_end_x = gun_x + cos_a * blade_len
            blade_end_y = gun_y + sin_a * blade_len
            # Blade (silver/metallic)
            blade_color = (180, 180, 190)
            blade_edge = (140, 140, 150)
            # Main blade
            pygame.draw.line(screen, blade_color, (int(gun_x), int(gun_y)), (int(blade_end_x), int(blade_end_y)), 5)
            # Sharp edge highlight
            pygame.draw.line(screen, blade_edge,
                (int(gun_x + perp_x*2), int(gun_y + perp_y*2)),
                (int(blade_end_x), int(blade_end_y)), 2)
            # Handle/grip (brown)
            handle_x = gun_x - cos_a * 12
            handle_y = gun_y - sin_a * 12
            pygame.draw.line(screen, gun_brown, (int(gun_x - cos_a*2), int(gun_y - sin_a*2)), (int(handle_x), int(handle_y)), 7)
            # Guard (cross piece between blade and handle)
            guard_x = gun_x - cos_a * 2
            guard_y = gun_y - sin_a * 2
            pygame.draw.line(screen, gun_dark,
                (int(guard_x - perp_x*5), int(guard_y - perp_y*5)),
                (int(guard_x + perp_x*5), int(guard_y + perp_y*5)), 3)

        else:
            # DEFAULT - simple gun shape
            barrel_len = 25 - kick
            barrel_end_x = gun_x + cos_a * barrel_len
            barrel_end_y = gun_y + sin_a * barrel_len
            pygame.draw.line(screen, gun_black, (int(gun_x), int(gun_y)), (int(barrel_end_x), int(barrel_end_y)), 6)
            pygame.draw.line(screen, gun_brown, (int(gun_x), int(gun_y)), (int(gun_x + perp_x*8), int(gun_y + perp_y*8)), 5)

        # Muzzle flash effect (keep existing)
        gun_end_x = gun_x + cos_a * (30 - kick)
        gun_end_y = gun_y + sin_a * (30 - kick)
        if self.muzzle_flash_timer > 0:
            flash_size = int(15 + self.current_weapon.damage / 10)
            flash_x = int(gun_end_x + math.cos(self.angle) * 5)
            flash_y = int(gun_end_y + math.sin(self.angle) * 5)
            # Outer flash (orange)
            pygame.draw.circle(screen, ORANGE, (flash_x, flash_y), flash_size)
            # Inner flash (yellow/white)
            pygame.draw.circle(screen, YELLOW, (flash_x, flash_y), flash_size // 2)
            pygame.draw.circle(screen, WHITE, (flash_x, flash_y), flash_size // 4)

        # Health bar
        bar_width = 50
        bar_height = 6
        health_ratio = self.health / self.max_health
        pygame.draw.rect(screen, RED, (draw_x - bar_width//2, draw_y - self.size - 15, bar_width, bar_height))
        pygame.draw.rect(screen, GREEN, (draw_x - bar_width//2, draw_y - self.size - 15, bar_width * health_ratio, bar_height))

        # Reload animation
        if self.is_reloading:
            reload_progress = 1 - (self.reload_timer / self.current_weapon.reload_time)

            # Circular progress indicator
            pygame.draw.arc(screen, YELLOW, (draw_x - 20, draw_y - 20, 40, 40),
                          -math.pi/2, -math.pi/2 + reload_progress * math.pi * 2, 3)

            # Magazine animation - magazine drops and new one slides in
            mag_offset_y = 0
            if reload_progress < 0.3:
                # Magazine dropping out
                mag_offset_y = int((reload_progress / 0.3) * 20)
                mag_alpha = int(255 * (1 - reload_progress / 0.3))
            elif reload_progress < 0.7:
                # No magazine visible
                mag_offset_y = 20
                mag_alpha = 0
            else:
                # New magazine sliding in
                mag_offset_y = int(20 * (1 - (reload_progress - 0.7) / 0.3))
                mag_alpha = int(255 * ((reload_progress - 0.7) / 0.3))

            # Draw magazine
            if mag_alpha > 50:
                mag_x = draw_x + int(math.cos(self.angle + math.pi/2) * 8)
                mag_y = draw_y + int(math.sin(self.angle + math.pi/2) * 8) + mag_offset_y
                pygame.draw.rect(screen, (80, 80, 80), (mag_x - 4, mag_y - 6, 8, 12))

            # "RELOADING" text
            font = pygame.font.Font(None, 18)
            reload_text = font.render("RELOADING", True, YELLOW)
            screen.blit(reload_text, (draw_x - reload_text.get_width()//2, draw_y - self.size - 30))

        # Player ID
        font = pygame.font.Font(None, 20)
        id_text = font.render(f"P{self.player_id + 1}", True, WHITE)
        screen.blit(id_text, (draw_x - 10, draw_y + self.size + 5))


class Bunker:
    """Central bunker where players can switch classes and resupply."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 200
        self.height = 150
        self.health = 1000
        self.max_health = 1000

    def get_rect(self):
        return pygame.Rect(self.x - self.width//2, self.y - self.height//2, self.width, self.height)

    def is_player_inside(self, player):
        return self.get_rect().collidepoint(player.x, player.y)

    def take_damage(self, damage):
        self.health -= damage
        if self.health < 0:
            self.health = 0

    def draw(self, screen, camera_offset):
        rect = self.get_rect()
        draw_rect = rect.move(-camera_offset[0], -camera_offset[1])

        # Main structure
        pygame.draw.rect(screen, GRAY, draw_rect)
        pygame.draw.rect(screen, DARK_GRAY, draw_rect, 4)

        # Roof
        roof_points = [
            (draw_rect.centerx, draw_rect.top - 30),
            (draw_rect.left - 10, draw_rect.top),
            (draw_rect.right + 10, draw_rect.top)
        ]
        pygame.draw.polygon(screen, DARK_GRAY, roof_points)

        # Door
        door_rect = pygame.Rect(draw_rect.centerx - 20, draw_rect.bottom - 60, 40, 60)
        pygame.draw.rect(screen, BROWN, door_rect)

        # Windows
        pygame.draw.rect(screen, LIGHT_BLUE, (draw_rect.left + 20, draw_rect.top + 30, 30, 30))
        pygame.draw.rect(screen, LIGHT_BLUE, (draw_rect.right - 50, draw_rect.top + 30, 30, 30))

        # Health bar
        bar_width = self.width
        health_ratio = self.health / self.max_health
        pygame.draw.rect(screen, RED, (draw_rect.x, draw_rect.y - 20, bar_width, 10))
        pygame.draw.rect(screen, GREEN, (draw_rect.x, draw_rect.y - 20, bar_width * health_ratio, 10))

        # Label
        font = pygame.font.Font(None, 24)
        text = font.render("BUNKER - Press B to change class", True, WHITE)
        screen.blit(text, (draw_rect.centerx - text.get_width()//2, draw_rect.y - 40))


class GameWorld:
    """Main game world containing all entities."""
    def __init__(self, width=5000, height=5000):
        self.width = width
        self.height = height
        self.players = []
        self.zombies = []
        self.bullets = []
        self.walls = []
        self.heal_zones = []
        self.particles = []
        self.bunker = Bunker(width // 2, height // 2)

        # Wave system
        self.current_wave = 0
        self.zombies_to_spawn = 0
        self.spawn_timer = 0
        self.wave_active = False
        self.wave_cooldown = 5  # Time between waves

        # Zombie King boss system
        self.zombie_king = None
        self.zombie_king_stage = 1  # Starts at stage 1
        self.zombie_king_defeated_count = 0

        # Scores
        self.kills = 0
        self.score = 0

        # Desert environment - generate rocks and shrubs
        self.rocks = []
        self.shrubs = []
        self.generate_desert_environment()

    def generate_desert_environment(self):
        """Generate rocks and dead shrubs for desert background."""
        # Generate rocks (avoid center bunker area)
        bunker_safe_zone = 400  # Don't spawn rocks near bunker
        for _ in range(80):  # 80 rocks scattered around
            while True:
                x = random.randint(50, self.width - 50)
                y = random.randint(50, self.height - 50)
                # Check not too close to bunker
                dist_to_bunker = math.sqrt((x - self.width//2)**2 + (y - self.height//2)**2)
                if dist_to_bunker > bunker_safe_zone:
                    break
            size = random.randint(20, 60)
            color_var = random.randint(-20, 20)
            rock_color = (120 + color_var, 110 + color_var, 100 + color_var)
            self.rocks.append({
                'x': x, 'y': y, 'size': size, 'color': rock_color,
                'shape': random.choice(['circle', 'polygon'])
            })

        # Generate dead shrubs
        for _ in range(60):  # 60 shrubs
            while True:
                x = random.randint(50, self.width - 50)
                y = random.randint(50, self.height - 50)
                dist_to_bunker = math.sqrt((x - self.width//2)**2 + (y - self.height//2)**2)
                if dist_to_bunker > bunker_safe_zone:
                    break
            size = random.randint(15, 40)
            # Dead shrub colors - browns and dark greens
            shrub_color = random.choice([
                (100, 80, 50), (90, 70, 40), (80, 90, 50), (70, 60, 30)
            ])
            self.shrubs.append({
                'x': x, 'y': y, 'size': size, 'color': shrub_color,
                'branches': random.randint(3, 6)
            })

    def start_wave(self, wave_num):
        self.current_wave = wave_num
        self.zombies_to_spawn = 10 + wave_num * 5
        self.wave_active = True
        self.spawn_timer = 0

    def spawn_zombie(self):
        # Spawn at edge of map
        side = random.randint(0, 3)
        if side == 0:  # Top
            x = random.randint(0, self.width)
            y = 0
        elif side == 1:  # Right
            x = self.width
            y = random.randint(0, self.height)
        elif side == 2:  # Bottom
            x = random.randint(0, self.width)
            y = self.height
        else:  # Left
            x = 0
            y = random.randint(0, self.height)

        # Zombie type based on wave - more variety as waves progress
        zombie_types = ["normal"]
        weights = [5]

        if self.current_wave >= 2:
            zombie_types.append("runner")
            weights.append(3)

        if self.current_wave >= 3:
            zombie_types.append("crawler")
            weights.append(2)
            zombie_types.append("speed")  # Speed zombie
            weights.append(2)

        if self.current_wave >= 4:
            zombie_types.append("tank")
            weights.append(2)

        if self.current_wave >= 5:
            zombie_types.append("spitter")
            weights.append(2)

        if self.current_wave >= 6:
            zombie_types.append("bloater")
            weights.append(1)

        if self.current_wave >= 4:
            zombie_types.append("radioactive")
            weights.append(1)

        # Zombie King spawns every 7 waves (wave 7, 14, 21, etc.)
        if self.current_wave >= 7 and self.current_wave % 7 == 0:
            if not hasattr(self, 'king_spawned_this_wave'):
                self.king_spawned_this_wave = False

            if not self.king_spawned_this_wave and self.zombie_king is None:
                # Spawn Zombie King at current stage
                zombie_type = "zombie_king"
                self.king_spawned_this_wave = True
                zombie = Zombie(x, y, zombie_type, self.current_wave, king_stage=self.zombie_king_stage)
                self.zombie_king = zombie
                self.zombies.append(zombie)
                return
        else:
            self.king_spawned_this_wave = False

        # Cage Walker boss every 5 waves (wave 5, 10, 15, etc.)
        if self.current_wave >= 5 and self.current_wave % 5 == 0:
            if not hasattr(self, 'boss_spawned_this_wave'):
                self.boss_spawned_this_wave = False

            if not self.boss_spawned_this_wave:
                zombie_type = "cage_walker"
                self.boss_spawned_this_wave = True
            else:
                zombie_type = random.choices(zombie_types, weights)[0]
        else:
            self.boss_spawned_this_wave = False
            zombie_type = random.choices(zombie_types, weights)[0]

        zombie = Zombie(x, y, zombie_type, self.current_wave)
        self.zombies.append(zombie)

    def update(self, dt):
        # Update wave spawning
        if self.wave_active:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0 and self.zombies_to_spawn > 0:
                self.spawn_zombie()
                self.zombies_to_spawn -= 1
                self.spawn_timer = max(0.3, 2 - self.current_wave * 0.1)

            # Check wave complete
            if self.zombies_to_spawn <= 0 and len(self.zombies) == 0:
                self.wave_active = False
                self.wave_cooldown = 5
        else:
            self.wave_cooldown -= dt
            if self.wave_cooldown <= 0:
                self.start_wave(self.current_wave + 1)

        # Update zombies
        for zombie in self.zombies[:]:
            if not zombie.update(dt, self.players, self.walls, self.bunker, self.zombies):
                # Check if this was the Zombie King
                if zombie.zombie_type == "zombie_king":
                    self.zombie_king = None
                    self.zombie_king_defeated_count += 1

                    # If defeated at wave 70+, permanently dead
                    if self.current_wave >= 70:
                        pass  # King is dead forever
                    else:
                        # Increase stage for next spawn
                        self.zombie_king_stage += 1

                self.zombies.remove(zombie)

        # Update bullets
        for bullet in self.bullets[:]:
            if not bullet.update(dt):
                self.bullets.remove(bullet)
                continue

            # Track which zombies this bullet already hit (for penetration)
            if not hasattr(bullet, 'hit_zombies'):
                bullet.hit_zombies = set()

            # Check zombie collisions
            for zombie in self.zombies[:]:
                # Skip if already hit this zombie
                if id(zombie) in bullet.hit_zombies:
                    continue

                dist = math.sqrt((bullet.x - zombie.x)**2 + (bullet.y - zombie.y)**2)
                if dist < zombie.size + 5:
                    angle = math.atan2(bullet.vy, bullet.vx)

                    if bullet.explosive:
                        # Explosion damage - hits all nearby zombies
                        for z in self.zombies:
                            exp_dist = math.sqrt((bullet.x - z.x)**2 + (bullet.y - z.y)**2)
                            if exp_dist < bullet.explosion_radius:
                                exp_damage = bullet.damage * (1 - exp_dist / bullet.explosion_radius)
                                exp_angle = math.atan2(z.y - bullet.y, z.x - bullet.x)
                                if z.take_damage(exp_damage, exp_angle):
                                    self.kills += 1
                                    self.score += 100

                        # Explosion particles
                        for _ in range(20):
                            p_angle = random.uniform(0, math.pi * 2)
                            p_speed = random.uniform(100, 300)
                            self.particles.append(Particle(
                                bullet.x, bullet.y, random.choice([ORANGE, RED, YELLOW]),
                                (math.cos(p_angle) * p_speed, math.sin(p_angle) * p_speed),
                                random.uniform(0.3, 0.6), 8
                            ))

                        # Explosives always stop on impact
                        bullet.active = False
                        if bullet in self.bullets:
                            self.bullets.remove(bullet)
                        break
                    else:
                        # Regular bullet with penetration
                        if zombie.take_damage(bullet.damage, angle):
                            self.kills += 1
                            self.score += 100

                        # Blood particles
                        for _ in range(5):
                            p_angle = angle + random.uniform(-0.5, 0.5)
                            p_speed = random.uniform(50, 150)
                            self.particles.append(Particle(
                                bullet.x, bullet.y, DARK_RED,
                                (math.cos(p_angle) * p_speed, math.sin(p_angle) * p_speed),
                                random.uniform(0.2, 0.4), 4
                            ))

                        # Mark this zombie as hit
                        bullet.hit_zombies.add(id(zombie))

                        # Check if bullet can continue (penetration)
                        if not bullet.hit_target():
                            # Bullet exhausted penetration
                            bullet.active = False
                            if bullet in self.bullets:
                                self.bullets.remove(bullet)
                            break

            # Bullets pass through builder walls (removed wall collision)

        # Update walls
        for wall in self.walls[:]:
            if not wall.active:
                self.walls.remove(wall)

        # Update heal zones
        for zone in self.heal_zones[:]:
            if not zone.update(dt):
                self.heal_zones.remove(zone)
            else:
                # Heal players in zone
                for player in self.players:
                    dist = math.sqrt((player.x - zone.x)**2 + (player.y - zone.y)**2)
                    if dist < zone.radius:
                        player.heal(zone.heal_rate * dt)

        # Update particles
        for particle in self.particles[:]:
            if not particle.update(dt):
                self.particles.remove(particle)

        # Update players
        for player in self.players:
            player.update(dt, self)

    def draw(self, screen, camera_offset):
        # Desert background
        screen.fill(SAND)

        # Draw subtle grid lines (sand dune patterns)
        grid_size = 150
        start_x = int(camera_offset[0] // grid_size) * grid_size
        start_y = int(camera_offset[1] // grid_size) * grid_size
        for x in range(start_x, int(camera_offset[0] + SCREEN_WIDTH + grid_size), grid_size):
            pygame.draw.line(screen, DARK_SAND,
                           (x - camera_offset[0], 0), (x - camera_offset[0], SCREEN_HEIGHT), 1)
        for y in range(start_y, int(camera_offset[1] + SCREEN_HEIGHT + grid_size), grid_size):
            pygame.draw.line(screen, DARK_SAND,
                           (0, y - camera_offset[1]), (SCREEN_WIDTH, y - camera_offset[1]), 1)

        # Draw rocks
        for rock in self.rocks:
            rx = int(rock['x'] - camera_offset[0])
            ry = int(rock['y'] - camera_offset[1])
            # Only draw if on screen
            if -100 < rx < SCREEN_WIDTH + 100 and -100 < ry < SCREEN_HEIGHT + 100:
                if rock['shape'] == 'circle':
                    pygame.draw.circle(screen, rock['color'], (rx, ry), rock['size'])
                    pygame.draw.circle(screen, (rock['color'][0]-20, rock['color'][1]-20, rock['color'][2]-20), (rx, ry), rock['size'], 2)
                else:
                    # Polygon rock
                    points = []
                    for i in range(5):
                        angle = i * (math.pi * 2 / 5) + random.random() * 0.3
                        dist = rock['size'] * (0.7 + random.random() * 0.3)
                        points.append((rx + math.cos(angle) * dist, ry + math.sin(angle) * dist))
                    pygame.draw.polygon(screen, rock['color'], points)

        # Draw dead shrubs
        for shrub in self.shrubs:
            sx = int(shrub['x'] - camera_offset[0])
            sy = int(shrub['y'] - camera_offset[1])
            if -50 < sx < SCREEN_WIDTH + 50 and -50 < sy < SCREEN_HEIGHT + 50:
                # Draw branches
                for i in range(shrub['branches']):
                    angle = (i / shrub['branches']) * math.pi * 2 + random.random() * 0.5
                    length = shrub['size'] * (0.6 + random.random() * 0.4)
                    end_x = sx + math.cos(angle) * length
                    end_y = sy + math.sin(angle) * length
                    pygame.draw.line(screen, shrub['color'], (sx, sy), (int(end_x), int(end_y)), 2)
                    # Sub-branches
                    if random.random() > 0.5:
                        sub_angle = angle + random.uniform(-0.5, 0.5)
                        sub_length = length * 0.5
                        pygame.draw.line(screen, shrub['color'],
                                       (int(end_x), int(end_y)),
                                       (int(end_x + math.cos(sub_angle) * sub_length),
                                        int(end_y + math.sin(sub_angle) * sub_length)), 1)

        # World boundary
        pygame.draw.rect(screen, RED, (-camera_offset[0], -camera_offset[1], self.width, self.height), 5)

        # Draw heal zones
        for zone in self.heal_zones:
            zone.draw(screen, camera_offset)

        # Draw walls
        for wall in self.walls:
            wall.draw(screen, camera_offset)

        # Draw bunker
        self.bunker.draw(screen, camera_offset)

        # Draw zombies
        for zombie in self.zombies:
            zombie.draw(screen, camera_offset)

        # Draw players
        for player in self.players:
            player.draw(screen, camera_offset)

        # Draw bullets
        for bullet in self.bullets:
            bullet.draw(screen, camera_offset)

        # Draw particles
        for particle in self.particles:
            particle.draw(screen, camera_offset)


class NetworkManager:
    """Handles online multiplayer networking."""
    def __init__(self):
        self.socket = None
        self.is_host = False
        self.is_connected = False
        self.clients = []
        self.server_thread = None
        self.receive_thread = None
        self.player_data = {}
        if NETWORK_AVAILABLE:
            self.lock = threading.Lock()
        else:
            self.lock = None
        self.host_ip = ""
        self.port = 5555
        self.room_code = ""

    def host_game(self, port=5555):
        if not NETWORK_AVAILABLE:
            return False
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('', port))
            self.socket.listen(4)
            self.is_host = True
            self.is_connected = True
            self.port = port

            # Get host IP - try to get the actual LAN IP, not localhost
            try:
                # Create a dummy connection to get the actual IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                self.host_ip = s.getsockname()[0]
                s.close()
            except:
                # Fallback to hostname method
                hostname = socket.gethostname()
                self.host_ip = socket.gethostbyname(hostname)

            # Generate a simple room code from the IP
            ip_parts = self.host_ip.split('.')
            if len(ip_parts) == 4:
                # Create code from last two octets (e.g., 192.168.1.5 -> 1005)
                self.room_code = f"{int(ip_parts[2]):02d}{int(ip_parts[3]):02d}"
            else:
                self.room_code = "0000"

            # Start accept thread
            self.server_thread = threading.Thread(target=self._accept_connections, daemon=True)
            self.server_thread.start()

            return True
        except Exception as e:
            print(f"Failed to host: {e}")
            return False

    def join_game(self, host_ip, port=5555):
        if not NETWORK_AVAILABLE:
            return False
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host_ip, port))
            self.is_host = False
            self.is_connected = True

            # Start receive thread
            self.receive_thread = threading.Thread(target=self._receive_data, daemon=True)
            self.receive_thread.start()

            return True
        except Exception as e:
            print(f"Failed to join: {e}")
            return False

    def _accept_connections(self):
        while self.is_connected:
            try:
                self.socket.settimeout(1.0)
                client, addr = self.socket.accept()
                self.clients.append(client)
                print(f"Client connected: {addr}")

                # Start receive thread for this client
                thread = threading.Thread(target=self._handle_client, args=(client,), daemon=True)
                thread.start()
            except socket.timeout:
                continue
            except:
                break

    def _handle_client(self, client):
        while self.is_connected:
            try:
                data = client.recv(4096)
                if data:
                    with self.lock:
                        player_info = pickle.loads(data)
                        self.player_data[player_info['id']] = player_info
            except:
                break

    def _receive_data(self):
        while self.is_connected:
            try:
                data = self.socket.recv(4096)
                if data:
                    with self.lock:
                        game_state = pickle.loads(data)
                        self.player_data = game_state
            except:
                break

    def send_player_data(self, player):
        data = {
            'id': player.player_id,
            'x': player.x,
            'y': player.y,
            'angle': player.angle,
            'health': player.health,
            'player_class': player.player_class.value,
            'shooting': player.mouse_buttons[0]
        }

        try:
            if self.is_host:
                # Send to all clients
                for client in self.clients:
                    try:
                        client.send(pickle.dumps(self.player_data))
                    except:
                        pass
            else:
                # Send to server
                self.socket.send(pickle.dumps(data))
        except:
            pass

    def get_other_players(self):
        if self.lock:
            with self.lock:
                return dict(self.player_data)
        return dict(self.player_data)

    def close(self):
        self.is_connected = False
        if self.socket:
            self.socket.close()
        for client in self.clients:
            client.close()


class Game:
    """Main game class."""
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Zombie Survival: Class Defense")
        self.clock = pygame.time.Clock()
        self.running = True

        self.state = GameState.MENU
        self.world = None
        self.local_players = []
        self.camera_offset = [0, 0]

        # Multiplayer
        self.network = NetworkManager()
        self.is_multiplayer = False
        self.num_local_players = 1

        # UI
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 32)

        # Class selection
        self.selected_class = [PlayerClass.RANGER] * 4
        self.class_confirmed = [False] * 4
        self.changing_class_in_bunker = False  # Flag for in-game class change

        # Input for IP
        self.ip_input = ""
        self.ip_active = False

        # Touch controls
        self.touch_enabled = True  # Always enable for web
        self.move_joystick = VirtualJoystick(120, SCREEN_HEIGHT - 120, 80)
        self.aim_joystick = VirtualJoystick(SCREEN_WIDTH - 120, SCREEN_HEIGHT - 120, 80)
        self.shoot_button = TouchButton(SCREEN_WIDTH - 120, SCREEN_HEIGHT - 250, 50, "FIRE", RED)
        self.ability_button = TouchButton(SCREEN_WIDTH - 220, SCREEN_HEIGHT - 120, 40, "Z", BLUE)
        self.weapon_prev_button = TouchButton(SCREEN_WIDTH - 300, SCREEN_HEIGHT - 200, 35, "Q", ORANGE)
        self.weapon_next_button = TouchButton(SCREEN_WIDTH - 220, SCREEN_HEIGHT - 200, 35, "E", ORANGE)
        self.reload_button = TouchButton(120, SCREEN_HEIGHT - 220, 35, "R", YELLOW)

    def reset_game(self):
        self.world = GameWorld()
        self.local_players = []
        self.class_confirmed = [False] * 4

        for i in range(self.num_local_players):
            player = Player(
                self.world.width // 2 + (i - self.num_local_players // 2) * 50,
                self.world.height // 2 + 100,
                i,
                self.selected_class[i]
            )
            # Player 2 uses 8/9 to aim, Player 3 uses 6/7 to aim
            self.local_players.append(player)
            self.world.players.append(player)

    def handle_menu_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.num_local_players = 1
                self.state = GameState.CLASS_SELECT
            elif event.key == pygame.K_2:
                self.num_local_players = 2
                self.state = GameState.CLASS_SELECT
            elif event.key == pygame.K_3:
                self.num_local_players = 3
                self.state = GameState.CLASS_SELECT
            elif event.key == pygame.K_h:
                self.state = GameState.HOST_GAME
            elif event.key == pygame.K_j:
                self.state = GameState.JOIN_GAME
                self.ip_input = ""
            elif event.key == pygame.K_ESCAPE:
                self.running = False

        # Touch/click support for menu
        elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
            if event.type == pygame.FINGERDOWN:
                x = event.x * SCREEN_WIDTH
                y = event.y * SCREEN_HEIGHT
            else:
                x, y = event.pos

            # Check menu option clicks (based on draw_menu positions)
            if 300 <= y <= 345:
                self.num_local_players = 1
                self.state = GameState.CLASS_SELECT
            elif 345 <= y <= 390:
                self.num_local_players = 2
                self.state = GameState.CLASS_SELECT
            elif 390 <= y <= 435:
                self.num_local_players = 3
                self.state = GameState.CLASS_SELECT

    def handle_class_select_events(self, event):
        if event.type == pygame.KEYDOWN:
            # Player 1 controls (WASD + Space)
            if event.key == pygame.K_a:
                idx = self.selected_class[0].value - 1
                idx = (idx - 1) % 4 + 1
                self.selected_class[0] = PlayerClass(idx)
            elif event.key == pygame.K_d:
                idx = self.selected_class[0].value - 1
                idx = (idx + 1) % 4 + 1
                self.selected_class[0] = PlayerClass(idx)
            elif event.key == pygame.K_SPACE:
                self.class_confirmed[0] = True

            # Player 2 controls (J/L + Enter) - if 2+ players
            if self.num_local_players >= 2 and event.key == pygame.K_j:
                idx = self.selected_class[1].value - 1
                idx = (idx - 1) % 4 + 1
                self.selected_class[1] = PlayerClass(idx)
            if self.num_local_players >= 2 and event.key == pygame.K_l:
                idx = self.selected_class[1].value - 1
                idx = (idx + 1) % 4 + 1
                self.selected_class[1] = PlayerClass(idx)
            if self.num_local_players >= 2 and event.key == pygame.K_RETURN:
                self.class_confirmed[1] = True

            # Player 3 controls (F/H + Tab) - if 3 players
            if self.num_local_players >= 3 and event.key == pygame.K_f:
                idx = self.selected_class[2].value - 1
                idx = (idx - 1) % 4 + 1
                self.selected_class[2] = PlayerClass(idx)
            if self.num_local_players >= 3 and event.key == pygame.K_h:
                idx = self.selected_class[2].value - 1
                idx = (idx + 1) % 4 + 1
                self.selected_class[2] = PlayerClass(idx)
            if self.num_local_players >= 3 and event.key == pygame.K_TAB:
                self.class_confirmed[2] = True

            # Check if all players confirmed
            if all(self.class_confirmed[:self.num_local_players]):
                if self.changing_class_in_bunker:
                    # Just update player classes without resetting
                    for i, player in enumerate(self.local_players):
                        old_health_percent = player.health / player.max_health
                        player.setup_class(self.selected_class[i])
                        # Keep health percentage and start with full ammo for new class
                        player.health = int(old_health_percent * player.max_health)
                        player.current_weapon_index = 0
                        player.current_ammo = player.weapons[0].mag_size
                        player.reserve_ammo = player.weapons[0].max_ammo
                    self.changing_class_in_bunker = False
                else:
                    self.reset_game()
                self.state = GameState.PLAYING

            if event.key == pygame.K_ESCAPE:
                if self.changing_class_in_bunker:
                    self.changing_class_in_bunker = False
                    self.state = GameState.PLAYING
                else:
                    self.state = GameState.MENU

        # Touch/click support for class selection
        elif event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.FINGERDOWN:
            if event.type == pygame.FINGERDOWN:
                x = event.x * SCREEN_WIDTH
                y = event.y * SCREEN_HEIGHT
            else:
                x, y = event.pos

            # Class boxes are at y=180 with height=250, width=300 each
            box_width = 300
            start_x = (SCREEN_WIDTH - box_width * 4 - 60) // 2

            if 180 <= y <= 430:
                for i in range(4):
                    box_x = start_x + i * (box_width + 20)
                    if box_x <= x <= box_x + box_width:
                        self.selected_class[0] = PlayerClass(i + 1)
                        self.class_confirmed[0] = True
                        break

            # Check if all players confirmed
            if all(self.class_confirmed[:self.num_local_players]):
                self.reset_game()
                self.state = GameState.PLAYING

    def handle_host_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.network.host_game():
                    self.is_multiplayer = True
                    self.num_local_players = 1
                    self.state = GameState.CLASS_SELECT
            elif event.key == pygame.K_ESCAPE:
                self.state = GameState.MENU

    def handle_join_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if self.network.join_game(self.ip_input):
                    self.is_multiplayer = True
                    self.num_local_players = 1
                    self.state = GameState.CLASS_SELECT
            elif event.key == pygame.K_BACKSPACE:
                self.ip_input = self.ip_input[:-1]
            elif event.key == pygame.K_ESCAPE:
                self.state = GameState.MENU
            else:
                if event.unicode in '0123456789.':
                    self.ip_input += event.unicode

    def handle_playing_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = GameState.PAUSED

            # Toggle touch controls with TAB
            if event.key == pygame.K_TAB:
                self.touch_enabled = not self.touch_enabled

            # Player 1 controls (WASD movement, Q/E weapons, Z ability)
            if len(self.local_players) > 0:
                player = self.local_players[0]
                player.keys_pressed.add(event.key)

                if event.key == pygame.K_q:
                    player.switch_weapon(-1)  # Previous weapon
                elif event.key == pygame.K_e:
                    player.switch_weapon(1)   # Next weapon
                elif event.key == pygame.K_z:
                    # Z key: Place wall (Builder) or use ability (other classes)
                    player.use_ability(self.world)
                    # Hide preview after placing for Builder
                    if player.player_class == PlayerClass.BUILDER:
                        player.show_block_preview = False
                elif event.key == pygame.K_c:
                    # C key: Toggle blueprint preview and rotate (Builder only)
                    if player.player_class == PlayerClass.BUILDER:
                        if player.show_block_preview:
                            # If preview is showing, rotate it
                            player.rotate_block()
                        else:
                            # If preview is hidden, show it
                            player.show_block_preview = True
                elif event.key == pygame.K_b:
                    # Class switch in bunker
                    if self.world.bunker.is_player_inside(player):
                        self.changing_class_in_bunker = True
                        # Set current classes as selected
                        for i, p in enumerate(self.local_players):
                            self.selected_class[i] = p.player_class
                        self.state = GameState.CLASS_SELECT
                        self.class_confirmed = [False] * 4

            # Player 2 controls (IJKL movement, U/O weapons, M ability, 8/9 aim, Space shoot)
            if len(self.local_players) > 1:
                player2 = self.local_players[1]
                if event.key in [pygame.K_i, pygame.K_j, pygame.K_k, pygame.K_l, pygame.K_8, pygame.K_9]:
                    player2.keys_pressed.add(event.key)
                elif event.key == pygame.K_u:
                    player2.switch_weapon(-1)  # Previous weapon
                elif event.key == pygame.K_o:
                    player2.switch_weapon(1)   # Next weapon
                elif event.key == pygame.K_m:
                    player2.use_ability(self.world)
                elif event.key == pygame.K_SPACE:
                    # Spacebar to shoot for Player 2
                    player2.mouse_buttons[0] = True

            # Player 3 controls (TFGH movement, R/Y weapons, V ability, 6/7 aim, B shoot)
            if len(self.local_players) > 2:
                player3 = self.local_players[2]
                if event.key in [pygame.K_t, pygame.K_f, pygame.K_g, pygame.K_h, pygame.K_6, pygame.K_7]:
                    player3.keys_pressed.add(event.key)
                elif event.key == pygame.K_r:
                    player3.switch_weapon(-1)  # Previous weapon
                elif event.key == pygame.K_y:
                    player3.switch_weapon(1)   # Next weapon
                elif event.key == pygame.K_v:
                    player3.use_ability(self.world)
                elif event.key == pygame.K_b:
                    # B to shoot for Player 3
                    player3.mouse_buttons[0] = True

        elif event.type == pygame.KEYUP:
            if len(self.local_players) > 0:
                player = self.local_players[0]
                player.keys_pressed.discard(event.key)

            # Player 2 key up
            if len(self.local_players) > 1:
                player2 = self.local_players[1]
                player2.keys_pressed.discard(event.key)
                # Stop shooting when spacebar released
                if event.key == pygame.K_SPACE:
                    player2.mouse_buttons[0] = False

            # Player 3 key up
            if len(self.local_players) > 2:
                player3 = self.local_players[2]
                player3.keys_pressed.discard(event.key)
                # Stop shooting when B released
                if event.key == pygame.K_b:
                    player3.mouse_buttons[0] = False

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if len(self.local_players) > 0:
                player = self.local_players[0]
                if event.button <= 3:
                    player.mouse_buttons[event.button - 1] = True

        elif event.type == pygame.MOUSEBUTTONUP:
            if len(self.local_players) > 0:
                player = self.local_players[0]
                if event.button <= 3:
                    player.mouse_buttons[event.button - 1] = False

        elif event.type == pygame.MOUSEWHEEL:
            if len(self.local_players) > 0:
                player = self.local_players[0]
                player.switch_weapon(event.y)

        # Touch events (FINGERDOWN, FINGERUP, FINGERMOTION)
        elif event.type == pygame.FINGERDOWN:
            x = event.x * SCREEN_WIDTH
            y = event.y * SCREEN_HEIGHT
            touch_id = event.finger_id

            # Check joysticks and buttons
            self.move_joystick.handle_touch_down(touch_id, x, y)
            self.aim_joystick.handle_touch_down(touch_id, x, y)
            self.shoot_button.handle_touch_down(touch_id, x, y)
            self.ability_button.handle_touch_down(touch_id, x, y)
            self.weapon_prev_button.handle_touch_down(touch_id, x, y)
            self.weapon_next_button.handle_touch_down(touch_id, x, y)
            self.reload_button.handle_touch_down(touch_id, x, y)

            # Handle button actions on press
            if len(self.local_players) > 0:
                player = self.local_players[0]
                if self.ability_button.pressed:
                    player.use_ability(self.world)
                if self.weapon_prev_button.pressed:
                    player.switch_weapon(-1)
                if self.weapon_next_button.pressed:
                    player.switch_weapon(1)
                if self.reload_button.pressed:
                    player.start_reload()

        elif event.type == pygame.FINGERUP:
            touch_id = event.finger_id
            self.move_joystick.handle_touch_up(touch_id)
            self.aim_joystick.handle_touch_up(touch_id)
            self.shoot_button.handle_touch_up(touch_id)
            self.ability_button.handle_touch_up(touch_id)
            self.weapon_prev_button.handle_touch_up(touch_id)
            self.weapon_next_button.handle_touch_up(touch_id)
            self.reload_button.handle_touch_up(touch_id)

        elif event.type == pygame.FINGERMOTION:
            x = event.x * SCREEN_WIDTH
            y = event.y * SCREEN_HEIGHT
            touch_id = event.finger_id
            self.move_joystick.handle_touch_move(touch_id, x, y)
            self.aim_joystick.handle_touch_move(touch_id, x, y)

    def handle_paused_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = GameState.PLAYING
            elif event.key == pygame.K_q:
                self.state = GameState.MENU

    def handle_game_over_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.state = GameState.CLASS_SELECT
                self.class_confirmed = [False] * 3
            elif event.key == pygame.K_ESCAPE:
                self.state = GameState.MENU

    def update(self, dt):
        if self.state == GameState.PLAYING:
            # Update mouse position for all local players
            mouse_pos = pygame.mouse.get_pos()
            for player in self.local_players:
                player.mouse_pos = mouse_pos

            # Handle touch controls for player 1
            if self.touch_enabled and len(self.local_players) > 0:
                player = self.local_players[0]

                # Movement from left joystick
                if self.move_joystick.active:
                    dx, dy = self.move_joystick.get_direction()
                    player.x += dx * player.speed * dt
                    player.y += dy * player.speed * dt
                    # Keep in bounds
                    player.x = max(player.size, min(self.world.width - player.size, player.x))
                    player.y = max(player.size, min(self.world.height - player.size, player.y))

                # Aiming from right joystick
                if self.aim_joystick.active:
                    dx, dy = self.aim_joystick.get_direction()
                    if abs(dx) > 0.1 or abs(dy) > 0.1:
                        player.angle = math.atan2(dy, dx)

                # Shooting from shoot button
                if self.shoot_button.pressed:
                    player.mouse_buttons[0] = True
                else:
                    # Only disable if no mouse click either
                    if not pygame.mouse.get_pressed()[0]:
                        player.mouse_buttons[0] = False

            # Update world
            self.world.update(dt)

            # Update camera to follow first alive player
            if self.local_players:
                # Find first alive player to follow
                camera_target = None
                for player in self.local_players:
                    if player.health > 0:
                        camera_target = player
                        break

                # If all dead, follow first player's body
                if camera_target is None:
                    camera_target = self.local_players[0]

                target_x = camera_target.x - SCREEN_WIDTH // 2
                target_y = camera_target.y - SCREEN_HEIGHT // 2
                self.camera_offset[0] += (target_x - self.camera_offset[0]) * 5 * dt
                self.camera_offset[1] += (target_y - self.camera_offset[1]) * 5 * dt

                # Apply screen shake from player recoil
                if camera_target.screen_shake > 0:
                    shake_x = random.uniform(-camera_target.screen_shake, camera_target.screen_shake)
                    shake_y = random.uniform(-camera_target.screen_shake, camera_target.screen_shake)
                    self.camera_offset[0] += shake_x
                    self.camera_offset[1] += shake_y

                # Clamp camera
                self.camera_offset[0] = max(0, min(self.world.width - SCREEN_WIDTH, self.camera_offset[0]))
                self.camera_offset[1] = max(0, min(self.world.height - SCREEN_HEIGHT, self.camera_offset[1]))

            # Check game over - all players dead OR bunker destroyed
            all_dead = all(p.health <= 0 for p in self.local_players)
            bunker_destroyed = self.world.bunker.health <= 0
            if all_dead or bunker_destroyed:
                self.state = GameState.GAME_OVER

            # Network update
            if self.is_multiplayer and self.local_players:
                self.network.send_player_data(self.local_players[0])

    def draw_menu(self):
        self.screen.fill(BLACK)

        # Title
        title = self.font_large.render("ZOMBIE SURVIVAL", True, RED)
        subtitle = self.font_medium.render("Class Defense", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        self.screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 180))

        # Menu options
        options = [
            ("Press 1 - Single Player", WHITE),
            ("Press 2 - 2 Player Local", WHITE),
            ("Press 3 - 3 Player Local", WHITE),
            ("", WHITE),
            ("Press H - Host Online Game" + ("" if NETWORK_AVAILABLE else " (Desktop only)"),
             WHITE if NETWORK_AVAILABLE else GRAY),
            ("Press J - Join Online Game" + ("" if NETWORK_AVAILABLE else " (Desktop only)"),
             WHITE if NETWORK_AVAILABLE else GRAY),
            ("", WHITE),
            ("Press ESC - Quit", WHITE)
        ]

        y = 300
        for option, color in options:
            if option:
                text = self.font_small.render(option, True, color)
                self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, y))
            y += 45

        # Instructions
        instructions = [
            "Controls (P1): WASD - Move | Mouse - Aim | LMB - Shoot",
            "Q/E - Switch Weapons | Z - Ability | B - Change Class (in bunker)",
            "Controls (P2): IJKL - Move | U/O - Weapons | M - Ability",
            "Controls (P3): TFGH - Move | R/Y - Weapons | V - Ability"
        ]
        y = SCREEN_HEIGHT - 150
        for inst in instructions:
            text = self.font_small.render(inst, True, GRAY)
            self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, y))
            y += 30

    def draw_class_select(self):
        self.screen.fill(DARK_GRAY)

        title = self.font_large.render("SELECT YOUR CLASS", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 50))

        classes = [
            (PlayerClass.BUILDER, "BUILDER", ORANGE,
             ["HP: 120 | Speed: Medium",
              "Ability: Build Walls",
              "Weapons: Nail Gun, Pistol",
              "Defensive specialist"]),
            (PlayerClass.RANGER, "RANGER", GREEN,
             ["HP: 100 | Speed: Fast",
              "Ability: Rapid Fire",
              "Weapons: Rifle, Pistol, Shotgun, Sniper",
              "Ranged combat expert"]),
            (PlayerClass.HEALER, "HEALER", LIGHT_BLUE,
             ["HP: 90 | Speed: Medium",
              "Ability: Heal Zone",
              "Weapons: Tranq Pistol, SMG",
              "Team support"]),
            (PlayerClass.TANK, "TANK", RED,
             ["HP: 180 | Speed: Slow",
              "Ability: Ground Slam",
              "Weapons: Minigun, RPG, Grenade Launcher",
              "Heavy firepower"])
        ]

        box_width = 300
        box_height = 250
        start_x = (SCREEN_WIDTH - box_width * 4 - 60) // 2

        for i, (pc, name, color, desc) in enumerate(classes):
            x = start_x + i * (box_width + 20)
            y = 180

            # Box
            rect = pygame.Rect(x, y, box_width, box_height)
            pygame.draw.rect(self.screen, color, rect, 3)

            # Highlight if selected
            for p_idx in range(self.num_local_players):
                if self.selected_class[p_idx] == pc:
                    if self.class_confirmed[p_idx]:
                        pygame.draw.rect(self.screen, color, rect)
                        text_color = BLACK
                    else:
                        pygame.draw.rect(self.screen, (*color[:3], 100), rect)
                        text_color = WHITE

                    # Player indicator
                    p_text = self.font_small.render(f"P{p_idx + 1}", True, WHITE if self.class_confirmed[p_idx] else color)
                    self.screen.blit(p_text, (x + box_width//2 - p_text.get_width()//2, y + box_height + 10))
                    break
            else:
                text_color = WHITE

            # Class name
            name_text = self.font_medium.render(name, True, text_color)
            self.screen.blit(name_text, (x + box_width//2 - name_text.get_width()//2, y + 20))

            # Description
            dy = 80
            for line in desc:
                desc_text = self.font_small.render(line, True, text_color)
                self.screen.blit(desc_text, (x + 10, y + dy))
                dy += 35

        # Instructions
        inst_y = SCREEN_HEIGHT - 140
        if self.num_local_players >= 1:
            inst1 = self.font_small.render("P1: A/D to select, SPACE to confirm", True, WHITE)
            self.screen.blit(inst1, (SCREEN_WIDTH//2 - inst1.get_width()//2, inst_y))
        if self.num_local_players >= 2:
            inst2 = self.font_small.render("P2: J/L to select, ENTER to confirm", True, WHITE)
            self.screen.blit(inst2, (SCREEN_WIDTH//2 - inst2.get_width()//2, inst_y + 30))
        if self.num_local_players >= 3:
            inst3 = self.font_small.render("P3: F/H to select, TAB to confirm", True, WHITE)
            self.screen.blit(inst3, (SCREEN_WIDTH//2 - inst3.get_width()//2, inst_y + 60))

    def draw_host_screen(self):
        self.screen.fill(BLACK)

        title = self.font_large.render("HOST GAME", True, GREEN)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 150))

        # Check if networking is available (not in web browser)
        if not NETWORK_AVAILABLE:
            # Web version - networking not supported
            error_text = self.font_medium.render("Online multiplayer not available", True, RED)
            self.screen.blit(error_text, (SCREEN_WIDTH//2 - error_text.get_width()//2, 300))

            reason_text = self.font_small.render("Web browsers cannot host game servers", True, YELLOW)
            self.screen.blit(reason_text, (SCREEN_WIDTH//2 - reason_text.get_width()//2, 360))

            tip_text = self.font_small.render("Use local co-op (2-3 players) instead!", True, WHITE)
            self.screen.blit(tip_text, (SCREEN_WIDTH//2 - tip_text.get_width()//2, 420))

            tip2_text = self.font_small.render("Or download the desktop version for online play", True, GRAY)
            self.screen.blit(tip2_text, (SCREEN_WIDTH//2 - tip2_text.get_width()//2, 460))
        elif self.network.is_host:
            # Room code (big and prominent)
            code_label = self.font_medium.render("ROOM CODE:", True, YELLOW)
            self.screen.blit(code_label, (SCREEN_WIDTH//2 - code_label.get_width()//2, 250))

            code_text = self.font_large.render(self.network.room_code, True, GREEN)
            self.screen.blit(code_text, (SCREEN_WIDTH//2 - code_text.get_width()//2, 300))

            # IP and Port (smaller, below)
            ip_text = self.font_small.render(f"IP: {self.network.host_ip}", True, GRAY)
            port_text = self.font_small.render(f"Port: {self.network.port}", True, GRAY)

            self.screen.blit(ip_text, (SCREEN_WIDTH//2 - ip_text.get_width()//2, 400))
            self.screen.blit(port_text, (SCREEN_WIDTH//2 - port_text.get_width()//2, 430))

            # Waiting message
            waiting = self.font_medium.render(f"Waiting for players... ({len(self.network.clients)} connected)", True, YELLOW)
            self.screen.blit(waiting, (SCREEN_WIDTH//2 - waiting.get_width()//2, 500))

            # Share instructions
            share_text = self.font_small.render("Share the ROOM CODE with friends to join!", True, WHITE)
            self.screen.blit(share_text, (SCREEN_WIDTH//2 - share_text.get_width()//2, 550))
        else:
            inst = self.font_medium.render("Press ENTER to start hosting", True, WHITE)
            self.screen.blit(inst, (SCREEN_WIDTH//2 - inst.get_width()//2, 400))

        back = self.font_small.render("Press ESC to go back", True, GRAY)
        self.screen.blit(back, (SCREEN_WIDTH//2 - back.get_width()//2, SCREEN_HEIGHT - 100))

    def draw_join_screen(self):
        self.screen.fill(BLACK)

        title = self.font_large.render("JOIN GAME", True, BLUE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 200))

        # Check if networking is available (not in web browser)
        if not NETWORK_AVAILABLE:
            # Web version - networking not supported
            error_text = self.font_medium.render("Online multiplayer not available", True, RED)
            self.screen.blit(error_text, (SCREEN_WIDTH//2 - error_text.get_width()//2, 300))

            reason_text = self.font_small.render("Web browsers cannot connect to game servers", True, YELLOW)
            self.screen.blit(reason_text, (SCREEN_WIDTH//2 - reason_text.get_width()//2, 360))

            tip_text = self.font_small.render("Use local co-op (2-3 players) instead!", True, WHITE)
            self.screen.blit(tip_text, (SCREEN_WIDTH//2 - tip_text.get_width()//2, 420))

            tip2_text = self.font_small.render("Or download the desktop version for online play", True, GRAY)
            self.screen.blit(tip2_text, (SCREEN_WIDTH//2 - tip2_text.get_width()//2, 460))
        else:
            inst = self.font_medium.render("Enter Host IP Address:", True, WHITE)
            self.screen.blit(inst, (SCREEN_WIDTH//2 - inst.get_width()//2, 350))

            # IP input box
            box_rect = pygame.Rect(SCREEN_WIDTH//2 - 150, 420, 300, 50)
            pygame.draw.rect(self.screen, WHITE, box_rect, 2)

            ip_display = self.font_medium.render(self.ip_input + "_", True, WHITE)
            self.screen.blit(ip_display, (box_rect.x + 10, box_rect.y + 10))

            enter_inst = self.font_small.render("Press ENTER to connect", True, YELLOW)
            self.screen.blit(enter_inst, (SCREEN_WIDTH//2 - enter_inst.get_width()//2, 500))

        back = self.font_small.render("Press ESC to go back", True, GRAY)
        self.screen.blit(back, (SCREEN_WIDTH//2 - back.get_width()//2, SCREEN_HEIGHT - 100))

    def draw_hud(self):
        if not self.local_players:
            return

        player = self.local_players[0]

        # Health bar
        pygame.draw.rect(self.screen, DARK_GRAY, (20, 20, 250, 30))
        pygame.draw.rect(self.screen, RED, (22, 22, 246, 26))
        health_width = (player.health / player.max_health) * 246
        pygame.draw.rect(self.screen, GREEN, (22, 22, health_width, 26))
        health_text = self.font_small.render(f"HP: {int(player.health)}/{player.max_health}", True, WHITE)
        self.screen.blit(health_text, (25, 55))

        # Ammo
        weapon = player.current_weapon
        ammo_text = self.font_medium.render(f"{weapon.name}", True, WHITE)
        ammo_count = self.font_medium.render(f"{player.current_ammo} / {player.reserve_ammo}", True, YELLOW if player.current_ammo > 0 else RED)
        self.screen.blit(ammo_text, (20, 90))
        self.screen.blit(ammo_count, (20, 130))

        if player.is_reloading:
            reload_text = self.font_small.render("RELOADING...", True, ORANGE)
            self.screen.blit(reload_text, (20, 170))

        # Ability cooldown
        ability_text = self.font_small.render(f"Ability (Z): ", True, WHITE)
        self.screen.blit(ability_text, (20, 200))
        if player.ability_cooldown > 0:
            cd_text = self.font_small.render(f"{player.ability_cooldown:.1f}s", True, RED)
        else:
            cd_text = self.font_small.render("READY", True, GREEN)
        self.screen.blit(cd_text, (140, 200))

        # Wave info
        wave_text = self.font_medium.render(f"Wave: {self.world.current_wave}", True, WHITE)
        self.screen.blit(wave_text, (SCREEN_WIDTH - 200, 20))

        zombies_text = self.font_small.render(f"Zombies: {len(self.world.zombies)}", True, RED)
        self.screen.blit(zombies_text, (SCREEN_WIDTH - 200, 60))

        score_text = self.font_small.render(f"Score: {self.world.score}", True, YELLOW)
        self.screen.blit(score_text, (SCREEN_WIDTH - 200, 90))

        kills_text = self.font_small.render(f"Kills: {self.world.kills}", True, WHITE)
        self.screen.blit(kills_text, (SCREEN_WIDTH - 200, 120))

        # Wave countdown
        if not self.world.wave_active:
            countdown = self.font_large.render(f"Next wave in: {self.world.wave_cooldown:.1f}", True, YELLOW)
            self.screen.blit(countdown, (SCREEN_WIDTH//2 - countdown.get_width()//2, 100))

        # Weapon slots
        slot_y = SCREEN_HEIGHT - 80
        for i, weap in enumerate(player.weapons):
            box_color = YELLOW if i == player.current_weapon_index else GRAY
            pygame.draw.rect(self.screen, box_color, (20 + i * 70, slot_y, 60, 60), 2)
            slot_text = self.font_small.render(str(i + 1), True, box_color)
            self.screen.blit(slot_text, (25 + i * 70, slot_y + 5))

            # Weapon name (abbreviated)
            name_abbr = weap.name[:6]
            name_text = pygame.font.Font(None, 18).render(name_abbr, True, WHITE)
            self.screen.blit(name_text, (25 + i * 70, slot_y + 35))

        # Class indicator
        class_names = {
            PlayerClass.BUILDER: "BUILDER",
            PlayerClass.RANGER: "RANGER",
            PlayerClass.HEALER: "HEALER",
            PlayerClass.TANK: "TANK"
        }
        class_text = self.font_medium.render(class_names[player.player_class], True, player.color)
        self.screen.blit(class_text, (SCREEN_WIDTH//2 - class_text.get_width()//2, SCREEN_HEIGHT - 50))

        # Bunker hint
        if self.world.bunker.is_player_inside(player):
            hint = self.font_small.render("Press B to change class", True, YELLOW)
            self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, SCREEN_HEIGHT - 80))

        # Crosshair
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.circle(self.screen, WHITE, mouse_pos, 10, 1)
        pygame.draw.line(self.screen, WHITE, (mouse_pos[0] - 15, mouse_pos[1]), (mouse_pos[0] - 5, mouse_pos[1]), 2)
        pygame.draw.line(self.screen, WHITE, (mouse_pos[0] + 5, mouse_pos[1]), (mouse_pos[0] + 15, mouse_pos[1]), 2)
        pygame.draw.line(self.screen, WHITE, (mouse_pos[0], mouse_pos[1] - 15), (mouse_pos[0], mouse_pos[1] - 5), 2)
        pygame.draw.line(self.screen, WHITE, (mouse_pos[0], mouse_pos[1] + 5), (mouse_pos[0], mouse_pos[1] + 15), 2)

        # Draw minimap (bottom-right corner)
        minimap_size = 150
        minimap_x = SCREEN_WIDTH - minimap_size - 20
        minimap_y = SCREEN_HEIGHT - minimap_size - 100
        scale = minimap_size / self.world.width

        # Minimap background
        minimap_bg = pygame.Surface((minimap_size, minimap_size))
        minimap_bg.fill((30, 30, 30))
        minimap_bg.set_alpha(180)
        self.screen.blit(minimap_bg, (minimap_x, minimap_y))

        # Minimap border
        pygame.draw.rect(self.screen, WHITE, (minimap_x, minimap_y, minimap_size, minimap_size), 2)

        # Draw bunker on minimap
        bunker_mx = int(minimap_x + self.world.bunker.x * scale)
        bunker_my = int(minimap_y + self.world.bunker.y * scale)
        bunker_mw = int(self.world.bunker.width * scale)
        bunker_mh = int(self.world.bunker.height * scale)
        pygame.draw.rect(self.screen, (100, 100, 100), (bunker_mx - bunker_mw//2, bunker_my - bunker_mh//2, bunker_mw, bunker_mh))

        # Draw zombies on minimap (red dots)
        for zombie in self.world.zombies:
            zx = int(minimap_x + zombie.x * scale)
            zy = int(minimap_y + zombie.y * scale)
            # Make sure dot is within minimap bounds
            if minimap_x <= zx <= minimap_x + minimap_size and minimap_y <= zy <= minimap_y + minimap_size:
                # Different colors for different zombie types
                if zombie.zombie_type == "zombie_king":
                    pygame.draw.circle(self.screen, PURPLE, (zx, zy), 4)
                elif zombie.zombie_type == "cage_walker":
                    pygame.draw.circle(self.screen, ORANGE, (zx, zy), 3)
                elif zombie.zombie_type == "tank":
                    pygame.draw.circle(self.screen, (150, 50, 50), (zx, zy), 2)
                else:
                    pygame.draw.circle(self.screen, RED, (zx, zy), 1)

        # Draw players on minimap (colored dots)
        for p in self.world.players:
            px = int(minimap_x + p.x * scale)
            py = int(minimap_y + p.y * scale)
            pygame.draw.circle(self.screen, p.color, (px, py), 4)
            pygame.draw.circle(self.screen, WHITE, (px, py), 4, 1)

        # Draw camera view rectangle
        cam_x = int(minimap_x + self.camera_offset[0] * scale)
        cam_y = int(minimap_y + self.camera_offset[1] * scale)
        cam_w = int(SCREEN_WIDTH * scale)
        cam_h = int(SCREEN_HEIGHT * scale)
        pygame.draw.rect(self.screen, (255, 255, 255, 100), (cam_x, cam_y, cam_w, cam_h), 1)

        # Minimap label
        map_label = pygame.font.Font(None, 18).render("MAP", True, WHITE)
        self.screen.blit(map_label, (minimap_x + minimap_size//2 - map_label.get_width()//2, minimap_y - 15))

        # Draw touch controls
        if self.touch_enabled:
            self.move_joystick.draw(self.screen)
            self.aim_joystick.draw(self.screen)
            self.shoot_button.draw(self.screen, self.font_small)
            self.ability_button.draw(self.screen, self.font_small)
            self.weapon_prev_button.draw(self.screen, self.font_small)
            self.weapon_next_button.draw(self.screen, self.font_small)
            self.reload_button.draw(self.screen, self.font_small)

    def draw_paused(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(150)
        self.screen.blit(overlay, (0, 0))

        paused = self.font_large.render("PAUSED", True, WHITE)
        self.screen.blit(paused, (SCREEN_WIDTH//2 - paused.get_width()//2, SCREEN_HEIGHT//2 - 100))

        resume = self.font_medium.render("Press ESC to resume", True, WHITE)
        quit_text = self.font_medium.render("Press Q to quit to menu", True, WHITE)
        self.screen.blit(resume, (SCREEN_WIDTH//2 - resume.get_width()//2, SCREEN_HEIGHT//2))
        self.screen.blit(quit_text, (SCREEN_WIDTH//2 - quit_text.get_width()//2, SCREEN_HEIGHT//2 + 50))

    def draw_game_over(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.fill(BLACK)
        overlay.set_alpha(200)
        self.screen.blit(overlay, (0, 0))

        game_over = self.font_large.render("GAME OVER", True, RED)
        self.screen.blit(game_over, (SCREEN_WIDTH//2 - game_over.get_width()//2, SCREEN_HEIGHT//2 - 150))

        wave_text = self.font_medium.render(f"Survived {self.world.current_wave} waves", True, WHITE)
        score_text = self.font_medium.render(f"Final Score: {self.world.score}", True, YELLOW)
        kills_text = self.font_medium.render(f"Total Kills: {self.world.kills}", True, WHITE)

        self.screen.blit(wave_text, (SCREEN_WIDTH//2 - wave_text.get_width()//2, SCREEN_HEIGHT//2 - 50))
        self.screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, SCREEN_HEIGHT//2))
        self.screen.blit(kills_text, (SCREEN_WIDTH//2 - kills_text.get_width()//2, SCREEN_HEIGHT//2 + 50))

        retry = self.font_small.render("Press R to retry", True, WHITE)
        menu = self.font_small.render("Press ESC for menu", True, WHITE)
        self.screen.blit(retry, (SCREEN_WIDTH//2 - retry.get_width()//2, SCREEN_HEIGHT//2 + 150))
        self.screen.blit(menu, (SCREEN_WIDTH//2 - menu.get_width()//2, SCREEN_HEIGHT//2 + 190))

    def draw(self):
        if self.state == GameState.MENU:
            self.draw_menu()
        elif self.state == GameState.CLASS_SELECT:
            self.draw_class_select()
        elif self.state == GameState.HOST_GAME:
            self.draw_host_screen()
        elif self.state == GameState.JOIN_GAME:
            self.draw_join_screen()
        elif self.state == GameState.PLAYING:
            self.world.draw(self.screen, self.camera_offset)
            self.draw_hud()
        elif self.state == GameState.PAUSED:
            self.world.draw(self.screen, self.camera_offset)
            self.draw_hud()
            self.draw_paused()
        elif self.state == GameState.GAME_OVER:
            self.world.draw(self.screen, self.camera_offset)
            self.draw_game_over()

        pygame.display.flip()

    async def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                if self.state == GameState.MENU:
                    self.handle_menu_events(event)
                elif self.state == GameState.CLASS_SELECT:
                    self.handle_class_select_events(event)
                elif self.state == GameState.HOST_GAME:
                    self.handle_host_events(event)
                elif self.state == GameState.JOIN_GAME:
                    self.handle_join_events(event)
                elif self.state == GameState.PLAYING:
                    self.handle_playing_events(event)
                elif self.state == GameState.PAUSED:
                    self.handle_paused_events(event)
                elif self.state == GameState.GAME_OVER:
                    self.handle_game_over_events(event)

            self.update(dt)
            self.draw()

            await asyncio.sleep(0)  # Required for Pygbag

        # Cleanup
        self.network.close()
        pygame.quit()


async def main():
    game = Game()
    await game.run()


if __name__ == "__main__":
    asyncio.run(main())
