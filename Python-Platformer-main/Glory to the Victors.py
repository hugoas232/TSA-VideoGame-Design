# import necessary modules
import os
import random
import math
import pygame
import json
from os import listdir
from os.path import isfile, join


# initialize pygame
pygame.init()

# set the title of the window
pygame.display.set_caption("Platformer")

# initialize constants for the game
WIDTH, HEIGHT = 1000, 800  # screen size
FPS = 60  # frames per second
PLAYER_VEL = 5  # player velocity
PLAYER_WIDTH = 50 # player width
PLAYER_HEIGHT = 50 # player height
BLOCK_SIZE = 96 # block size
SCROLL_AREA_WIDTH = 200 # width of area triggering camera scroll
GRAVITY = 1 
JUMP_POWER = 9 
ANIMATION_DELAY = 3
HIT_DELAY = 2
MENU = 0 #index for menu game state
GAME = 1 #index for playing game state
GAME_OVER = 2 #index for game over game state
GAME_WIN = 3 #index for win game state
FALL_THRESHOLD = 715  # value where the player takes damage

# list of player key bindings dictionaries
PLAYER_BINDINGS = [
    #player 1
    {"left": pygame.K_LEFT, "right": pygame.K_RIGHT, "jump": pygame.K_UP},
    #player 2
    {"left": pygame.K_a, "right": pygame.K_d, "jump": pygame.K_w},
    #player 3
    {"left": pygame.K_j, "right": pygame.K_l, "jump": pygame.K_i},
    #player 4
    {"left": pygame.K_f, "right": pygame.K_h, "jump": pygame.K_g},
]


# create a window with set width and height
window = pygame.display.set_mode((WIDTH, HEIGHT))


# function to flip a list of sprites horizontally
def flip(sprites):
    return [pygame.transform.flip(sprite, True, False) for sprite in sprites]


# function to load sprite sheets from a dir
def load_sprite_sheets(character_folder, character_name, width, height, direction=False):
    # get the path to the sprite sheet dir
    path = join("assets", character_folder, character_name)
    # get a list of files in the dir
    images = [f for f in listdir(path) if isfile(join(path, f))]

    # dictionary to store the sprite sheets
    all_sprites = {}

    # loop through each file in the dir
    for image in images:
        # load the sprite sheet
        sprite_sheet = pygame.image.load(join(path, image)).convert_alpha()

        # list to store individual sprites
        sprites = []
        # loop through each sprite in the sprite sheet
        #TODO make the sprite sheets
        for i in range(sprite_sheet.get_width() // width):
            # create a surface for the sprite
            surface = pygame.Surface((width, height), pygame.SRCALPHA, 32)
            # get the rectangle for sprite
            rect = pygame.Rect(i * width, 0, width, height)
            # blit (place image of) the sprite onto the surface
            surface.blit(sprite_sheet, (0, 0), rect)
            # scale the sprite up
            sprites.append(pygame.transform.scale2x(surface))

        # if the sprite sheet has a direction (like left and right), add both directions to the dictionary
        if direction:
            all_sprites[image.replace(".png", "") + "_right"] = sprites
            all_sprites[image.replace(".png", "") + "_left"] = flip(sprites)
        # else, add the sprite sheet to dictionary
        else:
            all_sprites[image.replace(".png", "")] = sprites

    # return dictionary of sprite sheets
    return all_sprites


# function to get a block sprite
def get_block(size):
    # get the path to the block sprite
    path = join("assets", "Terrain", "Terrain.png")
    # load the block sprite
    image = pygame.image.load(path).convert_alpha()
    # create surface for block
    surface = pygame.Surface((size, size), pygame.SRCALPHA, 32)
    # get the rectangle for the block
    rect = pygame.Rect(96, 0, size, size)
    # blit the block onto the surface
    surface.blit(image, (0, 0), rect)
    # scale block ip by a factor of 2
    return pygame.transform.scale2x(surface)


# object class
class Object(pygame.sprite.Sprite):
    # initialize the object
    def __init__(self, x, y, width, height, name=None):
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        self.width = width
        self.height = height
        self.name = name

    # method to draw the object
    def draw(self, win, offset_x, offset_y):
        win.blit(self.image, (self.rect.x - offset_x, self.rect.y - offset_y))


# exit class
class Exit(Object):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height, "exit")
        self.image = pygame.Surface((width, height), pygame.SRCALPHA)
        pygame.draw.rect(self.image, (255, 0, 0), (0, 0, width, height))
        self.mask = pygame.mask.from_surface(self.image)


