from pico2d import *
import game_framework
import title_mode

image = None
logo_start_time = 0.0


def init():
    global image, logo_start_time

    image = load_image('tuk_credit.png')
    logo_start_time = get_time()


def update():
    if get_time() - logo_start_time >= 2.0:
        game_framework.change_mode(title_mode)


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            game_framework.quit()


def render():
    clear_canvas()
    image.draw(400, 300)
    update_canvas()


def finish():
    global image
    del image

