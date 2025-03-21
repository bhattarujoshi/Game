import pygame
import os
import random
import time
import json
import math
# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Constants (unchanged)
GRID_SIZE = 10
TILE_SIZE = 60
FPS = 60
VISION_RADIUS = 2
UI_WIDTH = 250
MOVE_DELAY = 10
RESOURCE_GENERATION_INTERVAL = 5
GOLD_GENERATION_AMOUNT = 1
WOOD_GENERATION_AMOUNT = 1

# Colors (unchanged)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
LIGHT_GRAY = (230, 230, 230)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
HOVER_COLOR = (180, 180, 255)
GOLD_COLOR = (255, 215, 0)
WOOD_COLOR = (139, 69, 19)

# Global sprite variables (unchanged)
stone_sprite = None
bomb_sprite = None
spike_sprite = None

# Score history file path (unchanged)
SCORE_FILE = os.path.join(os.path.dirname(__file__), "score_history.json")

# Global variables
score_history = []
MAX_HISTORY = 5
particles = []
dialogue_active = False
dialogue_alpha = 255
DIALOGUE_FADE_SPEED = 2
modes = ["Easy", "Medium", "Hard"]
selected_mode = None
obstacles = {}
OBSTACLE_TYPES = ["Stone", "Bomb", "Spike"]

# New constants for obstacle penalties
BASE_PENALTIES = {
    "Stone": {"initial": 10, "continuous": 5},  # Base points deducted
    "Bomb": {"initial": 20, "continuous": 10},
    "Spike": {"initial": 30, "continuous": 15}
}
MODE_MULTIPLIERS = {"Easy": 0.5, "Medium": 1.0, "Hard": 1.5}  # Difficulty multipliers
OBSTACLE_CHECK_INTERVAL = 2.0  # Deduct points every 2 seconds

# New global variables to track obstacle contact time
player1_last_obstacle_deduction = 0
player2_last_obstacle_deduction = 0
player1_on_obstacle = False
player2_on_obstacle = False

def load_score_history():
    global score_history
    try:
        with open(SCORE_FILE, 'r') as f:
            score_history = json.load(f)
            if len(score_history) > MAX_HISTORY:
                score_history = score_history[-MAX_HISTORY:]
    except (FileNotFoundError, json.JSONDecodeError):
        score_history = []

load_score_history()

ASSET_DIR = os.path.join(os.path.dirname(__file__), "assets")
SOUND_DIR = os.path.join(ASSET_DIR, "sounds")


def setup_screen():
    global screen, WIDTH, HEIGHT, background_image, ui_background_image, game_finish_background
    WIDTH = GRID_SIZE * TILE_SIZE + UI_WIDTH
    HEIGHT = GRID_SIZE * TILE_SIZE
    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Two Player RTS Game")
    print(f"Screen initialized with size: {WIDTH}x{HEIGHT}")

    try:
        background_image = pygame.image.load(os.path.join(ASSET_DIR, "default_background.png")).convert()
        background_image = pygame.transform.smoothscale(background_image, (WIDTH, HEIGHT))
        print("Background image loaded successfully")
    except pygame.error as e:
        print(f"Error loading background image: {e}")
        background_image = pygame.Surface((WIDTH, HEIGHT))
        background_image.fill(BLACK)
        print("Using fallback black background")

    try:
        ui_background_image = pygame.image.load(os.path.join(ASSET_DIR, "new_ui_background1.png")).convert()
        ui_background_image = pygame.transform.smoothscale(ui_background_image, (UI_WIDTH, HEIGHT))
        print("UI background image loaded successfully")
    except pygame.error as e:
        print(f"Error loading UI background image: {e}")
        ui_background_image = pygame.Surface((UI_WIDTH, HEIGHT))
        ui_background_image.fill(LIGHT_GRAY)
        print("Using fallback light gray UI background")

    try:
        game_finish_background = pygame.image.load(os.path.join(ASSET_DIR, "game_finish_background.png")).convert()
        game_finish_background = pygame.transform.smoothscale(game_finish_background, (WIDTH, HEIGHT))
        print("Game finish background image loaded successfully")
    except pygame.error as e:
        print(f"Error loading game finish background image: {e}")
        game_finish_background = pygame.Surface((WIDTH, HEIGHT))
        game_finish_background.fill(BLACK)
        print("Using fallback black game finish background")

    return screen

screen = setup_screen()



# Load obstacle sprites
try:
    stone_sprite = pygame.image.load(os.path.join(ASSET_DIR, "stone.png")).convert_alpha()
    stone_sprite = pygame.transform.scale(stone_sprite, (TILE_SIZE, TILE_SIZE))
    bomb_sprite = pygame.image.load(os.path.join(ASSET_DIR, "bomb.png")).convert_alpha()
    bomb_sprite = pygame.transform.scale(bomb_sprite, (TILE_SIZE, TILE_SIZE))
    spike_sprite = pygame.image.load(os.path.join(ASSET_DIR, "spike.png")).convert_alpha()
    spike_sprite = pygame.transform.scale(spike_sprite, (TILE_SIZE, TILE_SIZE))
except pygame.error as e:
    print(f"Error loading obstacle sprites: {e}")
    stone_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
    stone_sprite.fill((100, 100, 100))
    bomb_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
    bomb_sprite.fill((255, 0, 0))
    spike_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
    spike_sprite.fill((150, 0, 150))

# Background Music
background_music = os.path.join(SOUND_DIR, "background_music.mp3")

# Sound Effects with error handling
try:
    resource_collect_sound = pygame.mixer.Sound(os.path.join(SOUND_DIR, "collect.wav"))
    move_sound = pygame.mixer.Sound(os.path.join(SOUND_DIR, "move.wav"))
    button_click_sound = pygame.mixer.Sound(os.path.join(SOUND_DIR, "button_click.wav"))
    game_over_sound = pygame.mixer.Sound(os.path.join(SOUND_DIR, "game_over.wav"))
    start_game_sound = pygame.mixer.Sound(os.path.join(SOUND_DIR, "start.wav"))
    build_sound = pygame.mixer.Sound(os.path.join(SOUND_DIR, "build.wav"))
except pygame.error as e:
    print(f"Error loading sound: {e}")
    resource_collect_sound = move_sound = button_click_sound = game_over_sound = start_game_sound = build_sound = pygame.mixer.Sound(pygame.mixer.Sound(buffer=b'\x00' * 1024))

# Set volume
resource_collect_sound.set_volume(0.7)
move_sound.set_volume(0.3)
button_click_sound.set_volume(0.6)
game_over_sound.set_volume(0.1)
start_game_sound.set_volume(0.7)
build_sound.set_volume(0.5)

# Load and scale sprites with error handling
try:
    player1_sprite = pygame.image.load(os.path.join(ASSET_DIR, "player1.png")).convert_alpha()
    player1_sprite = pygame.transform.scale(player1_sprite, (TILE_SIZE, TILE_SIZE))
