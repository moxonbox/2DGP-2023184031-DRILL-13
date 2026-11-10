from pico2d import get_canvas_width, load_image

import game_world

BALL_IMAGES = {1: 'ball21x21.png', 2: 'ball41x41.png'}


class Ball:
    def __init__(self, x, y, velocity, ball_type):
        if ball_type not in BALL_IMAGES:
            raise ValueError(f'Unknown ball type: {ball_type}')
        self.ball_type = ball_type
        self.image = load_image(BALL_IMAGES[ball_type])
        self.x, self.y = x, y
        self.velocity = velocity

    def update(self):
        self.x += self.velocity
        if self.x < 0 or self.x > get_canvas_width():
            game_world.remove_object(self)

    def draw(self):
        self.image.draw(self.x, self.y)
