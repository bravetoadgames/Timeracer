from ursina import *
from ursina.shaders import lit_with_shadows_shader
import time

app = Ursina()

# --- SETTINGS ---
window.title = 'PolyTrack 3D - Pro Editor Mode'
window.borderless = False
window.color = color.black

# --- LICHT ---
sun = DirectionalLight()
sun.look_at(Vec3(1, -1, -1))
AmbientLight(color=color.rgba(120, 120, 120, 255))

# --- GAME STATE ---
mode = 'race' 
selected_type = 'road'
tiles = {}
race_start_time = time.time()
race_finished = False

# --- DE AUTO ---
player = Entity(position=(0, 2, 0), model=None, collider='box')

def create_car_part(model, color, scale, position=(0,0,0), rotation=(0,0,0)):
    return Entity(parent=player, model=model, color=color, scale=scale, 
                  position=position, rotation=rotation, shader=lit_with_shadows_shader)

car_body = create_car_part('cube', color.azure, (1.4, 0.4, 2.5), position=(0, 0.2, 0))
car_cockpit = create_car_part('prism', color.cyan, (1.0, 0.5, 0.8), position=(0, 0.6, 0.2), rotation=(-10,0,0))
create_car_part('cube', color.azure, (1.6, 0.1, 0.5), position=(0, 0.7, -1.0))
w_front_l = create_car_part('cube', color.black, (0.35, 0.6, 0.6), position=(-0.9, 0.1, 0.8))
w_front_r = create_car_part('cube', color.black, (0.35, 0.6, 0.6), position=(0.9, 0.1, 0.8))
w_back_l = create_car_part('cube', color.black, (0.35, 0.6, 0.6), position=(-0.9, 0.1, -0.8))
w_back_r = create_car_part('cube', color.black, (0.35, 0.6, 0.6), position=(0.9, 0.1, -0.8))

speed = 0
max_speed = 55
acceleration = 35
rotation_speed = 140

# --- EDITOR ELEMENTS ---
cursor = Entity(model='cube', color=color.rgba(255,255,255,100), scale=(4, 0.1, 4), shader=lit_with_shadows_shader, enabled=False)
editor_cam_base = Entity() # Dummy entity voor camera translatie

def place_tile(pos, tile_type):
    # Snapping naar grid (4x4)
    grid_pos = Vec3(round(pos.x / 4) * 4, 0, round(pos.z / 4) * 4)
    
    # Voorkom dat we de onzichtbare grond zelf proberen te vervangen
    if grid_pos in tiles: 
        destroy(tiles[grid_pos])
    
    c = color.gray
    if tile_type == 'start': c = color.green
    if tile_type == 'finish': c = color.red
    
    tiles[grid_pos] = Entity(
        model='cube', 
        position=grid_pos, 
        scale=(4, 0.5, 4), 
        color=c, 
        collider='box', 
        shader=lit_with_shadows_shader
    )
    
def build_default():
    for i in range(5): place_tile(Vec3(0,0,i*4), 'start' if i==0 else 'road')
    place_tile(Vec3(4,0,16), 'road'); place_tile(Vec3(8,0,16), 'finish')
build_default()

# --- UI ---
info = Text(text='TAB: Mode | 1-3: Type | R: Reset | RMuis: Draai | WASD: Vlieg', position=(-0.85, 0.45), scale=0.7)
mode_text = Text(text='MODE: RACE', position=(-0.85, 0.40), color=color.azure)
timer_text = Text(text='0.00', position=(0, 0.45), origin=(0,0), scale=2)
finish_msg = Text(text='', position=(0, 0.1), origin=(0,0), scale=2, color=color.yellow)

def reset_player():
    global speed, race_start_time, race_finished
    player.position, player.rotation, speed = (0, 2, 0), (0, 0, 0), 0
    w_front_l.rotation_y = w_front_r.rotation_y = 0
    finish_msg.text = ''
    race_start_time, race_finished = time.time(), False

def input(key):
    global mode, selected_type
    
    if key == 'tab':
        mode = 'editor' if mode == 'race' else 'race'
        mode_text.text = f'MODE: {mode.upper()}'
        mode_text.color = color.orange if mode == 'editor' else color.azure
        
        if mode == 'race':
            camera.parent = player
            camera.position, camera.rotation = (0, 8, -18), (20, 0, 0)
            cursor.enabled = False
            mouse.locked = True
        else:
            camera.parent = render
            camera.position = player.position + Vec3(0, 20, -20)
            camera.rotation_x = 30
            cursor.enabled = True
            mouse.locked = False

    if mode == 'editor':
        if key == '1': selected_type = 'road'
        if key == '2': selected_type = 'start'
        if key == '3': selected_type = 'finish'
        if key == 'left mouse down' and mouse.world_point: 
            place_tile(mouse.world_point, selected_type)
        if key == 'right mouse down':
            mouse.locked = True # Lock voor vrij draaien
        if key == 'right mouse up':
            mouse.locked = False

    if key == 'r': reset_player()

# Start Settings
mouse.locked = True
camera.parent = player
camera.position, camera.rotation_x = (0, 8, -18), 20

def update():
    global speed, race_finished
    dt = time.dt
    
    if mode == 'race':
        if not race_finished:
            timer_text.text = f'{time.time() - race_start_time:.2f}'
        
        move_input = held_keys['w'] - held_keys['s']
        speed += move_input * acceleration * dt
        if move_input == 0: speed = lerp(speed, 0, dt * 2)
        speed = clamp(speed, -max_speed/2, max_speed)

        if abs(speed) > 0.1:
            steer = held_keys['d'] - held_keys['a']
            player.rotation_y += steer * rotation_speed * dt * (speed / max_speed)
            w_front_l.rotation_y = w_front_r.rotation_y = steer * 25

        player.position += player.forward * speed * dt

        ray = raycast(player.world_position + (0, 2, 0), (0, -1, 0), distance=5, ignore=(player, cursor))
        if ray.hit:
            player.y = lerp(player.y, ray.world_point.y + 0.1, dt * 15)
            if ray.entity and ray.entity.color == color.red and not race_finished:
                race_finished = True
                finish_msg.text = 'FINISH!'
        else:
            player.y -= 25 * dt
        if player.y < -30: reset_player()

    else: # EDITOR MODE
        # 1. Camera Rotatie (alleen met rechtermuisknop)
        if held_keys['right mouse']:
            camera.rotation_x -= mouse.velocity[1] * 40
            camera.rotation_y += mouse.velocity[0] * 40
        
        # 2. Camera Beweging (WASD + QE)
        cam_speed = 25 * dt
        if held_keys['shift']: cam_speed *= 2 # Turbo mode
        
        camera.position += camera.forward * (held_keys['w'] - held_keys['s']) * cam_speed
        camera.position += camera.right * (held_keys['d'] - held_keys['a']) * cam_speed
        camera.position += camera.up * (held_keys['e'] - held_keys['q']) * cam_speed

        # 3. Cursor op grid
        if mouse.world_point:
            cursor.position = Vec3(round(mouse.world_point.x / 4) * 4, 0.3, round(mouse.world_point.z / 4) * 4)

app.run()