except pygame.error as e:
    print(f"Error loading player1 sprite: {e}")
    player1_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
    player1_sprite.fill(BLUE)

try:
    player2_sprite = pygame.image.load(os.path.join(ASSET_DIR, "player2.png")).convert_alpha()
    player2_sprite = pygame.transform.scale(player2_sprite, (TILE_SIZE, TILE_SIZE))
except pygame.error as e:
    print(f"Error loading player2 sprite: {e}")
    player2_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
    player2_sprite.fill(RED)

try:
    background_image = pygame.image.load(os.path.join(ASSET_DIR, "default_background.png")).convert()
    background_image = pygame.transform.scale(background_image, (screen.get_width(), screen.get_height()))
except pygame.error as e:
    print(f"Error loading background image: {e}")
    background_image = pygame.Surface((screen.get_width(), screen.get_height()))
    background_image.fill(BLACK)

try:
    ui_background_image = pygame.image.load(os.path.join(ASSET_DIR, "new_ui_background1.png")).convert()
    ui_background_image = pygame.transform.scale(ui_background_image, (UI_WIDTH, HEIGHT))
except pygame.error as e:
    print(f"Error loading UI background image: {e}")
    ui_background_image = pygame.Surface((UI_WIDTH, HEIGHT))
    ui_background_image.fill(LIGHT_GRAY)

try:
    game_finish_background = pygame.image.load(os.path.join(ASSET_DIR, "game_finish_background.png")).convert()
    game_finish_background = pygame.transform.scale(game_finish_background, (screen.get_width(), screen.get_height()))
except pygame.error as e:
    print(f"Error loading game finish background image: {e}")
    game_finish_background = pygame.Surface((screen.get_width(), screen.get_height()))
    game_finish_background.fill(BLACK)

try:
    gold_mine_sprite = pygame.image.load(os.path.join(ASSET_DIR, "gold_mine.png")).convert_alpha()
    gold_mine_sprite = pygame.transform.scale(gold_mine_sprite, (TILE_SIZE, TILE_SIZE))
    lumber_mill_sprite = pygame.image.load(os.path.join(ASSET_DIR, "lumber_mill.png")).convert_alpha()
    lumber_mill_sprite = pygame.transform.scale(lumber_mill_sprite, (TILE_SIZE, TILE_SIZE))
except pygame.error as e:
    print(f"Error loading building sprites: {e}")
    gold_mine_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
    gold_mine_sprite.fill(GOLD_COLOR)
    lumber_mill_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
    lumber_mill_sprite.fill(WOOD_COLOR)

try:
    game_rule_button_image = pygame.image.load(os.path.join(ASSET_DIR, "generic_button.png")).convert_alpha()
    game_rule_button_image = pygame.transform.smoothscale(game_rule_button_image, (100, 50))
except pygame.error as e:
    print(f"Error loading game rule button image: {e}")
    game_rule_button_image = pygame.Surface((100, 50))
    game_rule_button_image.fill(GRAY)

def load_resource_sprites():
    global gold_sprite, wood_sprite
    try:
        gold_sprite = pygame.image.load(os.path.join(ASSET_DIR, "gold.png"))
        gold_sprite = pygame.transform.scale(gold_sprite, (TILE_SIZE, TILE_SIZE))
        wood_sprite = pygame.image.load(os.path.join(ASSET_DIR, "wood.png"))
        wood_sprite = pygame.transform.scale(wood_sprite, (TILE_SIZE, TILE_SIZE))
    except Exception as e:
        print(f"Error loading resource sprites: {e}")
        gold_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
        gold_sprite.fill(GOLD_COLOR)
        wood_sprite = pygame.Surface((TILE_SIZE, TILE_SIZE))
        wood_sprite.fill(WOOD_COLOR)

load_resource_sprites()

try:
    grid_texture = pygame.image.load(os.path.join(ASSET_DIR, "ground_tile1.png")).convert()
    grid_texture = pygame.transform.scale(grid_texture, (TILE_SIZE, TILE_SIZE))
except pygame.error as e:
    print(f"Error loading grid texture: {e}")
    grid_texture = pygame.Surface((TILE_SIZE, TILE_SIZE))
    grid_texture.fill(GRAY)

# Load generic button image for mode selection
try:
    generic_button_image = pygame.image.load(os.path.join(ASSET_DIR, "generic_button.png")).convert_alpha()
    generic_button_image = pygame.transform.scale(generic_button_image, (100, 50))  # Ensure 100x50 pixels
except pygame.error as e:
    print(f"Error loading generic button image: {e}")
    generic_button_image = pygame.Surface((100, 50))
    generic_button_image.fill(GRAY)

# Load timer images
try:
    timer_30s_image = pygame.image.load(os.path.join(ASSET_DIR, "timer_30s.png")).convert_alpha()
    timer_30s_image = pygame.transform.scale(timer_30s_image, (100, 50))
    timer_60s_image = pygame.image.load(os.path.join(ASSET_DIR, "timer_60s.png")).convert_alpha()
    timer_60s_image = pygame.transform.scale(timer_60s_image, (100, 50))
    timer_90s_image = pygame.image.load(os.path.join(ASSET_DIR, "timer_90s.png")).convert_alpha()
    timer_90s_image = pygame.transform.scale(timer_90s_image, (100, 50))
except pygame.error as e:
    print(f"Error loading timer images: {e}")
    timer_30s_image = pygame.Surface((100, 50))
    timer_30s_image.fill((100, 100, 200))
    timer_60s_image = pygame.Surface((100, 50))
    timer_60s_image.fill((100, 200, 100))
    timer_90s_image = pygame.Surface((100, 50))
    timer_90s_image.fill((200, 100, 100))

# Global game state
# Global game state (unchanged)
# Global game state (unchanged)
game_state = {
    "screen": "start",
    "timer": 0,
    "start_time": 0,
    "remaining_time": 0,
    "game_duration": 0,
    "last_resource_generation": 0,
    "last_building_generation": 0,
    "selected_duration": 0,
    "previous_screen": None,
    "selected_mode": None
}

# Global player positions and resources
player1_pos = [0, 0]
player2_pos = [0, 0]
player1_target = [0, 0]
player2_target = [0, 0]
resources = {}
player1_resources = {"Gold": 0, "Wood": 0, "Points": 0}
player2_resources = {"Gold": 0, "Wood": 0, "Points": 0}
buildings = {}

