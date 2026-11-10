from pico2d import *

import game_framework
import game_world
import play_mode

image = None


def init():
    global image
    image = load_image('item_select.png')


def handle_events():
    pass


def update():
    pass


def render():
    pass


def pause():
    pass


def resume():
    pass


def finish():
    global image
    image = None
