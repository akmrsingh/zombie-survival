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

# Weapon Types
@dataclass
class WeaponStats:
    name: str
    damage: int
    fire_rate: float  # shots per second
    reload_time: float  # seconds
    mag_size: int
    max_ammo: int
    bullet_speed: float
    spread: float  # degrees
    bullet_count: int = 1
    explosive: bool = False
    explosion_radius: float = 0
    range: float = 800

# Realistic weapon definitions
WEAPONS = {
    # Ranger weapons
    "pistol": WeaponStats("M1911 Pistol", 25, 3.0, 1.5, 7, 70, 20, 3),
    "rifle": WeaponStats("M4 Carbine", 30, 8.0, 2.0, 30, 180, 25, 2),
    "sniper": WeaponStats("Barrett M82", 150, 0.8, 3.0, 5, 25, 40, 0.5, range=1200),
    "shotgun": WeaponStats("Remington 870", 15, 1.2, 2.5, 8, 40, 15, 15, bullet_count=8),
    "smg": WeaponStats("MP5", 18, 12.0, 1.8, 30, 150, 18, 5),

    # Tank weapons
    "rpg": WeaponStats("RPG-7", 100, 0.5, 4.0, 1, 10, 12, 2, explosive=True, explosion_radius=100),
    "grenade_launcher": WeaponStats("M32 MGL", 80, 1.0, 3.5, 6, 24, 10, 3, explosive=True, explosion_radius=80),
    "minigun": WeaponStats("M134 Minigun", 20, 30.0, 5.0, 200, 600, 22, 8),

    # Builder tools
    "nail_gun": WeaponStats("Nail Gun", 10, 5.0, 1.0, 50, 200, 15, 8),

    # Healer weapons
    "tranq_pistol": WeaponStats("Tranq Pistol", 15, 2.0, 1.5, 10, 50, 12, 5),
}


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
    """Projectile class for all weapons."""
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

    def update(self, dt):
        move_dist = self.speed * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.distance_traveled += move_dist
        if self.distance_traveled > self.range:
            self.active = False
        return self.active

    def draw(self, screen, camera_offset):
        pygame.draw.circle(screen, YELLOW,
                         (int(self.x - camera_offset[0]), int(self.y - camera_offset[1])), 4)
        # Trail effect
        trail_x = self.x - self.vx * 0.02
        trail_y = self.y - self.vy * 0.02
        pygame.draw.line(screen, ORANGE,
                        (int(trail_x - camera_offset[0]), int(trail_y - camera_offset[1])),
                        (int(self.x - camera_offset[0]), int(self.y - camera_offset[1])), 2)