def reset_game():
    global player1_pos, player2_pos, player1_target, player2_target, resources, player1_resources, player2_resources, buildings, obstacles, selected_mode
    player1_pos = [random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)]
    player2_pos = [random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)]
    player1_target = list(player1_pos)
    player2_target = list(player2_pos)

    resources = {}
    player1_resources = {"Gold": 0, "Wood": 0, "Points": 0}
    player2_resources = {"Gold": 0, "Wood": 0, "Points": 0}
    buildings = {}
    obstacles = {}

    for _ in range(5):
        x, y = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
        resources[(x, y)] = {"type": "Gold", "amount": 1}
    for _ in range(5):
        x, y = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
        resources[(x, y)] = {"type": "Wood", "amount": 1}

    selected_mode = game_state["selected_mode"]
    if selected_mode == "Medium":
        for _ in range(3):
            while True:
                x, y = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
                if (x, y) not in resources and (x, y) not in buildings and [x, y] != player1_pos and [x, y] != player2_pos:
                    obstacles[(x, y)] = random.choice(OBSTACLE_TYPES)
                    break
    elif selected_mode == "Hard":
        for _ in range(5):
            while True:
                x, y = random.randint(0, GRID_SIZE - 1), random.randint(0, GRID_SIZE - 1)
                if (x, y) not in resources and (x, y) not in buildings and [x, y] != player1_pos and [x, y] != player2_pos:
                    obstacles[(x, y)] = random.choice(OBSTACLE_TYPES)
                    break

    game_state['last_resource_generation'] = time.time()
    game_state['last_building_generation'] = time.time()

# Reset button states to initial configuration
def reset_button_states():
    global start_button, close_button
    start_button.text = " "
    start_button.image = start_button_image
    # Close button should not be drawn on the initial start screen
    close_button.text = " "
    close_button.image = close_button_image  # Keep it defined but don't draw it initially

class ResponsiveButton:
    def __init__(self, x_ratio, y_ratio, width_ratio, height_ratio, text, image, text_color=WHITE, text_opacity=255):
        self.x_ratio = x_ratio
        self.y_ratio = y_ratio
        self.width_ratio = width_ratio
        self.height_ratio = height_ratio
        self.text = text
        self.image = image
        self.text_color = text_color
        self.text_opacity = text_opacity
        self.is_selected = False
        self.is_hover = False
        self.rect = None
        self.font = None

    def render_text(self, screen, font):
        text_surface = font.render(self.text, True, self.text_color)
        text_surface.set_alpha(self.text_opacity)
        text_rect = text_surface.get_rect(center=self.rect.center)  # Center text within the button
        screen.blit(text_surface, text_rect)

    def update_rect(self, screen_width, screen_height):
        # Use self. to access instance variables
        x = int(screen_width * self.x_ratio)
        y = int(screen_height * self.y_ratio)
        width = int(screen_width * self.width_ratio)
        height = int(screen_height * self.height_ratio)
        self.rect = pygame.Rect(x, y, width, height)
        # Dynamically adjust font size to fit the button height, with a cap
        font_size = min(max(20, int(height * 0.6)), 30)  # Range: 20 to 30 pixels
        self.font = pygame.font.Font(None, font_size)

    def draw(self, surface):
        if not self.rect:
            self.update_rect(surface.get_width(), surface.get_height())
        # Scale image to match the button rect dimensions
        scaled_image = pygame.transform.scale(self.image, (self.rect.width, self.rect.height))
        surface.blit(scaled_image, self.rect)
        self.render_text(surface, self.font)

    def is_clicked(self, pos):
        return self.rect and self.rect.collidepoint(pos)

    def handle_hover(self, pos):
        self.is_hover = self.rect and self.rect.collidepoint(pos)

# Load button images
start_button_image = pygame.image.load(os.path.join(ASSET_DIR, "start_icon.png")).convert_alpha()
start_button_image = pygame.transform.scale(start_button_image, (100, 50))
close_button_image = pygame.image.load(os.path.join(ASSET_DIR, "close_icon.png")).convert_alpha()
close_button_image = pygame.transform.scale(close_button_image, (100, 50))
replay_button_image = pygame.image.load(os.path.join(ASSET_DIR, "replay_icon.png")).convert_alpha()
replay_button_image = pygame.transform.scale(replay_button_image, (100, 50))
history_button_image = pygame.image.load(os.path.join(ASSET_DIR, "history_icon.png")).convert_alpha()
history_button_image = pygame.transform.scale(history_button_image, (50, 50))

# Initialize buttons (updated game_rule_button position)
start_button = ResponsiveButton(0.3, 0.7, 0.2, 0.1, " ", start_button_image)
close_button = ResponsiveButton(0.55, 0.7, 0.2, 0.1, " ", close_button_image)
timer_buttons = [
    ResponsiveButton(0.3, 0.5, 0.15, 0.1, "30s", timer_30s_image, text_opacity=0),
    ResponsiveButton(0.45, 0.5, 0.15, 0.1, "60s", timer_60s_image, text_opacity=0),
    ResponsiveButton(0.6, 0.5, 0.15, 0.1, "90s", timer_90s_image, text_opacity=0)
]
history_button = ResponsiveButton(0.9, 0.05, 0.08, 0.08, " ", history_button_image)  # Top right
game_rule_button = ResponsiveButton(0.05, 0.05, 0.08, 0.08, "Game Rules", game_rule_button_image, text_opacity=255, text_color=WHITE)  # Top left

def draw_grid():
    for x in range(GRID_SIZE):
        for y in range(GRID_SIZE):
            screen.blit(grid_texture, (x * TILE_SIZE, y * TILE_SIZE))
            if (y, x) in resources:
                resource = resources[(y, x)]
                resource_sprite = gold_sprite if resource['type'] == 'Gold' else wood_sprite
                screen.blit(resource_sprite, (x * TILE_SIZE, y * TILE_SIZE))
            if (y, x) in buildings:
                building = buildings[(y, x)]
                building_sprite = gold_mine_sprite if building['type'] == 'Gold Mine' else lumber_mill_sprite
                screen.blit(building_sprite, (x * TILE_SIZE, y * TILE_SIZE))
            if (y, x) in obstacles:
                obstacle_type = obstacles[(y, x)]
                obstacle_sprite = (
                    stone_sprite if obstacle_type == "Stone" else
                    bomb_sprite if obstacle_type == "Bomb" else
                    spike_sprite
                )
                screen.blit(obstacle_sprite, (x * TILE_SIZE, y * TILE_SIZE))
    

def draw_units():
    screen.blit(player1_sprite, (player1_pos[0] * TILE_SIZE, player1_pos[1] * TILE_SIZE))
    screen.blit(player2_sprite, (player2_pos[0] * TILE_SIZE, player2_pos[1] * TILE_SIZE))

