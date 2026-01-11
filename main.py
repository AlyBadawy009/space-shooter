# Space Shooter 
# ===============================================================#
# Controls:
# Move: WASD/Arrows | Shoot: SPACE (hold) | Slow: LSHIFT | Pause: P | Restart: R | Quit: ESC
# Menu: 1/2/3 difficulty, ENTER start

import math
import random
import struct
import pygame

#  EASY SETTINGS (Edit here) 
FEATURES = {
    "WAVES": True,
    "BOSS": True,
    "POWERUPS": True,
    "COMBO": True,
    "HEALTH": True,
    "PARTICLES": True,
    "SCREEN_SHAKE": False,
    "SOUNDS": True,
    "FULLSCREEN": True,      # True = fullscreen
}

WIDTH, HEIGHT = 960, 540
FPS = 60

PLAYER_SPEED = 420.0
PLAYER_SLOW_MULT = 0.55
PLAYER_RADIUS = 18
PLAYER_MAX_HP = 100
PLAYER_IFRAMES = 0.9

BULLET_SPEED = 780.0
BULLET_LIFETIME = 1.4
FIRE_COOLDOWN = 0.11

ENEMY_BASE_SPEED = 150.0
ENEMY_SPAWN_BASE = 1.05
ENEMY_HP = 20

ENEMY_BULLET_SPEED = 420.0
ENEMY_FIRE_COOLDOWN = 1.35

WAVE_DURATION = 18.0
WAVE_BANNER_TIME = 2.0
BOSS_EVERY_WAVES = 4
BOSS_WARNING_TIME = 2.2

BOSS_HP = 450
BOSS_SPEED = 140.0
BOSS_FIRE_COOLDOWN = 0.28

POWERUP_SPAWN_BASE = 7.0
POWERUP_DURATION = 7.0
SHIELD_HP = 55

COMBO_WINDOW = 1.8
COMBO_STEP = 6
MAX_MULTIPLIER = 6

SHAKE_DECAY = 18.0
PARTICLE_LIFE = 0.55

MASTER_VOLUME = 0.30
SFX_VOLUME = 0.65
SAMPLE_RATE = 44100

DIFFICULTIES = {
    "Easy":   {"enemy_mul": 0.85, "spawn_mul": 1.15, "boss_mul": 0.9},
    "Normal": {"enemy_mul": 1.00, "spawn_mul": 1.00, "boss_mul": 1.0},
    "Hard":   {"enemy_mul": 1.15, "spawn_mul": 0.88, "boss_mul": 1.1},
}

HIGHSCORE_FILE = "highscore.txt"

def clamp(v, a, b):
    return max(a, min(b, v))

def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip() or "0")
    except Exception:
        return 0

def save_highscore(v: int):
    try:
        with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
            f.write(str(int(v)))
    except Exception:
        pass

