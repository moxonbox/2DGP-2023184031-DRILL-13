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
        if event.type == SDL_KEYDOWN and event.key == SDLK_i:
            game_framework.pop_mode()
            return
        elif event.type == SDL_KEYDOWN and event.key in selections:
            play_mode.boy.selected_ball = selections[event.key]


def update():
    play_mode.update()


def render():
    clear_canvas()
    game_world.render()
    cx, cy = get_canvas_width() / 2, get_canvas_height() / 2
    image.draw(cx, cy)
    row_y = cy + (1 - play_mode.boy.selected_ball) * 66
    draw_rectangle(cx - 132, row_y - 30, cx + 132, row_y + 30,
                   255, 220, 0, filled=False)
    update_canvas()


def pause():
    pass


def resume():
    pass


def finish():
    global image
    image = None