# New function to draw the game rule screen
def draw_game_rule_screen():
    screen.blit(background_image, (0, 0))
    title_font = pygame.font.Font(None, int(HEIGHT * 0.1))
    title = title_font.render("Game Rules", True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 10)))

    # Define the rules text
    rules_font = pygame.font.Font(None, int(HEIGHT * 0.03))
    rules_text = [
        "Welcome to Two Player RTS Game!",
        "Objective: Collect resources (Gold and Wood), build structures, and earn points to outscore your opponent within the time limit.",
        "Controls:",
        "  - Blue Player (1P):",
        "    - Move: Arrow Keys",
        "    - Upgrade Resource Generation: 1",
        "    - Upgrade Movement Speed: 2",
        "    - Upgrade Vision Radius: 3",
        "    - Build Gold Mine: 4",
        "    - Build Lumber Mill: 5",
        "  - Red Player (2P):",
        "    - Move: W, A, S, D",
        "    - Upgrade Resource Generation: 7",
        "    - Upgrade Movement Speed: 8",
        "    - Upgrade Vision Radius: 9",
        "    - Build Gold Mine: I",
        "    - Build Lumber Mill: O",
        "Resources:",
        "  - Gold: Collected from the map or generated by Gold Mines (50 points each).",
        "  - Wood: Collected from the map or generated by Lumber Mills (30 points each).",
        "Buildings:",
        "  - Gold Mine: Costs 10 Gold, generates 1 Gold every 5 seconds.",
        "  - Lumber Mill: Costs 10 Wood, generates 1 Wood every 5 seconds.",
        "Upgrades: Use Gold to improve Resource Generation, Movement Speed, or Vision Radius (max 5, 3, 3 levels).",
        "Obstacles:",
        "  - Stone: Initial 10 points loss, 5 points every 2 seconds.",
        "  - Bomb: Initial 20 points loss, 10 points every 2 seconds.",
        "  - Spike: Initial 30 points loss, 15 points every 2 seconds.",
        "  - Penalties scale with difficulty (Easy: 0.5x, Medium: 1x, Hard: 1.5x).",
        "Winning: The player with the most points when time runs out wins. A draw occurs if points are equal."
    ]

    # Draw rules text in a scrollable box
    box_width = WIDTH - 100
    box_height = HEIGHT - 150
    box_x = (WIDTH - box_width) // 2
    box_y = HEIGHT // 5
    rule_box = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
    rule_box.fill((50, 50, 50, 200))  # Semi-transparent background
    pygame.draw.rect(rule_box, WHITE, (0, 0, box_width, box_height), 2)  # Border

    y_offset = 20
    for line in rules_text:
        text = rules_font.render(line, True, WHITE)
        if y_offset + text.get_height() <= box_height - 20:
            rule_box.blit(text, (10, y_offset))
            y_offset += text.get_height() + 5

    screen.blit(rule_box, (box_x, box_y))

    # Back button
    back_button = ResponsiveButton(0.45, 0.85, 0.1, 0.1, "Back", close_button_image, text_opacity=255, text_color=WHITE)
    back_button.update_rect(WIDTH, HEIGHT)
    back_button.draw(screen)
    return back_button