class SoundManager:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.ok = False
        self.sounds = {}
        if not enabled:
            return
        try:
            pygame.mixer.pre_init(SAMPLE_RATE, size=-16, channels=1, buffer=512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(10)
            self.ok = True
        except Exception:
            self.enabled = False
            self.ok = False
            return
        self.sounds["shoot"] = self._tone(880, 0.045, amp=0.40)
        self.sounds["hit"] = self._tone(210, 0.12, amp=0.50)
        self.sounds["boom"] = self._noise(0.16, amp=0.40)
        self.sounds["power"] = self._tone(520, 0.09, amp=0.45)
        self.sounds["boss"] = self._tone(320, 0.20, amp=0.45)
        for s in self.sounds.values():
            s.set_volume(MASTER_VOLUME * SFX_VOLUME)

    def _tone(self, freq_hz: float, duration: float, amp: float = 0.45):
        n = int(SAMPLE_RATE * duration)
        buf = bytearray()
        fade = max(1, int(0.01 * SAMPLE_RATE))
        for i in range(n):
            t = i / SAMPLE_RATE
            sample = math.sin(2 * math.pi * freq_hz * t)
            if i < fade:
                sample *= (i / fade)
            if i > n - fade:
                sample *= max(0.0, (n - i) / fade)
            val = int(sample * amp * 32767)
            buf += struct.pack("<h", val)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def _noise(self, duration: float, amp: float = 0.35):
        n = int(SAMPLE_RATE * duration)
        buf = bytearray()
        fade = max(1, int(0.02 * SAMPLE_RATE))
        for i in range(n):
            sample = (random.random() * 2 - 1)
            if i < fade:
                sample *= (i / fade)
            if i > n - fade:
                sample *= max(0.0, (n - i) / fade)
            val = int(sample * amp * 32767)
            buf += struct.pack("<h", val)
        return pygame.mixer.Sound(buffer=bytes(buf))

    def play(self, name: str):
        if self.enabled and self.ok and name in self.sounds:
            try:
                self.sounds[name].play()
            except Exception:
                pass

class Particle:
    def __init__(self, pos, vel, life=PARTICLE_LIFE, radius=3, color=(255, 200, 80)):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.life = life
        self.max_life = life
        self.radius = radius
        self.color = color
    def update(self, dt):
        self.pos += self.vel * dt
        self.vel *= (1.0 - 1.8 * dt)
        self.life -= dt
    def draw(self, surf, offset=(0, 0)):
        if self.life <= 0: return
        a = clamp(self.life / self.max_life, 0, 1)
        r = max(1, int(self.radius * a))
        pygame.draw.circle(surf, self.color, (int(self.pos.x + offset[0]), int(self.pos.y + offset[1])), r)
    @property
    def dead(self): return self.life <= 0

class Star:
    def __init__(self):
        self.reset()
        self.x = random.uniform(0, WIDTH)
    def reset(self):
        self.x = WIDTH + random.uniform(0, WIDTH)
        self.y = random.uniform(0, HEIGHT)
        self.s = random.uniform(1.0, 3.2)
        self.v = random.uniform(40, 140)
    def update(self, dt, speed_mul=1.0):
        self.x -= self.v * speed_mul * dt
        if self.x < -10:
            self.reset()
    def draw(self, surf, offset=(0, 0)):
        pygame.draw.circle(surf, (200, 200, 220), (int(self.x + offset[0]), int(self.y + offset[1])), int(self.s))

class Bullet:
    def __init__(self, pos, vel, friendly=True, radius=4, color=(220, 240, 255)):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.friendly = friendly
        self.radius = radius
        self.color = color
        self.life = BULLET_LIFETIME
    def update(self, dt):
        self.pos += self.vel * dt
        self.life -= dt
    @property
    def dead(self):
        return self.life <= 0 or self.pos.x < -50 or self.pos.x > WIDTH + 50 or self.pos.y < -50 or self.pos.y > HEIGHT + 50
    def draw(self, surf, offset=(0, 0)):
        pygame.draw.circle(surf, self.color, (int(self.pos.x + offset[0]), int(self.pos.y + offset[1])), self.radius)
    def collides_circle(self, center, r):
        return self.pos.distance_to(center) <= (self.radius + r)

class Player:
    def __init__(self):
        self.pos = pygame.Vector2(WIDTH * 0.18, HEIGHT * 0.5)
        self.hp = PLAYER_MAX_HP
        self.iframes = 0.0
        self.shield = 0
        self.rapid_time = 0.0
        self.spread_time = 0.0
        self.fire_cd = 0.0
    @property
    def radius(self): return PLAYER_RADIUS
    @property
    def alive(self): return self.hp > 0
    def update(self, dt, keys):
        self.iframes = max(0.0, self.iframes - dt)
        self.rapid_time = max(0.0, self.rapid_time - dt)
        self.spread_time = max(0.0, self.spread_time - dt)
        slow = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
        speed = PLAYER_SPEED * (PLAYER_SLOW_MULT if slow else 1.0)
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        v = pygame.Vector2(dx, dy)
        if v.length_squared() > 0: v = v.normalize() * speed
        self.pos += v * dt
        self.pos.x = clamp(self.pos.x, 40, WIDTH - 40)
        self.pos.y = clamp(self.pos.y, 40, HEIGHT - 40)
        self.fire_cd = max(0.0, self.fire_cd - dt)
    def can_shoot(self):
        cd = FIRE_COOLDOWN * (0.55 if self.rapid_time > 0 else 1.0)
        return self.fire_cd <= 0.0, cd
    def shoot(self, bullets, sound: SoundManager):
        ok, cd = self.can_shoot()
        if not ok: return
        self.fire_cd = cd
        base = pygame.Vector2(BULLET_SPEED, 0)
        bullets.append(Bullet(self.pos + (18, 0), base, True, 4, (220, 240, 255)))
        if self.spread_time > 0:
            ang = math.radians(14)
            v1 = pygame.Vector2(BULLET_SPEED, 0).rotate_rad(ang)
            v2 = pygame.Vector2(BULLET_SPEED, 0).rotate_rad(-ang)
            bullets.append(Bullet(self.pos + (18, -2), v1, True, 4, (200, 255, 220)))
            bullets.append(Bullet(self.pos + (18, 2), v2, True, 4, (200, 255, 220)))
        sound.play("shoot")
    def take_damage(self, dmg: int, sound: SoundManager):
        if not FEATURES["HEALTH"]:
            self.hp = 0
            return
        if self.iframes > 0: return
        if self.shield > 0:
            self.shield = max(0, self.shield - dmg)
            self.iframes = PLAYER_IFRAMES * 0.55
            sound.play("hit")
            return
        self.hp -= dmg
        self.iframes = PLAYER_IFRAMES
        sound.play("hit")
    def draw(self, surf, offset=(0, 0)):
        if self.iframes > 0 and (pygame.time.get_ticks() // 120) % 2 == 0: return
        x, y = int(self.pos.x + offset[0]), int(self.pos.y + offset[1])
        pygame.draw.polygon(surf, (235, 235, 245), [(x + 18, y), (x - 18, y - 10), (x - 18, y + 10)])
        pygame.draw.circle(surf, (60, 80, 120), (x - 6, y), 5)
        if self.shield > 0:
            pygame.draw.circle(surf, (110, 190, 255), (x, y), self.radius + 8, width=3)

class EnemyBase:
    def __init__(self, pos, hp=ENEMY_HP, radius=16):
        self.pos = pygame.Vector2(pos)
        self.hp = hp
        self.radius = radius
        self.dead_flag = False
    @property
    def dead(self): return self.dead_flag or self.hp <= 0 or self.pos.x < -120
    def hit(self, dmg, sound: SoundManager):
        self.hp -= dmg
        if self.hp <= 0: sound.play("boom")
    def update(self, dt, game): pass
    def draw(self, surf, offset=(0, 0)):
        x, y = int(self.pos.x + offset[0]), int(self.pos.y + offset[1])
        pygame.draw.circle(surf, (255, 120, 120), (x, y), self.radius)
        pygame.draw.circle(surf, (60, 30, 30), (x, y), self.radius, width=2)

class EnemyChaser(EnemyBase):
    def __init__(self, pos, speed, hp=ENEMY_HP):
        super().__init__(pos, hp=hp, radius=16)
        self.speed = speed
    def update(self, dt, game):
        target_y = game.player.pos.y
        dy = clamp(target_y - self.pos.y, -1, 1)
        self.pos.x -= self.speed * dt
        self.pos.y += dy * (self.speed * 0.65) * dt
        self.pos.y = clamp(self.pos.y, 30, HEIGHT - 30)
    def draw(self, surf, offset=(0, 0)):
        x, y = int(self.pos.x + offset[0]), int(self.pos.y + offset[1])
        pygame.draw.circle(surf, (255, 150, 90), (x, y), self.radius)
        pygame.draw.circle(surf, (35, 35, 40), (x + 4, y), 4)

class EnemyShooter(EnemyBase):
    def __init__(self, pos, speed, hp=ENEMY_HP):
        super().__init__(pos, hp=hp, radius=17)
        self.speed = speed
        self.fire_cd = random.uniform(0.4, ENEMY_FIRE_COOLDOWN)
    def update(self, dt, game):
        self.pos.x -= self.speed * dt
        self.pos.y += math.sin(pygame.time.get_ticks() * 0.004 + self.pos.x * 0.01) * 18 * dt
        self.pos.y = clamp(self.pos.y, 30, HEIGHT - 30)
        self.fire_cd -= dt
        if self.fire_cd <= 0 and self.pos.x < WIDTH * 0.92:
            self.fire_cd = ENEMY_FIRE_COOLDOWN * random.uniform(0.8, 1.2)
            dv = (game.player.pos - self.pos)
            if dv.length_squared() > 0: dv = dv.normalize()
            game.bullets.append(Bullet(self.pos, dv * ENEMY_BULLET_SPEED, False, 4, (255, 210, 120)))
    def draw(self, surf, offset=(0, 0)):
        x, y = int(self.pos.x + offset[0]), int(self.pos.y + offset[1])
        pygame.draw.rect(surf, (255, 110, 170), (x - 18, y - 12, 36, 24), border_radius=10)
        pygame.draw.circle(surf, (25, 25, 30), (x + 8, y), 4)

class Boss(EnemyBase):
    def __init__(self, pos, hp):
        super().__init__(pos, hp=hp, radius=48)
        self.speed = BOSS_SPEED
        self.fire_cd = 0.9
        self.phase = 0.0
        self.entering = True
    def update(self, dt, game):
        self.phase += dt
        if self.entering:
            self.pos.x -= self.speed * dt
            if self.pos.x < WIDTH * 0.78:
                self.entering = False
        else:
            self.pos.y = HEIGHT * 0.5 + math.sin(self.phase * 1.4) * 110
        self.fire_cd -= dt
        if self.fire_cd <= 0:
            self.fire_cd = BOSS_FIRE_COOLDOWN
            for a in (-26, -13, 0, 13, 26):
                v = pygame.Vector2(-1, 0).rotate(a) * (ENEMY_BULLET_SPEED * 1.10)
                game.bullets.append(Bullet(self.pos + (-35, 0), v, False, 5, (255, 140, 140)))
            if int(self.phase) % 2 == 0:
                dv = (game.player.pos - self.pos)
                if dv.length_squared() > 0: dv = dv.normalize()
                game.bullets.append(Bullet(self.pos + (-35, 0), dv * (ENEMY_BULLET_SPEED * 1.25), False, 5, (255, 200, 90)))
    def draw(self, surf, offset=(0, 0)):
        x, y = int(self.pos.x + offset[0]), int(self.pos.y + offset[1])
        pygame.draw.circle(surf, (160, 120, 255), (x, y), self.radius)
        pygame.draw.circle(surf, (30, 30, 40), (x - 10, y - 10), 7)
        pygame.draw.circle(surf, (30, 30, 40), (x - 10, y + 10), 7)
        pygame.draw.rect(surf, (30, 30, 40), (x - 64, y - 18, 30, 36), border_radius=10)
        bar_w, bar_h = 200, 10
        px, py = x - bar_w // 2, y - self.radius - 20
        pygame.draw.rect(surf, (40, 40, 55), (px, py, bar_w, bar_h), border_radius=6)
        frac = clamp(self.hp / BOSS_HP, 0, 1)
        pygame.draw.rect(surf, (220, 220, 245), (px, py, int(bar_w * frac), bar_h), border_radius=6)

class PowerUp:
    TYPES = ("rapid", "spread", "shield", "heal")
    def __init__(self, pos, ptype: str):
        self.pos = pygame.Vector2(pos)
        self.ptype = ptype
        self.radius = 14
        self.vel = pygame.Vector2(-180, 0)
    def update(self, dt): self.pos += self.vel * dt
    @property
    def dead(self): return self.pos.x < -80
    def draw(self, surf, offset=(0, 0)):
        colors = {"rapid": (120, 255, 190), "spread": (160, 255, 160), "shield": (110, 190, 255), "heal": (255, 140, 180)}
        c = colors[self.ptype]
        pygame.draw.circle(surf, c, (int(self.pos.x + offset[0]), int(self.pos.y + offset[1])), self.radius)
        pygame.draw.circle(surf, (25, 25, 30), (int(self.pos.x + offset[0]), int(self.pos.y + offset[1])), self.radius, width=2)

class Game:
    MENU, PLAYING, PAUSED, GAMEOVER = "menu", "playing", "paused", "gameover"
    def __init__(self, sound: SoundManager):
        self.sound = sound
        self.state = self.MENU
        self.difficulty = "Normal"
        self.player = Player()
        self.enemies = []
        self.powerups = []
        self.bullets = []
        self.particles = []
        self.stars = [Star() for _ in range(80)]
        self.score = 0
        self.high = load_highscore()
        self.time = 0.0
        self.wave = 1
        self.wave_banner = WAVE_BANNER_TIME if FEATURES["WAVES"] else 0.0
        self.boss_warning = 0.0
        self.boss_active = False
        self.enemy_timer = ENEMY_SPAWN_BASE
        self.power_timer = POWERUP_SPAWN_BASE
        self.combo_kills = 0
        self.combo_timer = 0.0
        self.shake = 0.0

    def reset_run(self):
        self.player = Player()
        self.enemies.clear(); self.powerups.clear(); self.bullets.clear(); self.particles.clear()
        self.score = 0
        self.time = 0.0; self.wave = 1
        self.wave_banner = WAVE_BANNER_TIME if FEATURES["WAVES"] else 0.0
        self.boss_warning = 0.0; self.boss_active = False
        self.enemy_timer = ENEMY_SPAWN_BASE
        self.power_timer = POWERUP_SPAWN_BASE
        self.combo_kills = 0; self.combo_timer = 0.0
        self.shake = 0.0
        self.state = self.PLAYING

    def diff_cfg(self): return DIFFICULTIES[self.difficulty]
    def wave_scaler(self): return 1.0 if not FEATURES["WAVES"] else 1.0 + (self.wave - 1) * 0.11
    def spawn_rate(self):
        cfg = self.diff_cfg(); scaler = self.wave_scaler()
        return (ENEMY_SPAWN_BASE / scaler) * cfg["spawn_mul"]
    def enemy_speed(self):
        cfg = self.diff_cfg(); scaler = self.wave_scaler()
        return ENEMY_BASE_SPEED * cfg["enemy_mul"] * (1.0 + (scaler - 1) * 0.65)
    def enemy_hp(self):
        cfg = self.diff_cfg(); scaler = self.wave_scaler()
        return int(ENEMY_HP * cfg["enemy_mul"] * (1.0 + (scaler - 1) * 0.55))
    def score_mult(self):
        if not FEATURES["COMBO"]: return 1
        m = 1 + (self.combo_kills // COMBO_STEP)
        return int(clamp(m, 1, MAX_MULTIPLIER))
    def add_shake(self, amount):
        if FEATURES["SCREEN_SHAKE"]:
            self.shake = min(24.0, self.shake + amount)

    def maybe_spawn_enemy(self, dt):
        if self.boss_active: return
        self.enemy_timer -= dt
        if self.enemy_timer <= 0:
            self.enemy_timer = random.uniform(0.75, 1.35) * self.spawn_rate()
            y = random.uniform(40, HEIGHT - 40); x = WIDTH + 60
            spd = self.enemy_speed(); hp = self.enemy_hp()
            if self.wave >= 3 and random.random() < 0.38:
                self.enemies.append(EnemyShooter((x, y), spd * 0.92, hp=hp + 8))
            else:
                self.enemies.append(EnemyChaser((x, y), spd, hp=hp))

    def maybe_spawn_powerup(self, dt):
        if not FEATURES["POWERUPS"]: return
        self.power_timer -= dt
        if self.power_timer <= 0:
            scaler = self.wave_scaler()
            self.power_timer = random.uniform(0.7, 1.2) * (POWERUP_SPAWN_BASE * (0.95 + scaler * 0.18))
            y = random.uniform(60, HEIGHT - 60); x = WIDTH + 40
            p = random.random()
            if p < 0.34: t = "rapid"
            elif p < 0.62: t = "spread"
            elif p < 0.84: t = "shield"
            else: t = "heal"
            self.powerups.append(PowerUp((x, y), t))

    def maybe_spawn_boss(self):
        if not (FEATURES["WAVES"] and FEATURES["BOSS"]): return
        if self.boss_active: return
        if self.wave > 1 and self.wave % BOSS_EVERY_WAVES == 0:
            if self.boss_warning <= 0:
                self.boss_warning = BOSS_WARNING_TIME
                self.sound.play("boss")

    def spawn_boss_now(self):
        cfg = self.diff_cfg()
        hp = int(BOSS_HP * cfg["boss_mul"] * (1.0 + (self.wave - 1) * 0.08))
        self.enemies.append(Boss((WIDTH + 120, HEIGHT * 0.5), hp=hp))
        self.boss_active = True

    def enemy_killed(self, enemy):
        base = 8 if isinstance(enemy, EnemyShooter) else 6
        self.score += base * self.score_mult()
        if FEATURES["COMBO"]:
            self.combo_kills += 1
            self.combo_timer = COMBO_WINDOW
        self.add_shake(7.0)
        if FEATURES["PARTICLES"]:
            for _ in range(18):
                ang = random.uniform(0, math.tau)
                sp = random.uniform(80, 320)
                vel = (math.cos(ang) * sp, math.sin(ang) * sp)
                self.particles.append(Particle(enemy.pos, vel, life=PARTICLE_LIFE, radius=random.randint(2, 4), color=(255, 200, 80)))

    def update_combo(self, dt):
        if not FEATURES["COMBO"]: return
        if self.combo_kills > 0:
            self.combo_timer -= dt
            if self.combo_timer <= 0:
                self.combo_kills = 0
                self.combo_timer = 0.0

    def apply_powerup(self, pu: PowerUp):
        self.sound.play("power")
        if pu.ptype == "rapid":
            self.player.rapid_time = POWERUP_DURATION
        elif pu.ptype == "spread":
            self.player.spread_time = POWERUP_DURATION
        elif pu.ptype == "shield":
            self.player.shield = min(SHIELD_HP, self.player.shield + SHIELD_HP)
        elif pu.ptype == "heal":
            self.player.hp = min(PLAYER_MAX_HP, self.player.hp + 35)

    def update(self, dt, keys):
        speed_mul = 1.0 + (self.wave_scaler() - 1) * 0.25
        for s in self.stars:
            s.update(dt, speed_mul=speed_mul)

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if not p.dead]

        if self.shake > 0:
            self.shake = max(0.0, self.shake - SHAKE_DECAY * dt)

        if self.state != self.PLAYING:
            return

        self.time += dt

        if FEATURES["WAVES"] and self.time >= self.wave * WAVE_DURATION:
            self.wave += 1
            self.wave_banner = WAVE_BANNER_TIME
            self.sound.play("power")
            self.enemy_timer = min(self.enemy_timer, self.spawn_rate())

        if self.wave_banner > 0:
            self.wave_banner -= dt

        self.maybe_spawn_boss()
        if self.boss_warning > 0:
            self.boss_warning -= dt
            if self.boss_warning <= 0:
                self.spawn_boss_now()

        self.update_combo(dt)

        self.player.update(dt, keys)
        if keys[pygame.K_SPACE]:
            self.player.shoot(self.bullets, self.sound)

        self.maybe_spawn_enemy(dt)
        self.maybe_spawn_powerup(dt)

        for pu in self.powerups: pu.update(dt)
        self.powerups = [p for p in self.powerups if not p.dead]

        for e in self.enemies: e.update(dt, self)

        for b in self.bullets: b.update(dt)
        self.bullets = [b for b in self.bullets if not b.dead]

        # friendly bullets -> enemies
        for b in list(self.bullets):
            if not b.friendly: continue
            for e in list(self.enemies):
                if b.collides_circle(e.pos, e.radius):
                    e.hit(10, self.sound)
                    b.life = 0
                    self.add_shake(2.0)
                    if FEATURES["PARTICLES"]:
                        self.particles.append(Particle(b.pos, (random.uniform(-90, 90), random.uniform(-90, 90)), life=0.25, radius=3, color=(220, 240, 255)))
                    if e.hp <= 0:
                        self.enemy_killed(e)
                        if isinstance(e, Boss):
                            self.boss_active = False
                            self.score += 120 * self.score_mult()
                            self.sound.play("boom")
                            self.add_shake(12.0)
                        self.enemies.remove(e)
                    break

        # enemy bullets -> player
        for b in list(self.bullets):
            if b.friendly: continue
            if b.collides_circle(self.player.pos, self.player.radius):
                b.life = 0
                self.player.take_damage(18, self.sound)
                self.add_shake(10.0)
                if FEATURES["PARTICLES"]:
                    for _ in range(12):
                        self.particles.append(Particle(self.player.pos, (random.uniform(-240, 240), random.uniform(-240, 240)), life=0.45, radius=3, color=(255, 150, 150)))

        # ram collisions
        for e in list(self.enemies):
            if self.player.pos.distance_to(e.pos) <= (self.player.radius + e.radius):
                self.player.take_damage(24, self.sound)
                self.add_shake(12.0)
                if not isinstance(e, Boss):
                    self.enemies.remove(e)
                if FEATURES["COMBO"]:
                    self.combo_kills = 0
                    self.combo_timer = 0.0
                break

        # powerup pickup
        for pu in list(self.powerups):
            if self.player.pos.distance_to(pu.pos) <= (self.player.radius + pu.radius):
                self.apply_powerup(pu)
                self.powerups.remove(pu)

        if not self.player.alive:
            self.state = self.GAMEOVER
            self.high = max(self.high, self.score)
            save_highscore(self.high)

    def shake_offset(self):
        if not (FEATURES["SCREEN_SHAKE"] and self.shake > 0): return (0, 0)
        mag = self.shake
        return (random.uniform(-mag, mag), random.uniform(-mag, mag))

    def draw_hud(self, surf, font):
        surf.blit(font.render(f"Score: {self.score}", True, (240, 240, 245)), (16, 14))
        surf.blit(font.render(f"High: {self.high}", True, (180, 180, 190)), (16, 40))
        if FEATURES["WAVES"]:
            surf.blit(font.render(f"Wave: {self.wave}", True, (210, 220, 240)), (16, 66))

        x, y = 16, 94
        bar_w, bar_h = 220, 12
        pygame.draw.rect(surf, (40, 40, 60), (x, y, bar_w, bar_h), border_radius=6)
        frac = clamp(self.player.hp / PLAYER_MAX_HP, 0, 1)
        pygame.draw.rect(surf, (220, 220, 245), (x, y, int(bar_w * frac), bar_h), border_radius=6)
        surf.blit(font.render("HP", True, (200, 200, 210)), (x + bar_w + 10, y - 2))

        if self.player.shield > 0:
            sy = y + 18
            pygame.draw.rect(surf, (40, 40, 60), (x, sy, bar_w, 10), border_radius=6)
            sfrac = clamp(self.player.shield / SHIELD_HP, 0, 1)
            pygame.draw.rect(surf, (110, 190, 255), (x, sy, int(bar_w * sfrac), 10), border_radius=6)
            surf.blit(font.render("SHIELD", True, (180, 210, 240)), (x + bar_w + 10, sy - 4))

        pt = []
        if self.player.rapid_time > 0: pt.append(f"RAPID {self.player.rapid_time:0.1f}s")
        if self.player.spread_time > 0: pt.append(f"SPREAD {self.player.spread_time:0.1f}s")
        if pt:
            surf.blit(font.render(" | ".join(pt), True, (220, 240, 220)), (16, 130))

        if FEATURES["COMBO"] and self.combo_kills > 0:
            surf.blit(font.render(f"Combo: {self.combo_kills}  x{self.score_mult()}", True, (255, 235, 160)), (WIDTH - 220, 16))

    def draw_overlays(self, surf, font, bigfont):
        if self.state == self.MENU:
            self._center(surf, bigfont, "SPACE SHOOTER", 160)
            self._center(surf, font, "1=Easy  2=Normal  3=Hard   |   ENTER to Start", 225)
            self._center(surf, font, "Move: WASD/Arrows | Shoot: SPACE (hold) | Shift: Slow | P: Pause", 255)
            self._center(surf, font, "Power-ups: Rapid / Spread / Shield / Heal", 285)
            self._center(surf, font, "Boss appears every few waves (if enabled).", 315)
        elif self.state == self.PAUSED:
            self._center(surf, bigfont, "PAUSED", 210)
            self._center(surf, font, "Press P to resume", 260)
        elif self.state == self.GAMEOVER:
            self._center(surf, bigfont, "GAME OVER", 200)
            self._center(surf, font, f"Score: {self.score}   High: {self.high}", 255)
            self._center(surf, font, "Press R to restart or ESC to quit", 285)

        if FEATURES["WAVES"] and self.wave_banner > 0 and self.state == self.PLAYING:
            txt = font.render(f"Wave {self.wave}", True, (250, 250, 255))
            rect = txt.get_rect(center=(WIDTH // 2, 80))
            bg = pygame.Surface((rect.width + 28, rect.height + 16), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 120))
            surf.blit(bg, (rect.x - 14, rect.y - 8))
            surf.blit(txt, rect)

        if self.boss_warning > 0 and self.state == self.PLAYING:
            txt = font.render("WARNING: BOSS INCOMING", True, (255, 220, 220))
            rect = txt.get_rect(center=(WIDTH // 2, 110))
            bg = pygame.Surface((rect.width + 28, rect.height + 16), pygame.SRCALPHA)
            bg.fill((50, 0, 0, 120))
            surf.blit(bg, (rect.x - 14, rect.y - 8))
            surf.blit(txt, rect)

    @staticmethod
    def _center(surf, font, text, y):
        s = font.render(text, True, (245, 245, 250))
        surf.blit(s, s.get_rect(center=(WIDTH // 2, y)))

    def draw(self, screen, font, bigfont):
        offset = self.shake_offset()
        screen.fill((16, 18, 28))
        for s in self.stars: s.draw(screen, offset)
        for pu in self.powerups: pu.draw(screen, offset)
        for e in self.enemies: e.draw(screen, offset)
        for b in self.bullets: b.draw(screen, offset)
        self.player.draw(screen, offset)
        if FEATURES["PARTICLES"]:
            for p in self.particles: p.draw(screen, offset)
        self.draw_hud(screen, font)
        self.draw_overlays(screen, font, bigfont)

def main():
    pygame.init()
    flags = 0
    if FEATURES["FULLSCREEN"]:
        flags = pygame.FULLSCREEN | pygame.SCALED
    pygame.display.set_caption("Space Shooter ")
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    bigfont = pygame.font.Font(None, 60)
    sound = SoundManager(FEATURES["SOUNDS"])
    game = Game(sound)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        keys = pygame.key.get_pressed()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if game.state == Game.MENU:
                    if event.key == pygame.K_1: game.difficulty = "Easy"
                    elif event.key == pygame.K_2: game.difficulty = "Normal"
                    elif event.key == pygame.K_3: game.difficulty = "Hard"
                    elif event.key == pygame.K_RETURN: game.reset_run()
                elif game.state == Game.PLAYING:
                    if event.key == pygame.K_p: game.state = Game.PAUSED
                elif game.state == Game.PAUSED:
                    if event.key == pygame.K_p: game.state = Game.PLAYING
                elif game.state == Game.GAMEOVER:
                    if event.key == pygame.K_r: game.reset_run()

        game.update(dt, keys)
        game.draw(screen, font, bigfont)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
