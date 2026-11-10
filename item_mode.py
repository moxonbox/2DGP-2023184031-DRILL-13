from pico2d import *

import game_framework
import game_world
import play_mode

image = None


def init():
    global image
    image = load_image('item_select.png')


def handle_events():
    selections = {SDLK_0: 0, SDLK_1: 1, SDLK_2: 2}
    for event in get_events():
        if event.type == SDL_KEYDOWN and event.key in selections:
            play_mode.boy.selected_ball = selections[event.key]


def update():
    pass


def render():
    clear_canvas()
    game_world.render()
    cx, cy = get_canvas_width() / 2, get_canvas_height() / 2
    image.draw(cx, cy)
    update_canvas()


def pause():
    pass


def resume():
    pass


def finish():
    global image
    image = None