def draw_ui():


    screen.blit(ui_background_image, (GRID_SIZE * TILE_SIZE, 0))
    ui_x = GRID_SIZE * TILE_SIZE
    
    font = pygame.font.Font(None, 36)
    resources_title = font.render("Player Resources", True, WHITE)
    screen.blit(resources_title, resources_title.get_rect(centerx=ui_x + UI_WIDTH // 2, top=50))
    
    blue_title = font.render("Blue Player", True, BLUE)
    screen.blit(blue_title, blue_title.get_rect(centerx=ui_x + UI_WIDTH // 2, top=100))
    screen.blit(font.render(f"Gold: {player1_resources['Gold']}", True, WHITE), (ui_x + UI_WIDTH // 2 - 50, 140))
    screen.blit(font.render(f"Wood: {player1_resources['Wood']}", True, WHITE), (ui_x + UI_WIDTH // 2 - 50, 180))
    screen.blit(font.render(f"Points: {player1_resources['Points']}", True, WHITE), (ui_x + UI_WIDTH // 2 - 50, 220))
    
    red_title = font.render("Red Player", True, RED)
    screen.blit(red_title, red_title.get_rect(centerx=ui_x + UI_WIDTH // 2, top=280))
    screen.blit(font.render(f"Gold: {player2_resources['Gold']}", True, WHITE), (ui_x + UI_WIDTH // 2 - 50, 320))
    screen.blit(font.render(f"Wood: {player2_resources['Wood']}", True, WHITE), (ui_x + UI_WIDTH // 2 - 50, 360))
    screen.blit(font.render(f"Points: {player2_resources['Points']}", True, WHITE), (ui_x + UI_WIDTH // 2 - 50, 400))
    
    if game_state["screen"] == "playing":
        timer_title = font.render("Time Remaining", True, WHITE)
        screen.blit(timer_title, timer_title.get_rect(centerx=ui_x + UI_WIDTH // 2, top=460))
        remaining_time = max(0, int(game_state["game_duration"] - (time.time() - game_state["start_time"])))
        timer_text = font.render(f"{remaining_time} s", True, WHITE)
        screen.blit(timer_text, timer_text.get_rect(centerx=ui_x + UI_WIDTH // 2, top=500))


def draw_tooltip(screen, text, mouse_pos):
    """
    Draws a tooltip near the mouse cursor
    """
    font = pygame.font.Font(None, 24)
    tooltip_text = font.render(text, True, (255, 255, 255))
    tooltip_bg = pygame.Surface((tooltip_text.get_width() + 10, tooltip_text.get_height() + 10))
    tooltip_bg.fill((40, 40, 60))
    pygame.draw.rect(tooltip_bg, (100, 100, 140), tooltip_bg.get_rect(), 2)
    
    # Position the tooltip near the mouse but ensure it stays on screen
    x = mouse_pos[0] + 15
    y = mouse_pos[1] + 15
    
    # Keep tooltip on screen
    if x + tooltip_bg.get_width() > screen.get_width():
        x = screen.get_width() - tooltip_bg.get_width()
    if y + tooltip_bg.get_height() > screen.get_height():
        y = screen.get_height() - tooltip_bg.get_height()
    
    screen.blit(tooltip_bg, (x, y))
    screen.blit(tooltip_text, (x + 5, y + 5))


# Modified draw_start_screen to include close_button
def draw_start_screen():
    # Create a gradient background effect instead of a flat image
    gradient_surface = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        color_value = int(180 * (1 - y / HEIGHT))  # Darkens from top to bottom
        gradient_surface.fill((color_value // 3, color_value // 2, color_value), (0, y, WIDTH, 1))
    
    # Apply the background image with some transparency over the gradient
    screen.blit(gradient_surface, (0, 0))
    temp_bg = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    temp_bg.blit(background_image, (0, 0))
    temp_bg.set_alpha(180)  # Semi-transparent background
    screen.blit(temp_bg, (0, 0))
    
    # Add particle effects in the background
    for particle in particles:
        particle.update()
        particle.draw(screen)
    
    # Create a glowing, animated title
    title_scale = 1.0 + 0.05 * math.sin(pygame.time.get_ticks() / 500)  # Pulsing effect
    title_font = pygame.font.Font(None, int(HEIGHT * 0.1 * title_scale))
    title_shadow = title_font.render("Two Player RTS Game", True, (30, 30, 50))
    title = title_font.render("Two Player RTS Game", True, (220, 220, 255))
    
    # Add shadow effect to the title
    screen.blit(title_shadow, title_shadow.get_rect(center=(WIDTH // 2 + 4, HEIGHT // 4 + 4)))
    screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 4)))
    
    # Add a decorative line under the title
    pygame.draw.line(screen, (150, 150, 255), (WIDTH // 4, HEIGHT // 4 + 30), 
                    (WIDTH // 4 * 3, HEIGHT // 4 + 30), 3)
    
    # Create an improved subtitle with better styling
    subtitle_font = pygame.font.Font(None, int(HEIGHT * 0.05))
    subtitle = subtitle_font.render("Select Game Duration", True, (200, 200, 255))
    screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100)))
    
    # Add hover animations and improved styling to buttons
    mouse_pos = pygame.mouse.get_pos()
    current_time = pygame.time.get_ticks()
    
    # Draw a panel behind the timer buttons
    # pygame.draw.rect(screen, (20, 30, 60, 180), 
    #                  pygame.Rect(WIDTH // 4, HEIGHT // 2 - 70, WIDTH // 2, 120), 
    #                  border_radius=10)
    
    for button in timer_buttons:
        button.update_rect(WIDTH, HEIGHT)
        button.handle_hover(mouse_pos)
        
        # Add a glow effect to selected buttons
        if button.is_selected:
            glow_surf = pygame.Surface((button.rect.width + 10, button.rect.height + 10), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (255, 0, 0, 100), 
                             pygame.Rect(0, 0, button.rect.width + 10, button.rect.height + 10), 
                             border_radius=12)
            screen.blit(glow_surf, (button.rect.x - 5, button.rect.y - 5))
            
        button.draw(screen)
        
        if button.is_hover:
            hover_size = 2 + math.sin(current_time / 200) * 1  # Animated border
            pygame.draw.rect(screen, HOVER_COLOR, button.rect, int(hover_size))
        elif button.is_selected:
            pygame.draw.rect(screen, (255, 0, 0), button.rect, 3)
    
    # Create a visually distinct section for utility buttons
    # pygame.draw.rect(screen, (30, 40, 70, 180), 
    #                  pygame.Rect(WIDTH // 4, HEIGHT - 150, WIDTH // 2, 100), 
    #                  border_radius=10)
    
    # Add icons to buttons
    for btn in [game_rule_button, history_button, start_button, close_button]:
        btn.update_rect(WIDTH, HEIGHT)
        btn.handle_hover(mouse_pos)
        
        # Add shadow effect to buttons
        shadow_rect = btn.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(screen, (0, 0, 0, 100), shadow_rect, border_radius=8)
        
        btn.draw(screen)
        
        if btn.is_hover:
            # Create a pulsing highlight effect
            highlight_size = 2 + math.sin(current_time / 200)
            pygame.draw.rect(screen, HOVER_COLOR, btn.rect, int(highlight_size), border_radius=8)
            
            # Show tooltip for buttons
            if btn == game_rule_button:
                draw_tooltip(screen, "View Game Rules", mouse_pos)
            elif btn == history_button:
                draw_tooltip(screen, "Match History", mouse_pos)
    
    # Add a version number in the corner
    version_font = pygame.font.Font(None, int(HEIGHT * 0.02))
    version_text = version_font.render("v1.0.2", True, (150, 150, 150))
    screen.blit(version_text, (WIDTH - 60, HEIGHT - 30))
# Modified draw_game_over_screen and draw_game_draw_screen to include close_button
def draw_game_over_screen(winner):
    screen.blit(game_finish_background, (0, 0))
    title_font = pygame.font.Font(None, int(HEIGHT * 0.1))
    winner_text = title_font.render(f"{winner} Player Wins!", True, BLACK)
    screen.blit(winner_text, winner_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    
    start_button.text = ""
    start_button.image = replay_button_image
    start_button.update_rect(WIDTH, HEIGHT)
    start_button.draw(screen)
    
    close_button.update_rect(WIDTH, HEIGHT)
    close_button.draw(screen)  # Show close_button on game_over screen

def draw_game_draw_screen():
    screen.blit(game_finish_background, (0, 0))
    title_font = pygame.font.Font(None, int(HEIGHT * 0.1))
    draw_text = title_font.render("Game Draw!", True, BLACK)
    screen.blit(draw_text, draw_text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
    
    start_button.text = ""
    start_button.image = replay_button_image
    start_button.update_rect(WIDTH, HEIGHT)
    start_button.draw(screen)
    
    close_button.update_rect(WIDTH, HEIGHT)
    close_button.draw(screen)  # Show close_button on game_draw screen

def draw_history_screen():
    screen.blit(background_image, (0, 0))
    title_font = pygame.font.Font(None, int(HEIGHT * 0.1))
    title = title_font.render("Score History", True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 4)))

    history_font = pygame.font.Font(None, int(HEIGHT * 0.035))
    history_rect = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2 - 100, 400, 200)
    pygame.draw.rect(screen, (50, 50, 50, 180), history_rect, 0, 5)

    y_offset = HEIGHT // 2 - 70
    for i, game in enumerate(reversed(score_history)):
        if game["winner"] == "Blue":
            color = BLUE
        elif game["winner"] == "Red":
            color = RED
        else:
            color = WHITE
        text = f"Game {len(score_history) - i}: Blue ({game['blue_points']}) vs Red ({game['red_points']})"
        history_text = history_font.render(text, True, color)
        screen.blit(history_text, history_text.get_rect(center=(WIDTH // 2, y_offset)))
        y_offset += 30

    back_button = ResponsiveButton(0.45, 0.8, 0.1, 0.1, " ", close_button_image)
    back_button.update_rect(WIDTH, HEIGHT)
    back_button.draw(screen)
    return back_button

def draw_dialogue_box(message):
    global dialogue_alpha, dialogue_active
    
    if not dialogue_active:
        return
    
    dialogue_surface = pygame.Surface((300, 100), pygame.SRCALPHA)
    dialogue_surface.fill((50, 50, 50, dialogue_alpha))
    
    font = pygame.font.Font(None, 36)
    text = font.render(message, True, WHITE)
    text_rect = text.get_rect(center=(150, 50))
    dialogue_surface.blit(text, text_rect)
    
    screen.blit(dialogue_surface, (WIDTH // 2 - 150, HEIGHT // 2 - 50))
    
    dialogue_alpha -= DIALOGUE_FADE_SPEED
    if dialogue_alpha <= 0:
        dialogue_active = False
        dialogue_alpha = 255

def draw_mode_selection_screen():
    screen.blit(background_image, (0, 0))
    title_font = pygame.font.Font(None, int(HEIGHT * 0.1))
    title = title_font.render("Select Difficulty", True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 4)))

    # Use generic button image for mode selection
    button_image = generic_button_image

    mode_buttons = [
        ResponsiveButton(0.3, 0.5, 0.15, 0.1, "Easy", button_image, text_opacity=255, text_color=WHITE),
        ResponsiveButton(0.45, 0.5, 0.15, 0.1, "Medium", button_image, text_opacity=255, text_color=WHITE),
        ResponsiveButton(0.6, 0.5, 0.15, 0.1, "Hard", button_image, text_opacity=255, text_color=WHITE)
    ]

    mouse_pos = pygame.mouse.get_pos()
    for button in mode_buttons:
        button.update_rect(WIDTH, HEIGHT)
        button.handle_hover(mouse_pos)
        button.draw(screen)
        if button.is_hover:
            pygame.draw.rect(screen, HOVER_COLOR, button.rect, 2)

    return mode_buttons

# Sound settings
sound_enabled = True

def toggle_sound():
    global sound_enabled
    sound_enabled = not sound_enabled
    if sound_enabled:
        pygame.mixer.music.unpause()
    else:
        pygame.mixer.music.pause()

def collect_resources(player_pos, player_resources):
    global resources
    px, py = int(player_pos[0]), int(player_pos[1])
    if (py, px) in resources:
        resource = resources[(py, px)]
        amount = resource["amount"]
        if resource["type"] == "Gold":
            player_resources['Gold'] += amount
            points = amount * 50
        elif resource["type"] == "Wood":
            player_resources['Wood'] += amount
            points = amount * 30
        else:
            points = 0
        
        if points > 0:
            resource_collect_sound.play()
            player_resources['Points'] += points
        del resources[(py, px)]
        resource_collection_effect(player_pos, {"Gold": amount if resource["type"] == "Gold" else 0, "Wood": amount if resource["type"] == "Wood" else 0})
        return points
    return 0

def build_structure(player_pos, player_resources, building_type, player_id):
    global buildings
    px, py = int(player_pos[0]), int(player_pos[1])
    pos = (py, px)
    
    if pos in buildings:
        print(f"Cannot build {building_type} at {pos}: Tile already has a building.")
        return False
    if pos in resources:
        print(f"Cannot build {building_type} at {pos}: Tile has resources.")
        return False
    
    if building_type == "Gold Mine":
        if player_resources["Gold"] >= 10:
            player_resources["Gold"] -= 10
            buildings[pos] = {"type": "Gold Mine", "owner": player_id, "last_generated": time.time()}
            build_sound.play()
            player_resources["Points"] += 100
            print(f"Player {player_id} built a Gold Mine at {pos}")
            return True
        else:
            print(f"Player {player_id} lacks gold (has {player_resources['Gold']}, needs 10) for Gold Mine")
    elif building_type == "Lumber Mill":
        if player_resources["Wood"] >= 10:
            player_resources["Wood"] -= 10
            buildings[pos] = {"type": "Lumber Mill", "owner": player_id, "last_generated": time.time()}
            build_sound.play()
            player_resources["Points"] += 75
            print(f"Player {player_id} built a Lumber Mill at {pos}")
            return True
        else:
            print(f"Player {player_id} lacks wood (has {player_resources['Wood']}, needs 10) for Lumber Mill")
    
    return False

def generate_building_resources():
    current_time = time.time()
    if (current_time - game_state["last_building_generation"]) >= 5:
        for pos, building in buildings.items():
            owner_resources = player1_resources if building["owner"] == 1 else player2_resources
            if building["type"] == "Gold Mine":
                owner_resources["Gold"] += 1
                print(f"Gold Mine at {pos} generated 1 Gold for Player {building['owner']}")
            elif building["type"] == "Lumber Mill":
                owner_resources["Wood"] += 1
                print(f"Lumber Mill at {pos} generated 1 Wood for Player {building['owner']}")
            building["last_generated"] = current_time
        game_state["last_building_generation"] = current_time

# Modified check_obstacle_collision function
def check_obstacle_collision(player_pos, player_resources, player_id):
    global player1_on_obstacle, player2_on_obstacle, player1_last_obstacle_deduction, player2_last_obstacle_deduction
    px, py = int(player_pos[0]), int(player_pos[1])
    pos = (py, px)
    current_time = time.time()

    if pos in obstacles and player_resources["Points"] > 0:
        obstacle_type = obstacles[pos]
        multiplier = MODE_MULTIPLIERS.get(selected_mode, 1.0)  # Default to 1.0 if mode is None
        initial_penalty = BASE_PENALTIES[obstacle_type]["initial"] * multiplier
        continuous_penalty = BASE_PENALTIES[obstacle_type]["continuous"] * multiplier

        # Handle initial collision
        if (player_id == 1 and not player1_on_obstacle) or (player_id == 2 and not player2_on_obstacle):
            player_resources["Points"] = max(0, player_resources["Points"] - initial_penalty)
            resource_collect_sound.play()
            print(f"Player {player_id} hit {obstacle_type} at {pos}, lost {initial_penalty} points (initial)")
            if player_id == 1:
                player1_on_obstacle = True
                player1_last_obstacle_deduction = current_time
            else:
                player2_on_obstacle = True
                player2_last_obstacle_deduction = current_time

        # Handle continuous deduction every 2 seconds
        if player_id == 1 and player1_on_obstacle:
            time_since_last_deduction = current_time - player1_last_obstacle_deduction
            if time_since_last_deduction >= OBSTACLE_CHECK_INTERVAL:
                player_resources["Points"] = max(0, player_resources["Points"] - continuous_penalty)
                resource_collect_sound.play()
                print(f"Player {player_id} on {obstacle_type} at {pos}, lost {continuous_penalty} points (continuous)")
                player1_last_obstacle_deduction = current_time
        elif player_id == 2 and player2_on_obstacle:
            time_since_last_deduction = current_time - player2_last_obstacle_deduction
            if time_since_last_deduction >= OBSTACLE_CHECK_INTERVAL:
                player_resources["Points"] = max(0, player_resources["Points"] - continuous_penalty)
                resource_collect_sound.play()
                print(f"Player {player_id} on {obstacle_type} at {pos}, lost {continuous_penalty} points (continuous)")
                player2_last_obstacle_deduction = current_time
    else:
        # Reset obstacle status when player is off the obstacle
        if player_id == 1 and player1_on_obstacle:
            player1_on_obstacle = False
        elif player_id == 2 and player2_on_obstacle:
            player2_on_obstacle = False


def save_score_history():
    try:
        with open(SCORE_FILE, 'w') as f:
            json.dump(score_history, f)
    except Exception as e:
        print(f"Error saving score history: {e}")

def determine_winner():
    blue_points = player1_resources["Points"]
    red_points = player2_resources["Points"]
    if blue_points > red_points:
        winner = "Blue"
    elif blue_points < red_points:
        winner = "Red"
    else:
        winner = "Draw"
    
    score_history.append({
        "winner": winner,
        "blue_points": blue_points,
        "red_points": red_points
    })
    if len(score_history) > MAX_HISTORY:
        score_history.pop(0)
    save_score_history()
    
    return winner
class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-0.5, 0.5)
        self.size = random.randint(1, 3)
        self.color = (
            random.randint(100, 200),
            random.randint(100, 200),
            random.randint(200, 255),
            random.randint(20, 100)
        )
        self.life = random.randint(30, 100)
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        
        # Fade out as life decreases
        if self.color[3] > 0:
            alpha = int(self.color[3] * (self.life / 100))
            self.color = (self.color[0], self.color[1], self.color[2], alpha)
    
    def draw(self, surface):
        if self.life > 0:
            s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, self.color, (self.size, self.size), self.size)
            surface.blit(s, (int(self.x), int(self.y)))

# Create initial particles
particles = []
for _ in range(50):
    particles.append(Particle(
        random.randint(0, WIDTH),
        random.randint(0, HEIGHT)
    ))

# Add this to your game loop to maintain particles
def update_particles():
    # Remove dead particles
    global particles
    particles = [p for p in particles if p.life > 0]
    
    # Add new particles occasionally
    if len(particles) < 50 and random.random() < 0.1:
        particles.append(Particle(
            random.randint(0, WIDTH),
            random.randint(0, HEIGHT)
        ))
def generate_resources():
    current_time = time.time()
    interval = RESOURCE_GENERATION_INTERVAL / (1 + 0.2 * max(player1_upgrades.upgrades['resource_generation'].current_level, player2_upgrades.upgrades['resource_generation'].current_level))
    if (current_time - game_state["last_resource_generation"]) >= interval:
        empty_cells = [(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE) if (r, c) not in resources and (r, c) not in buildings]
        if empty_cells:
            num_resources = min(len(empty_cells), random.randint(1, 3))
            resource_cells = random.sample(empty_cells, num_resources)
            for cell in resource_cells:
                resource_type = 'Gold' if len(resources) % 2 == 0 else 'Wood'
                resources[cell] = {
                    "type": resource_type,
                    "amount": GOLD_GENERATION_AMOUNT if resource_type == 'Gold' else WOOD_GENERATION_AMOUNT,
                    "spawn_time": current_time
                }
        game_state['last_resource_generation'] = current_time

class Upgrade:
    def __init__(self, name, description, base_cost, max_level, effect_function):
        self.name = name
        self.description = description
        self.base_cost = base_cost
        self.max_level = max_level
        self.current_level = 0
        self.effect_function = effect_function

    def can_upgrade(self, resources):
        return resources >= self.get_current_cost()

    def get_current_cost(self):
        return self.base_cost * (2 ** self.current_level)

    def apply_upgrade(self):
        if self.current_level < self.max_level:
            self.current_level += 1
            return True
        return False

class PlayerUpgrades:
    def __init__(self):
        self.upgrades = {
            'resource_generation': Upgrade('Resource Generation', 'Increase resource generation speed', 50, 5, self.modify_resource_generation),
            'movement_speed': Upgrade('Movement Speed', 'Increase player movement speed', 75, 3, self.modify_movement_speed),
            'vision_radius': Upgrade('Vision Radius', 'Expand player vision', 100, 3, self.modify_vision_radius)
        }
    
    def modify_resource_generation(self, current_value):
        return current_value * (1 + 0.2 * self.upgrades['resource_generation'].current_level)

    def modify_movement_speed(self, current_value):
        return current_value * (1 + 0.15 * self.upgrades['movement_speed'].current_level)

    def modify_vision_radius(self, current_value):
        return current_value + self.upgrades['vision_radius'].current_level

    def can_upgrade(self, upgrade_name, resources):
        return self.upgrades[upgrade_name].can_upgrade(resources)

    def upgrade(self, upgrade_name, resources):
        upgrade = self.upgrades[upgrade_name]
        if upgrade.can_upgrade(resources):
            if upgrade.apply_upgrade():
                return upgrade.get_current_cost()
        return 0

player1_upgrades = PlayerUpgrades()
player2_upgrades = PlayerUpgrades()

class ResourceParticle:
    def __init__(self, x, y, resource_type):
        self.x = x
        self.y = y
        self.resource_type = resource_type
        self.color = GOLD_COLOR if resource_type == 'Gold' else WOOD_COLOR
        self.size = random.randint(3, 7)
        self.velocity_x = random.uniform(-2, 2)
        self.velocity_y = random.uniform(-3, -1)
        self.alpha = 255
        
    def update(self):
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.velocity_y += 0.2
        self.alpha = max(0, self.alpha - 10)
        return self.alpha > 0
        
    def draw(self, screen):
        particle_surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        pygame.draw.circle(particle_surface, (*self.color, self.alpha), (self.size//2, self.size//2), self.size//2)
        screen.blit(particle_surface, (int(self.x), int(self.y)))

def resource_collection_effect(pos, resources_collected):
    x = pos[0] * TILE_SIZE + TILE_SIZE // 2
    y = pos[1] * TILE_SIZE + TILE_SIZE // 2
    for resource_type, amount in resources_collected.items():
        for _ in range(amount * 2):
            particles.append(ResourceParticle(x, y, resource_type))

def play_background_music():
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.load(background_music)
        pygame.mixer.music.set_volume(0.1)
        pygame.mixer.music.play(-1)

# Modified main function
def main():
    global game_state, particles, dialogue_active, dialogue_alpha, selected_mode
    global player1_on_obstacle, player2_on_obstacle, player1_last_obstacle_deduction, player2_last_obstacle_deduction
    play_background_music()
    
    move_cooldown1 = MOVE_DELAY
    move_cooldown2 = MOVE_DELAY
    running = True
    winner = None
    clock = pygame.time.Clock()

    # Reset button states when starting the game
    reset_button_states()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m:
                    toggle_sound()
                if game_state["screen"] == "playing":
                    # Check obstacle collision for both players
                    check_obstacle_collision(player1_pos, player1_resources, 1)
                    check_obstacle_collision(player2_pos, player2_resources, 2)
                    
                    # Handle upgrade keys for player 1
                    if event.key == pygame.K_1 and player1_resources['Gold'] >= player1_upgrades.upgrades['resource_generation'].get_current_cost():
                        cost = player1_upgrades.upgrade('resource_generation', player1_resources['Gold'])
                        player1_resources['Gold'] -= cost
                    elif event.key == pygame.K_2 and player1_resources['Gold'] >= player1_upgrades.upgrades['movement_speed'].get_current_cost():
                        cost = player1_upgrades.upgrade('movement_speed', player1_resources['Gold'])
                        player1_resources['Gold'] -= cost
                    elif event.key == pygame.K_3 and player1_resources['Gold'] >= player1_upgrades.upgrades['vision_radius'].get_current_cost():
                        cost = player1_upgrades.upgrade('vision_radius', player1_resources['Gold'])
                        player1_resources['Gold'] -= cost
                    elif event.key == pygame.K_4:
                        build_structure(player1_pos, player1_resources, "Gold Mine", 1)
                    elif event.key == pygame.K_5:
                        build_structure(player1_pos, player1_resources, "Lumber Mill", 1)
                    elif event.key == pygame.K_7 and player2_resources['Gold'] >= player2_upgrades.upgrades['resource_generation'].get_current_cost():
                        cost = player2_upgrades.upgrade('resource_generation', player2_resources['Gold'])
                        player2_resources['Gold'] -= cost
                    elif event.key == pygame.K_8 and player2_resources['Gold'] >= player2_upgrades.upgrades['movement_speed'].get_current_cost():
                        cost = player2_upgrades.upgrade('movement_speed', player2_resources['Gold'])
                        player2_resources['Gold'] -= cost
                    elif event.key == pygame.K_9 and player2_resources['Gold'] >= player2_upgrades.upgrades['vision_radius'].get_current_cost():
                        cost = player2_upgrades.upgrade('vision_radius', player2_resources['Gold'])
                        player2_resources['Gold'] -= cost
                    elif event.key == pygame.K_i:
                        build_structure(player2_pos, player2_resources, "Gold Mine", 2)
                    elif event.key == pygame.K_o:
                        build_structure(player2_pos, player2_resources, "Lumber Mill", 2)

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                if game_state["screen"] == "start":
                    if event.button == 1:
                        for button in timer_buttons:
                            if button.is_clicked(event.pos):
                                button_click_sound.play()
                                for b in timer_buttons:
                                    b.is_selected = False
                                button.is_selected = True
                                game_state["selected_duration"] = int(button.text.replace("s", ""))
                        if start_button.is_clicked(mouse_pos):
                            if game_state["selected_duration"] > 0:
                                button_click_sound.play()
                                game_state["screen"] = "mode_selection"
                            else:
                                button_click_sound.play()
                                dialogue_active = True
                                dialogue_alpha = 255
                        if close_button.is_clicked(mouse_pos):
                            button_click_sound.play()
                            running = False
                        if history_button.is_clicked(mouse_pos):
                            button_click_sound.play()
                            game_state["previous_screen"] = "start"
                            game_state["screen"] = "history"
                        if game_rule_button.is_clicked(mouse_pos):
                            button_click_sound.play()
                            game_state["previous_screen"] = "start"
                            game_state["screen"] = "game_rule"
                elif game_state["screen"] == "mode_selection":
                    mode_buttons = draw_mode_selection_screen()
                    if event.button == 1:
                        for button in mode_buttons:
                            if button.is_clicked(mouse_pos):
                                button_click_sound.play()
                                game_state["selected_mode"] = button.text
                                reset_game()
                                game_state["screen"] = "playing"
                                game_state["start_time"] = time.time()
                                game_state["game_duration"] = game_state["selected_duration"]
                elif game_state["screen"] == "history":
                    back_button = draw_history_screen()
                    if back_button.is_clicked(mouse_pos):
                        button_click_sound.play()
                        game_state["screen"] = game_state["previous_screen"]
                        game_state["previous_screen"] = None
                elif game_state["screen"] == "game_rule":
                    back_button = draw_game_rule_screen()
                    if back_button.is_clicked(mouse_pos):
                        button_click_sound.play()
                        game_state["screen"] = game_state["previous_screen"]
                        game_state["previous_screen"] = None
                elif game_state["screen"] in ["game_over", "game_draw"]:
                    if start_button.is_clicked(mouse_pos):
                        reset_game()
                        reset_button_states()
                        game_state["screen"] = "start"
                        winner = None
                        for button in timer_buttons:
                            button.is_selected = False
                        game_state["selected_duration"] = 0
                        player1_on_obstacle = False
                        player2_on_obstacle = False
                    if close_button.is_clicked(mouse_pos):
                        running = False

        keys = pygame.key.get_pressed()

        if game_state["screen"] == "playing":
            move_cooldown1 -= 1
            if move_cooldown1 <= 0:
                moved = False
                if keys[pygame.K_UP] and player1_target[1] > 0:
                    player1_target[1] -= 1
                    move_cooldown1 = MOVE_DELAY
                    moved = True
                elif keys[pygame.K_DOWN] and player1_target[1] < GRID_SIZE - 1:
                    player1_target[1] += 1
                    move_cooldown1 = MOVE_DELAY
                    moved = True
                elif keys[pygame.K_LEFT] and player1_target[0] > 0:
                    player1_target[0] -= 1
                    move_cooldown1 = MOVE_DELAY
                    moved = True
                elif keys[pygame.K_RIGHT] and player1_target[0] < GRID_SIZE - 1:
                    player1_target[0] += 1
                    move_cooldown1 = MOVE_DELAY
                    moved = True
                if moved:
                    move_sound.play()
                    player1_pos[:] = player1_target
                check_obstacle_collision(player1_pos, player1_resources, 1)

            move_cooldown2 -= 1
            if move_cooldown2 <= 0:
                moved = False
                if keys[pygame.K_w] and player2_target[1] > 0:
                    player2_target[1] -= 1
                    move_cooldown2 = MOVE_DELAY
                    moved = True
                elif keys[pygame.K_s] and player2_target[1] < GRID_SIZE - 1:
                    player2_target[1] += 1
                    move_cooldown2 = MOVE_DELAY
                    moved = True
                elif keys[pygame.K_a] and player2_target[0] > 0:
                    player2_target[0] -= 1
                    move_cooldown2 = MOVE_DELAY
                    moved = True
                elif keys[pygame.K_d] and player2_target[0] < GRID_SIZE - 1:
                    player2_target[0] += 1
                    move_cooldown2 = MOVE_DELAY
                    moved = True
                if moved:
                    move_sound.play()
                    player2_pos[:] = player2_target
                check_obstacle_collision(player2_pos, player2_resources, 2)

            screen.blit(background_image, (0, 0))
            draw_grid()
            draw_units()
            draw_ui()

            particles[:] = [p for p in particles if p.update()]
            for particle in particles:
                particle.draw(screen)

            game_state["remaining_time"] = max(0, game_state["game_duration"] - int(time.time() - game_state["start_time"]))
            if game_state["remaining_time"] <= 0:
                winner = determine_winner()
                game_over_sound.play()
                game_state["screen"] = "game_over" if winner != "Draw" else "game_draw"

            collect_resources(player1_pos, player1_resources)
            collect_resources(player2_pos, player2_resources)
            generate_resources()
            generate_building_resources()

        elif game_state["screen"] == "start":
            draw_start_screen()
            if dialogue_active:
                draw_dialogue_box("Please select a timer!")
        elif game_state["screen"] == "mode_selection":
            draw_mode_selection_screen()
        elif game_state["screen"] == "history":
            draw_history_screen()
        elif game_state["screen"] == "game_rule":
            draw_game_rule_screen()
        elif game_state["screen"] == "game_over":
            draw_game_over_screen(winner)
        elif game_state["screen"] == "game_draw":
            draw_game_draw_screen()

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()