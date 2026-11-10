from pico2d import *
import game_framework
import game_world
import play_mode


def init():
    pass


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_p:
            game_framework.pop_mode()
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            import title_mode
            game_framework.pop_mode()
            game_framework.change_mode(title_mode)
            return
        elif event.type == SDL_KEYUP:
            play_mode.boy.handle_event(event)


def update():
    pass


def render():
    clear_canvas()
    game_world.render()
    x, y = get_canvas_width() / 2, get_canvas_height() / 2
    draw_rectangle(x - 90, y - 70, x + 90, y + 70, 20, 20, 20, filled=True)
    draw_rectangle(x - 42, y - 40, x - 14, y + 40, 255, 220, 0, filled=True)
    draw_rectangle(x + 14, y - 40, x + 42, y + 40, 255, 220, 0, filled=True)
    update_canvas()


def finish():
    pass
