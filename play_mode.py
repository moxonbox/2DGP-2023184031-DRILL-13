from pico2d import *
import game_framework
import game_world
import pause_mode
from boy import Boy
from grass import Grass

boy = None
pause_started_at = None


def release_movement_keys(events):
    # A mode switch must not discard key releases already polled this frame.
    for event in events:
        if event.type == SDL_KEYUP and event.key in (SDLK_LEFT, SDLK_RIGHT):
            boy.handle_event(event)


def handle_events():
    global pause_started_at
    event_list = get_events()
    for index, event in enumerate(event_list):
        if event.type == SDL_QUIT:
            game_framework.quit()
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            import title_mode
            game_framework.change_mode(title_mode)
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_p:
            pause_started_at = get_time()
            game_framework.push_mode(pause_mode)
            release_movement_keys(event_list[index + 1:])
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_i:
            import item_mode
            game_framework.push_mode(item_mode)
            release_movement_keys(event_list[index + 1:])
            return
        else:
            boy.handle_event(event)


def init():
    global boy, pause_started_at
    pause_started_at = None

    boy = Boy()
    game_world.add_oject(boy)

    grass = Grass()
    game_world.add_oject(grass, 0)


def update():
    game_world.update()


def pause():
    pass


def resume():
    global pause_started_at
    if pause_started_at is None:
        return
    if boy.state == 'IDLE':
        boy.idle_started_at += get_time() - max(pause_started_at, boy.idle_started_at)
    pause_started_at = None


def render():
    clear_canvas()
    game_world.render()
    update_canvas()


def finish():
    global boy
    game_world.clear()
    boy = None