# class for blocks
class Block(Object):
    # method to initialize the block
    def __init__(self, x, y, size):
        # initialize the block
        super().__init__(x, y, size, size)
        # get the block sprite
        block = get_block(size)
        # blit the block onto the image
        self.image.blit(block, (0, 0))
        # update the mask
        self.mask = pygame.mask.from_surface(self.image)


# level class to handle individual levels
class level:
    def __init__(self, name, background, blocks, exit, player_start):
        self.name = name
        self.background = background
        self.blocks = blocks
        self.exit = exit
        self.player_start = player_start

# player class
class Player(pygame.sprite.Sprite):
    COLOR = (255, 0, 0)  # default color

    def __init__(self, x, y, width, height, character_folder, character_name, sprite_width, sprite_height):
        # initialize the player
        super().__init__()
        self.rect = pygame.Rect(x, y, width, height)
        self.x_vel = 0  # initial x velocity
        self.y_vel = 0  # initial y velocity
        self.mask = None  # mask for collision detection
        self.direction = "left"  # initial direction
        self.animation_count = 0  # animation counter
        self.fall_count = 0  # fall counter
        self.jump_count = 0  # jump counter (0: on ground, 1: single jump)
        self.hit = False  # hit flag
        self.hit_count = 0  # hit counter
        self.color = (255, 0, 0)
        self.last_hit_time = 0  # keeps track of the last hit
        self.on_ground = False  # Flag to indicate if the player is on the ground
        self.SPRITES = load_sprite_sheets(
            character_folder, character_name, sprite_width, sprite_height, True
        )

    def jump(self):
        if self.jump_count < 2:
            # set the y velocity to -8 times the gravity constant
            self.y_vel = -GRAVITY * JUMP_POWER
            # reset animation counter
            self.animation_count = 0
            # increment jump counter
            self.jump_count += 1
            # reset fall count if initial jump (so it doesnt fall too fast)
            if self.jump_count == 1:
                self.fall_count = 0
                self.on_ground = False  # set the player to not be on the ground

    # method to move player
    def move(self, dx, dy):
        # move player by specified amount
        self.rect.x += dx
        self.rect.y += dy

    # method to make the player hit
    def make_hit(self):
        # set hit flag to True
        self.hit = True
        self.last_hit_time = pygame.time.get_ticks()

    # method to move the player left
    def move_left(self, vel):
        # set x velocity to negative vel (left)
        self.x_vel = -vel
        # if direction is not left, set it to left and reset animation counter
        if self.direction != "left":
            self.direction = "left"
            self.animation_count = 0

    # method to move the player right
    def move_right(self, vel):
        # set x velocity to positive vel (right)
        self.x_vel = vel
        # if direction is not right, set it to right and reset animation counter
        if self.direction != "right":
            self.direction = "right"
            self.animation_count = 0

    # method to update the player
    def loop(self, fps):
        # check if on ground to apply gravity, call gravity only if not on ground
        if not self.on_ground:
            self.y_vel += min(1, (self.fall_count / fps) * GRAVITY)

        # move the player by the x and y values
        self.move(self.x_vel, self.y_vel)

        # if player is hit, increment hit counter
        if self.hit:
            self.hit_count += 1
        # if the higt counter is more than 2 sec., reset hit flag and counter
        if self.hit_count > fps * HIT_DELAY:
            self.hit = False
            self.hit_count = 0

        # increment fall counter
        self.fall_count += 1
        # update sprite
        self.update_sprite()

    # method to land the player
    def landed(self):
        self.fall_count = 0
        self.y_vel = 0
        self.jump_count = 0  # Reset jump count when landed
        self.on_ground = True  # Set the on_ground flag to True when player lands

    # method to hit the player's head
    def hit_head(self):
        # reset count
        self.count = 0
        # reverse y velocity (multiply by -1)
        self.y_vel *= -1

    # method to update the sprite
    def update_sprite(self):
        # Determine sprite sheet based on player's state
        sprite_sheet = "idle"
        if self.hit:
            sprite_sheet = "hit"
        elif self.y_vel < 0:
            if self.jump_count == 1:
                sprite_sheet = "jump"
        elif self.y_vel > GRAVITY * 2:
            sprite_sheet = "fall"
        elif self.x_vel != 0:
            sprite_sheet = "run"

        # Get the sprite sheet name
        sprite_sheet_name = sprite_sheet + "_" + self.direction
        # Get the sprites from the sprite sheet
        sprites = self.SPRITES[sprite_sheet_name]

        # Get the sprite index based on the animation counter
        sprite_index = (self.animation_count // ANIMATION_DELAY) % len(sprites)

        # Set the sprite
        self.sprite = sprites[sprite_index]
        # Increment the animation counter
        self.animation_count += 1
        # Update the player
        self.update()

        # Reset animation counter if it exceeds the sprite sheet length
        if self.animation_count // ANIMATION_DELAY >= len(sprites):
            self.animation_count = 0

    # method to update the player
    def update(self):
        # update the rectangle and mask
        self.rect = self.sprite.get_rect(topleft=(self.rect.x, self.rect.y))
        self.mask = pygame.mask.from_surface(self.sprite)

    # method to draw the player
    def draw(self, win, offset_x, offset_y):
        win.blit(self.sprite, (self.rect.x - offset_x, self.rect.y - offset_y))


# function to get the background
def get_background(name):
    # get the path to the background image
    image = pygame.image.load(join("assets", "Background", name))
    # get the width and height of the image
    _, _, width, height = image.get_rect()
    # create a list to store the background tiles
    tiles = []

    # loop through each tile in the background
    for i in range(WIDTH // width + 1):
        for j in range(HEIGHT // height + 1):
            # get the position of the tile
            pos = (i * width, j * height)
            # add the tile to the list
            tiles.append(pos)

    # add the tile to the list
    return tiles, image

# function to draw the game over screen
def draw_game_over(window):
    window.fill((0, 0, 0))  # fill window with black

    font = pygame.font.Font(None, 60) # set the font of the text 
    text_surface = font.render("Game Over", True, (255, 255, 255)) #type the text
    text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    window.blit(text_surface, text_rect)

    font = pygame.font.Font(None, 30)
    restart_text_surface = font.render("Press R to Restart the Level", True, (255, 255, 255))
    restart_text_rect = restart_text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    window.blit(restart_text_surface, restart_text_rect)

    pygame.display.update()

# function to draw the game winning screen
def draw_game_win(window):
    window.fill((0, 0, 0))  # Fill with black

    font = pygame.font.Font(None, 60)
    text_surface = font.render("You Win!", True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    window.blit(text_surface, text_rect)

    font = pygame.font.Font(None, 30)
    restart_text_surface = font.render("Press R to Restart", True, (255, 255, 255))
    restart_text_rect = restart_text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    window.blit(restart_text_surface, restart_text_rect)

    pygame.display.update()


# function to draw the whole game on the window
def draw(window, background, bg_image, players, objects, exit, offset_x, offset_y, lives, game_state):
    menu_boxes = []  # Initialize menu_boxes

    if game_state == MENU:
        menu_boxes = draw_menu(window)
    elif game_state == GAME:
        # Draw the background
        for tile in background:
            window.blit(bg_image, tile)

        # Draw the objects
        for obj in objects:
            obj.draw(window, offset_x, offset_y)
        
        #Draw the exit
        exit.draw(window, offset_x, offset_y)

        # Draw the player(s)
        for player in players:
            player.draw(window, offset_x, offset_y)

        # Draw lives
        font = pygame.font.Font(None, 36)
        text = font.render(f"Lives: {lives}", True, (255, 255, 255))
        window.blit(text, (10, 10))
    elif game_state == GAME_OVER:
        draw_game_over(window)
    elif game_state == GAME_WIN:
        draw_game_win(window)

    # Update the display
    pygame.display.update()
    return menu_boxes


# method to handle vertical collisions
def handle_vertical_collision(player, objects, dy):
    # create a list to store the collided objects
    collided_objects = []
    # loop through each object
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            if dy > 0:
                player.rect.bottom = obj.rect.top
                player.landed()  # Call landed when player touches the ground
            elif dy < 0:
                player.rect.top = obj.rect.bottom
                player.hit_head()

            collided_objects.append(obj)

    # returns list of collided objects
    return collided_objects


# method to check for player collition
def collide(player, objects, dx):
    # move the player by amount
    player.move(dx, 0)
    # update the player
    player.update()
    # initialize collided object to none (meaning there is no colision)
    collided_object = None
    # loop through each object
    for obj in objects:
        if pygame.sprite.collide_mask(player, obj):
            # set the collided object
            collided_object = obj
            break

    # move the player by specified amount
    player.move(-dx, 0)
    # update player
    player.update()
    # return collided object
    return collided_object


# Method that handles the movement of the player based on their keybindings
def handle_player_input(player, keys, bindings, collide_left, collide_right):
    if keys[bindings["left"]] and not collide_left:
        player.move_left(PLAYER_VEL)
    if keys[bindings["right"]] and not collide_right:
        player.move_right(PLAYER_VEL)
    if keys[bindings["jump"]] and player.jump_count < 1:
        player.jump()


def is_on_ground(player, objects):
    # Create a rect below the player
    player_rect = player.rect

    # check for collisions along the width of the player
    for x_offset in range(0, player_rect.width, 4):  # Increment by 5 to make less intensive checks for perfomance
        temp_rect = pygame.Rect(player_rect.x + x_offset, player_rect.bottom + 1, 1, 1)
        for obj in objects:
            if temp_rect.colliderect(obj.rect):
                return True
    return False


# method handling movement of the players
def handle_move(players, objects, lives):
    keys = pygame.key.get_pressed()
    hit_this_frame = False  # Flag to track if any player was hit this frame

    for i, player in enumerate(players):
        # reset the player(s) velocity
        player.x_vel = 0
        # check for collision with objects left and right
        collide_left = collide(player, objects, -PLAYER_VEL * 2)
        collide_right = collide(player, objects, PLAYER_VEL * 2)

        # handle movement (keybinds)
        handle_player_input(player, keys, PLAYER_BINDINGS[i], collide_left, collide_right)

        player.on_ground = is_on_ground(player, objects)  # check if on the ground before all other collision checks

        # handle vertical collisions
        vertical_collide = handle_vertical_collision(player, objects, player.y_vel)

        # check for collisions with other objects
        to_check = [collide_left, collide_right, *vertical_collide]

        # Future function for entity damage
        # loop through each object to check
        # for obj in to_check:
        #      #check if the object is an entity
        #      if obj and obj.name == "": #Check if object is an entity
        #         if pygame.time.get_ticks() - player.last_hit_time > 1000: # prevent players from taking infinite damage
        #             #make the player hit if colliding with the entity
        #              player.make_hit()
        #              hit_this_frame = True # signal signifying the player was hit

    if hit_this_frame:  # Decrease lives only if a player has been hit in this frame
        lives -= 1
    return lives

# function for the camera following player one
#TODO make it so camera takes into account other players
def camera_follow(player, offset_x, offset_y, level_width, level_height):
    offset_x = max(0, min(level_width - WIDTH, player.rect.centerx - WIDTH // 2))
    offset_y = max(0, min(level_height - HEIGHT, player.rect.centery - HEIGHT // 2))

    return offset_x, offset_y


def draw_menu(window):
    window.fill((0, 0, 0))  # Fill with black

    font = pygame.font.Font(None, 60)
    text_surface = font.render("Select Number of Players", True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 4))
    window.blit(text_surface, text_rect)

    options = ["2 Players", "3 Players", "4 Players"]
    y_offset = HEIGHT // 2
    menu_boxes = []
    for i, option in enumerate(options):
        option_surface = font.render(option, True, (255, 255, 255))
        option_rect = option_surface.get_rect(center=(WIDTH // 2, y_offset))

        # Create rectangle behind the text
        box_rect = option_rect.inflate(20, 10)
        pygame.draw.rect(window, (100, 100, 100), box_rect)
        window.blit(option_surface, option_rect)
        menu_boxes.append(box_rect)
        y_offset += 80
    return menu_boxes


def handle_menu_input(event, menu_boxes):
    if event.type == pygame.MOUSEBUTTONDOWN:
        mouse_pos = pygame.mouse.get_pos()
        for i, box in enumerate(menu_boxes):
            if box.collidepoint(mouse_pos):
                return i + 2  # Number of players is index (0,1,2) + 2
    return None


def load_level(level_path):
    with open(level_path, "r") as f:
        level_data = json.load(f)

    #set variable names for easier coding
    level_name = level_data["name"]
    background = level_data["background"]
    player_start = level_data["player_start"]
    # create object lists
    blocks = []
    exit = None

    for obj_data in level_data["objects"]:
        obj_type = obj_data["type"]
        if obj_type == "block":
            blocks.append(Block(obj_data["x"], obj_data["y"], obj_data["size"]))
        elif obj_type == "exit":
            exit = Exit(obj_data["x"], obj_data["y"], obj_data["width"], obj_data["height"])

    level_width = 0
    level_height = 0
    if blocks:
        min_x = min([block.rect.left for block in blocks])
        max_x = max([block.rect.right for block in blocks])
        min_y = min([block.rect.top for block in blocks])
        max_y = max([block.rect.bottom for block in blocks])
        level_width = max_x - min_x
        level_height = max_y - min_y
    else:
        level_height = HEIGHT  # set to the height of the screen if there are no blocks
        level_width = WIDTH

    return level(level_name, background, blocks, exit, player_start), level_width, level_height


# main function of the game
def main(window):
    # create clock to control frame rate
    clock = pygame.time.Clock()
    # get the current lvl
    current_level_index = 0
    # load the first lvl
    current_level, level_width, level_height = load_level(f"levels/level{current_level_index + 1}.json")  # load lvl 1
    # store current lvl
    current_level_data = (current_level, level_width, level_height, current_level_index)

    # get background tiles and image
    background, bg_image = get_background(current_level.background)

    # set initial game state to menu
    game_state = MENU
    num_players = 0
    players = []
    lives = 0
    objects = []
    offset_x = 0
    offset_y = 0
    exit = None # Added default exit variable

    menu_boxes = []

    # main game loop
    run = True
    initial_offset = True  # cue for intial offset
    while run:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # quit game if window closed
                run = False
                break
            if game_state == MENU:
                num_players_selected = handle_menu_input(event, menu_boxes)
                if num_players_selected:
                    game_state = GAME
                    num_players = num_players_selected
                    lives = num_players + 1
                    # create a list of players
                    #MAKE SURE DIMENSIONS ARE ACCURATE WITH SPRITE SHEET
                    players = [
                        Player(
                            current_level.player_start["x"],
                            current_level.player_start["y"],
                            PLAYER_WIDTH,
                            PLAYER_HEIGHT,
                            "MainCharacters",
                            "p1Njal",
                            12,
                            45,
                        ),
                        Player(
                            current_level.player_start["x"] + 100,
                            current_level.player_start["y"],
                            PLAYER_WIDTH,
                            PLAYER_HEIGHT,
                            "MainCharacters",
                            "p2Revna",
                            15,
                            42,
                        ),
                    ]
                    if num_players >= 3:
                        players.append(
                            Player(
                                current_level.player_start["x"] + 200,
                                current_level.player_start["y"],
                                PLAYER_WIDTH,
                                PLAYER_HEIGHT,
                                "MainCharacters",
                                "p3Dwalin",
                                13,
                                35,
                            )
                        )
                    if num_players == 4:
                        players.append(
                            Player(
                                current_level.player_start["x"] + 300,
                                current_level.player_start["y"],
                                PLAYER_WIDTH,
                                PLAYER_HEIGHT,
                                "MainCharacters",
                                "p4Bjorn",
                                10,
                                43,
                            )
                        )
                    objects = current_level.blocks
                    exit = current_level.exit #separate exit

                    initial_offset = True

        if game_state == GAME:
            # update each player
            for player in players:
                player.loop(FPS)

            # handle player movement
            lives = handle_move(players, objects, lives)

            # check for initial offset and update the offset if true
            if initial_offset:
                offset_x, offset_y = camera_follow(
                    players[0], offset_x, offset_y, level_width, level_height
                )
                initial_offset = False

            # Update camera
            offset_x, offset_y = camera_follow(
                players[0], offset_x, offset_y, level_width, level_height
            )

            # Check for player falling off the map, and if so decrease lives
            for player in players:
                if not player.on_ground and player.rect.top > (FALL_THRESHOLD):
                    if pygame.time.get_ticks() - player.last_hit_time > 1000:
                        jump_count = 0
                        player.jump()
                        lives -= 1

        # draw game
        menu_boxes = draw(window, background, bg_image, players, objects, exit, offset_x, offset_y, lives, game_state)

        if game_state == GAME:
            # check for level completion
            all_players_in_exit = all(exit.rect.collidepoint(player.rect.center) for player in players)


            if all_players_in_exit:
                # switch to next lvl
                current_level_index += 1
                
                #exception to handle the end of the game
                try:
                    #try to switch to the next lvl
                    current_level, level_width, level_height = load_level(f"levels/level{current_level_index + 1}.json")  # load next level
                    current_level_data = (
                        current_level,
                        level_width,
                        level_height,
                        current_level_index,
                    )  # update current lvl data
                except FileNotFoundError:
                    #if no more lvls, u won
                    game_state = GAME_WIN
                    break

                background, bg_image = get_background(current_level.background)
                objects = current_level.blocks
                exit = current_level.exit #seperate exit

                for p in players:
                    p.rect.x = current_level.player_start["x"]
                    p.rect.y = current_level.player_start["y"]
                initial_offset = True

            #check for lives
            if lives <= 0:
                #if no more lives, u lost
                game_state = GAME_OVER
        elif game_state == GAME_OVER or game_state == GAME_WIN:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_r]:
                # reset game
                # load previous data
                current_level, level_width, level_height, current_level_index = current_level_data
                background, bg_image = get_background(current_level.background)

                for p in players:
                    p.rect.x = current_level.player_start["x"]
                    p.rect.y = current_level.player_start["y"]

                game_state = MENU
                num_players = 0
                players = []
                lives = 0
                objects = []
                offset_x = 0
                offset_y = 0
                exit = None # reset Exit
                menu_boxes = []
                initial_offset = True

    # quit pygame
    pygame.quit()
    # quit program


# run main function
if __name__ == "__main__":
    main(window)