class Wall:
    """Buildable wall for Builder class."""
    def __init__(self, x, y, width=80, height=20, health=200):
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
    def __init__(self, x, y, zombie_type="normal", wave=1):
        self.x = x
        self.y = y
        self.zombie_type = zombie_type
        self.wave = wave

        # Type-specific stats
        if zombie_type == "normal":
            self.health = 50 + wave * 10
            self.speed = 80 + wave * 2
            self.damage = 10 + wave
            self.size = 20
            self.color = ZOMBIE_GREEN
        elif zombie_type == "runner":
            self.health = 30 + wave * 5
            self.speed = 150 + wave * 5
            self.damage = 8 + wave
            self.size = 16
            self.color = (100, 150, 100)
        elif zombie_type == "tank":
            self.health = 200 + wave * 30
            self.speed = 40 + wave
            self.damage = 25 + wave * 2
            self.size = 35
            self.color = (30, 80, 30)
        elif zombie_type == "spitter":
            self.health = 40 + wave * 8
            self.speed = 60 + wave * 2
            self.damage = 15 + wave
            self.size = 22
            self.color = (80, 120, 40)
            self.spit_cooldown = 0
            self.spit_range = 300

        self.max_health = self.health
        self.active = True
        self.attack_cooldown = 0
        self.target = None
        self.angle = 0
        self.knockback_vx = 0
        self.knockback_vy = 0

    def update(self, dt, players, walls):
        # Apply knockback
        if abs(self.knockback_vx) > 1 or abs(self.knockback_vy) > 1:
            self.x += self.knockback_vx * dt
            self.y += self.knockback_vy * dt
            self.knockback_vx *= 0.9
            self.knockback_vy *= 0.9

        # Find nearest target (player or wall)
        nearest_dist = float('inf')
        nearest_target = None
        target_type = None

        for player in players:
            if player.health > 0:
                dist = math.sqrt((player.x - self.x)**2 + (player.y - self.y)**2)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_target = player
                    target_type = "player"

        # Check walls in path
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

            # Attack
            self.attack_cooldown -= dt
            if self.attack_cooldown <= 0:
                if target_type == "player" and nearest_dist < 40:
                    nearest_target.take_damage(self.damage)
                    self.attack_cooldown = 1.0
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

        # Body
        pygame.draw.circle(screen, self.color, (draw_x, draw_y), self.size)
        pygame.draw.circle(screen, DARK_GREEN, (draw_x, draw_y), self.size, 2)

        # Eyes (facing direction)
        eye_offset = self.size * 0.4
        eye_x = draw_x + math.cos(self.angle) * eye_offset
        eye_y = draw_y + math.sin(self.angle) * eye_offset
        pygame.draw.circle(screen, RED, (int(eye_x - 4), int(eye_y)), 4)
        pygame.draw.circle(screen, RED, (int(eye_x + 4), int(eye_y)), 4)

        # Health bar
        if self.health < self.max_health:
            bar_width = self.size * 2
            health_ratio = self.health / self.max_health
            pygame.draw.rect(screen, RED, (draw_x - bar_width//2, draw_y - self.size - 10, bar_width, 5))
            pygame.draw.rect(screen, GREEN, (draw_x - bar_width//2, draw_y - self.size - 10, bar_width * health_ratio, 5))


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
        self.is_reloading = False

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

    def setup_class(self, player_class):
        self.player_class = player_class

        if player_class == PlayerClass.BUILDER:
            self.max_health = 120
            self.speed = 200
            self.weapons = [WEAPONS["nail_gun"], WEAPONS["pistol"]]
            self.color = ORANGE
            self.ability_max_cooldown = 3  # Wall building cooldown
            self.max_walls = 10

        elif player_class == PlayerClass.RANGER:
            self.max_health = 100
            self.speed = 220
            self.weapons = [WEAPONS["rifle"], WEAPONS["pistol"], WEAPONS["shotgun"], WEAPONS["sniper"]]
            self.color = GREEN
            self.ability_max_cooldown = 15  # Rapid fire mode

        elif player_class == PlayerClass.HEALER:
            self.max_health = 90
            self.speed = 210
            self.weapons = [WEAPONS["tranq_pistol"], WEAPONS["smg"]]
            self.color = LIGHT_BLUE
            self.ability_max_cooldown = 12  # Heal zone

        elif player_class == PlayerClass.TANK:
            self.max_health = 180
            self.speed = 140
            self.weapons = [WEAPONS["minigun"], WEAPONS["rpg"], WEAPONS["grenade_launcher"]]
            self.color = RED
            self.ability_max_cooldown = 20  # Ground slam

        self.health = self.max_health
        self.current_weapon_index = 0
        self.current_ammo = self.weapons[0].mag_size
        self.reserve_ammo = self.weapons[0].max_ammo

    @property
    def current_weapon(self):
        return self.weapons[self.current_weapon_index]

    def take_damage(self, damage):
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
        # Movement
        move_x = 0
        move_y = 0

        # P1: WASD/Arrows, P2: IJKL
        if pygame.K_w in self.keys_pressed or pygame.K_UP in self.keys_pressed or pygame.K_i in self.keys_pressed:
            move_y -= 1
        if pygame.K_s in self.keys_pressed or pygame.K_DOWN in self.keys_pressed or pygame.K_k in self.keys_pressed:
            move_y += 1
        if pygame.K_a in self.keys_pressed or pygame.K_LEFT in self.keys_pressed or pygame.K_j in self.keys_pressed:
            move_x -= 1
        if pygame.K_d in self.keys_pressed or pygame.K_RIGHT in self.keys_pressed or pygame.K_l in self.keys_pressed:
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

        self.x += move_x * current_speed * dt
        self.y += move_y * current_speed * dt

        # Keep in bounds
        self.x = max(self.size, min(game_world.width - self.size, self.x))
        self.y = max(self.size, min(game_world.height - self.size, self.y))

        # Aim towards mouse or auto-aim at nearest zombie
        if self.auto_aim and game_world.zombies:
            # Find nearest zombie
            nearest_dist = float('inf')
            nearest_zombie = None
            for zombie in game_world.zombies:
                dist = math.sqrt((zombie.x - self.x)**2 + (zombie.y - self.y)**2)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_zombie = zombie
            if nearest_zombie and nearest_dist < 500:  # Only aim if zombie is close
                self.angle = math.atan2(nearest_zombie.y - self.y, nearest_zombie.x - self.x)
                self.auto_shoot = True
            else:
                self.auto_shoot = False
        else:
            screen_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            dx = self.mouse_pos[0] - screen_center[0]
            dy = self.mouse_pos[1] - screen_center[1]
            self.angle = math.atan2(dy, dx)

        # Cooldowns
        self.fire_cooldown -= dt
        self.ability_cooldown -= dt

        # Reloading
        if self.is_reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                ammo_needed = self.current_weapon.mag_size - self.current_ammo
                ammo_to_add = min(ammo_needed, self.reserve_ammo)
                self.current_ammo += ammo_to_add
                self.reserve_ammo -= ammo_to_add
                self.is_reloading = False

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
        weapon = self.current_weapon
        self.current_ammo -= 1
        self.fire_cooldown = 1.0 / weapon.fire_rate

        # Create bullets
        for _ in range(weapon.bullet_count):
            spread = math.radians(random.uniform(-weapon.spread, weapon.spread))
            bullet_angle = self.angle + spread

            # Bullet starts at gun position
            gun_dist = self.size + 10
            bx = self.x + math.cos(self.angle) * gun_dist
            by = self.y + math.sin(self.angle) * gun_dist

            bullet = Bullet(bx, by, bullet_angle, weapon, self.player_id)
            game_world.bullets.append(bullet)

        # Muzzle flash particles
        for _ in range(5):
            angle = self.angle + random.uniform(-0.5, 0.5)
            speed = random.uniform(100, 200)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            game_world.particles.append(Particle(
                self.x + math.cos(self.angle) * (self.size + 15),
                self.y + math.sin(self.angle) * (self.size + 15),
                YELLOW, (vx, vy), random.uniform(0.1, 0.2), 4
            ))

        # Auto-reload when empty
        if self.current_ammo <= 0 and self.reserve_ammo > 0:
            self.start_reload()

    def start_reload(self):
        if not self.is_reloading and self.reserve_ammo > 0 and self.current_ammo < self.current_weapon.mag_size:
            self.is_reloading = True
            self.reload_timer = self.current_weapon.reload_time

    def use_ability(self, game_world):
        if self.ability_cooldown > 0:
            return

        if self.player_class == PlayerClass.BUILDER:
            # Build wall
            if len([w for w in game_world.walls if w.active]) < self.max_walls:
                wall_x = self.x + math.cos(self.angle) * 60
                wall_y = self.y + math.sin(self.angle) * 60
                wall = Wall(wall_x, wall_y)
                game_world.walls.append(wall)
                self.walls_built.append(wall)
                self.ability_cooldown = self.ability_max_cooldown

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

        # Gun
        gun_length = 30
        gun_end_x = draw_x + math.cos(self.angle) * (self.size + gun_length)
        gun_end_y = draw_y + math.sin(self.angle) * (self.size + gun_length)
        pygame.draw.line(screen, DARK_GRAY, (draw_x, draw_y), (int(gun_end_x), int(gun_end_y)), 6)

        # Health bar
        bar_width = 50
        bar_height = 6
        health_ratio = self.health / self.max_health
        pygame.draw.rect(screen, RED, (draw_x - bar_width//2, draw_y - self.size - 15, bar_width, bar_height))
        pygame.draw.rect(screen, GREEN, (draw_x - bar_width//2, draw_y - self.size - 15, bar_width * health_ratio, bar_height))

        # Reload indicator
        if self.is_reloading:
            reload_progress = 1 - (self.reload_timer / self.current_weapon.reload_time)
            pygame.draw.arc(screen, YELLOW, (draw_x - 20, draw_y - 20, 40, 40),
                          -math.pi/2, -math.pi/2 + reload_progress * math.pi * 2, 3)

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
        text = font.render("BUNKER - Press E to change class", True, WHITE)
        screen.blit(text, (draw_rect.centerx - text.get_width()//2, draw_rect.y - 40))


class GameWorld:
    """Main game world containing all entities."""
    def __init__(self, width=3000, height=3000):
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

        # Scores
        self.kills = 0
        self.score = 0

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

        # Zombie type based on wave
        zombie_types = ["normal"]
        if self.current_wave >= 2:
            zombie_types.append("runner")
        if self.current_wave >= 3:
            zombie_types.append("tank")
        if self.current_wave >= 5:
            zombie_types.append("spitter")

        # Weight towards normal zombies
        weights = [5] + [2] * (len(zombie_types) - 1)
        zombie_type = random.choices(zombie_types, weights[:len(zombie_types)])[0]

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
            if not zombie.update(dt, self.players, self.walls):
                self.zombies.remove(zombie)

        # Update bullets
        for bullet in self.bullets[:]:
            if not bullet.update(dt):
                self.bullets.remove(bullet)
                continue

            # Check zombie collisions
            for zombie in self.zombies[:]:
                dist = math.sqrt((bullet.x - zombie.x)**2 + (bullet.y - zombie.y)**2)
                if dist < zombie.size + 5:
                    angle = math.atan2(bullet.vy, bullet.vx)

                    if bullet.explosive:
                        # Explosion damage
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
                    else:
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

                    bullet.active = False
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    break

            # Check wall collisions
            for wall in self.walls:
                if wall.active and wall.get_rect().collidepoint(bullet.x, bullet.y):
                    bullet.active = False
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    break

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
        # Background
        screen.fill((30, 40, 30))

        # Grid
        grid_size = 100
        start_x = int(camera_offset[0] // grid_size) * grid_size
        start_y = int(camera_offset[1] // grid_size) * grid_size
        for x in range(start_x, int(camera_offset[0] + SCREEN_WIDTH + grid_size), grid_size):
            pygame.draw.line(screen, (40, 50, 40),
                           (x - camera_offset[0], 0), (x - camera_offset[0], SCREEN_HEIGHT))
        for y in range(start_y, int(camera_offset[1] + SCREEN_HEIGHT + grid_size), grid_size):
            pygame.draw.line(screen, (40, 50, 40),
                           (0, y - camera_offset[1]), (SCREEN_WIDTH, y - camera_offset[1]))

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

            # Get host IP
            hostname = socket.gethostname()
            self.host_ip = socket.gethostbyname(hostname)

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

        # Input for IP
        self.ip_input = ""
        self.ip_active = False

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
            # Player 2+ use auto-aim since they can't use mouse
            if i >= 1:
                player.auto_aim = True
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
            elif event.key == pygame.K_4:
                self.num_local_players = 4
                self.state = GameState.CLASS_SELECT
            elif event.key == pygame.K_h:
                self.state = GameState.HOST_GAME
            elif event.key == pygame.K_j:
                self.state = GameState.JOIN_GAME
                self.ip_input = ""
            elif event.key == pygame.K_ESCAPE:
                self.running = False

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

            # Player 2 controls (Arrow keys + Enter) - if 2+ players
            if self.num_local_players >= 2:
                if event.key == pygame.K_LEFT:
                    idx = self.selected_class[1].value - 1
                    idx = (idx - 1) % 4 + 1
                    self.selected_class[1] = PlayerClass(idx)
                elif event.key == pygame.K_RIGHT:
                    idx = self.selected_class[1].value - 1
                    idx = (idx + 1) % 4 + 1
                    self.selected_class[1] = PlayerClass(idx)
                elif event.key == pygame.K_RETURN:
                    self.class_confirmed[1] = True

            # Check if all players confirmed
            if all(self.class_confirmed[:self.num_local_players]):
                self.reset_game()
                self.state = GameState.PLAYING

            if event.key == pygame.K_ESCAPE:
                self.state = GameState.MENU

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

            # Player 1 controls
            if len(self.local_players) > 0:
                player = self.local_players[0]
                player.keys_pressed.add(event.key)

                if event.key == pygame.K_r:
                    player.start_reload()
                elif event.key == pygame.K_q:
                    player.use_ability(self.world)
                elif event.key == pygame.K_1:
                    if len(player.weapons) > 0:
                        player.current_weapon_index = 0
                        player.current_ammo = player.weapons[0].mag_size
                        player.reserve_ammo = player.weapons[0].max_ammo
                elif event.key == pygame.K_2:
                    if len(player.weapons) > 1:
                        player.current_weapon_index = 1
                        player.current_ammo = player.weapons[1].mag_size
                        player.reserve_ammo = player.weapons[1].max_ammo
                elif event.key == pygame.K_3:
                    if len(player.weapons) > 2:
                        player.current_weapon_index = 2
                        player.current_ammo = player.weapons[2].mag_size
                        player.reserve_ammo = player.weapons[2].max_ammo
                elif event.key == pygame.K_4:
                    if len(player.weapons) > 3:
                        player.current_weapon_index = 3
                        player.current_ammo = player.weapons[3].mag_size
                        player.reserve_ammo = player.weapons[3].max_ammo
                elif event.key == pygame.K_e:
                    # Class switch in bunker
                    if self.world.bunker.is_player_inside(player):
                        self.state = GameState.CLASS_SELECT
                        self.class_confirmed = [False] * 4

            # Player 2 controls (IJKL + U for ability, O for reload)
            if len(self.local_players) > 1:
                player2 = self.local_players[1]
                # IJKL movement
                if event.key in [pygame.K_i, pygame.K_j, pygame.K_k, pygame.K_l]:
                    player2.keys_pressed.add(event.key)
                elif event.key == pygame.K_o:
                    player2.start_reload()
                elif event.key == pygame.K_u:
                    player2.use_ability(self.world)
                elif event.key == pygame.K_p:
                    player2.switch_weapon(1)

        elif event.type == pygame.KEYUP:
            if len(self.local_players) > 0:
                player = self.local_players[0]
                player.keys_pressed.discard(event.key)

            # Player 2 key up
            if len(self.local_players) > 1:
                player2 = self.local_players[1]
                player2.keys_pressed.discard(event.key)

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

    def handle_paused_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = GameState.PLAYING
            elif event.key == pygame.K_q:
                self.state = GameState.MENU

    def handle_game_over_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.state = GameState.CLASS_SELECT
                self.class_confirmed = [False] * 4
            elif event.key == pygame.K_ESCAPE:
                self.state = GameState.MENU

    def update(self, dt):
        if self.state == GameState.PLAYING:
            # Update mouse position for all local players
            mouse_pos = pygame.mouse.get_pos()
            for player in self.local_players:
                player.mouse_pos = mouse_pos

            # Update world
            self.world.update(dt)

            # Update camera to follow first local player
            if self.local_players:
                target_x = self.local_players[0].x - SCREEN_WIDTH // 2
                target_y = self.local_players[0].y - SCREEN_HEIGHT // 2
                self.camera_offset[0] += (target_x - self.camera_offset[0]) * 5 * dt
                self.camera_offset[1] += (target_y - self.camera_offset[1]) * 5 * dt

                # Clamp camera
                self.camera_offset[0] = max(0, min(self.world.width - SCREEN_WIDTH, self.camera_offset[0]))
                self.camera_offset[1] = max(0, min(self.world.height - SCREEN_HEIGHT, self.camera_offset[1]))

            # Check game over
            all_dead = all(p.health <= 0 for p in self.local_players)
            if all_dead:
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
            ("Press 4 - 4 Player Local", WHITE),
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
            "Controls:",
            "WASD/Arrows - Move | Mouse - Aim | LMB - Shoot",
            "R - Reload | Q - Class Ability | E - Change Class (in bunker)",
            "1-4 - Switch Weapons | Scroll - Cycle Weapons"
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
        inst_y = SCREEN_HEIGHT - 120
        if self.num_local_players >= 1:
            inst1 = self.font_small.render("P1: A/D to select, SPACE to confirm", True, WHITE)
            self.screen.blit(inst1, (SCREEN_WIDTH//2 - inst1.get_width()//2, inst_y))
        if self.num_local_players >= 2:
            inst2 = self.font_small.render("P2: LEFT/RIGHT to select, ENTER to confirm", True, WHITE)
            self.screen.blit(inst2, (SCREEN_WIDTH//2 - inst2.get_width()//2, inst_y + 35))

    def draw_host_screen(self):
        self.screen.fill(BLACK)

        title = self.font_large.render("HOST GAME", True, GREEN)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 200))

        if self.network.is_host:
            ip_text = self.font_medium.render(f"Your IP: {self.network.host_ip}", True, WHITE)
            port_text = self.font_medium.render(f"Port: {self.network.port}", True, WHITE)
            waiting = self.font_small.render(f"Waiting for players... ({len(self.network.clients)} connected)", True, YELLOW)

            self.screen.blit(ip_text, (SCREEN_WIDTH//2 - ip_text.get_width()//2, 350))
            self.screen.blit(port_text, (SCREEN_WIDTH//2 - port_text.get_width()//2, 410))
            self.screen.blit(waiting, (SCREEN_WIDTH//2 - waiting.get_width()//2, 500))
        else:
            inst = self.font_medium.render("Press ENTER to start hosting", True, WHITE)
            self.screen.blit(inst, (SCREEN_WIDTH//2 - inst.get_width()//2, 400))

        back = self.font_small.render("Press ESC to go back", True, GRAY)
        self.screen.blit(back, (SCREEN_WIDTH//2 - back.get_width()//2, SCREEN_HEIGHT - 100))

    def draw_join_screen(self):
        self.screen.fill(BLACK)

        title = self.font_large.render("JOIN GAME", True, BLUE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 200))

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
        ability_text = self.font_small.render(f"Ability (Q): ", True, WHITE)
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
            hint = self.font_small.render("Press E to change class", True, YELLOW)
            self.screen.blit(hint, (SCREEN_WIDTH//2 - hint.get_width()//2, SCREEN_HEIGHT - 80))

        # Crosshair
        mouse_pos = pygame.mouse.get_pos()
        pygame.draw.circle(self.screen, WHITE, mouse_pos, 10, 1)
        pygame.draw.line(self.screen, WHITE, (mouse_pos[0] - 15, mouse_pos[1]), (mouse_pos[0] - 5, mouse_pos[1]), 2)
        pygame.draw.line(self.screen, WHITE, (mouse_pos[0] + 5, mouse_pos[1]), (mouse_pos[0] + 15, mouse_pos[1]), 2)
        pygame.draw.line(self.screen, WHITE, (mouse_pos[0], mouse_pos[1] - 15), (mouse_pos[0], mouse_pos[1] - 5), 2)
        pygame.draw.line(self.screen, WHITE, (mouse_pos[0], mouse_pos[1] + 5), (mouse_pos[0], mouse_pos[1] + 15), 2)

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

        retry = self.font_small.render("Press SPACE to retry", True, WHITE)
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
