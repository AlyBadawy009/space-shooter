# Space Shooter — Full Features Toggleable


## How to Run the game:
```Open CMD in folder and type:

        pip install -r requirements.txt
        python main.py
```

## Controls
- Move: WASD / Arrow keys
- Shoot: SPACE (hold)
- Slow move: Left SHIFT
- Pause/Resume: P
- Restart: R
- Menu: 1/2/3 difficulty, ENTER to start
- Quit: ESC

## Feature toggles (easy ON/OFF)
At the top of `main.py`:
```python
FEATURES = {
    "WAVES": True,
    "BOSS": True,
    "POWERUPS": True,
    "COMBO": True,
    "HEALTH": True,
    "PARTICLES": True,
    "SCREEN_SHAKE": True,
    "SOUNDS": True,
    "FULLSCREEN": False,
}
```

## Most important tuning variables
- Player: PLAYER_SPEED, PLAYER_MAX_HP, PLAYER_IFRAMES
- Shooting: BULLET_SPEED, FIRE_COOLDOWN
- Enemies: ENEMY_BASE_SPEED, ENEMY_SPAWN_BASE, ENEMY_HP
- Waves: WAVE_DURATION, BOSS_EVERY_WAVES
- Boss: BOSS_HP, BOSS_FIRE_COOLDOWN
- Powerups: POWERUP_DURATION, SHIELD_HP
- Combo: COMBO_WINDOW, COMBO_STEP, MAX_MULTIPLIER
- FX: SHAKE_DECAY, PARTICLE_LIFE
