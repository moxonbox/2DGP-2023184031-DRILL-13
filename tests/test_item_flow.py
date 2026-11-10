"""Test game logic with real state transitions, without opening a canvas."""

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from sdl2 import SDL_KEYDOWN, SDL_KEYUP, SDLK_LEFT, SDLK_RIGHT, SDLK_SPACE

import ball
import boy
import game_framework
import game_world
import grass
import play_mode


class ItemFlowTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.images = {}
        self.load_image = Mock(side_effect=self.image_for)
        for module in (ball, boy, grass):
            self.enterContext(patch.object(module, 'load_image', self.load_image))
        for module in (boy, play_mode):
            self.enterContext(patch.object(module, 'get_time', lambda: self.now))
        self.enterContext(patch.object(ball, 'get_canvas_width', return_value=800))
        self.enterContext(patch.object(boy, 'get_canvas_width', return_value=800))
        game_world.clear()
        ball.Ball.images.clear()
        game_framework.running = False
        game_framework.stack = [play_mode]
        self.addCleanup(self.finish_modes)
        play_mode.init()

    def image_for(self, filename):
        if filename not in self.images:
            self.images[filename] = Mock(name=filename)
        return self.images[filename]

    def finish_modes(self):
        while game_framework.stack:
            game_framework.stack.pop().finish()
        game_world.clear()
        ball.Ball.images.clear()
        game_framework.running = False

    @staticmethod
    def key(key, event_type=SDL_KEYDOWN):
        return SimpleNamespace(type=event_type, key=key)

    def events(self, mode, *events):
        with patch.object(mode, 'get_events', return_value=list(events)):
            mode.handle_events()

    def balls(self):
        return [obj for layer in game_world.world for obj in layer
                if isinstance(obj, ball.Ball)]

    def test_new_play_has_no_ball_and_space_does_not_fire(self):
        self.assertEqual(play_mode.boy.selected_ball, 0)
        self.events(play_mode, self.key(SDLK_SPACE))
        self.assertEqual(self.balls(), [])

    def test_selected_ball_fires_in_last_facing_direction(self):
        character = play_mode.boy
        for ball_type in (1, 2):
            for direction_key, direction in ((SDLK_LEFT, -1), (SDLK_RIGHT, 1)):
                with self.subTest(ball_type=ball_type, direction=direction):
                    character.selected_ball = ball_type
                    self.events(play_mode, self.key(direction_key),
                                self.key(direction_key, SDL_KEYUP))
                    count = len(self.balls())
                    self.events(play_mode, self.key(SDLK_SPACE))
                    self.assertEqual(len(self.balls()), count + 1)
                    fired = self.balls()[-1]
                    self.assertEqual(fired.ball_type, ball_type)
                    self.assertEqual(fired.velocity, direction * 10)
                    self.assertEqual((fired.x, fired.y), (character.x, character.y))
                    self.assertIs(fired.image, self.images[ball.BALL_IMAGES[ball_type]])

    def test_space_fires_while_running_without_stopping(self):
        play_mode.boy.selected_ball = 1
        self.events(play_mode, self.key(SDLK_RIGHT), self.key(SDLK_SPACE))
        self.assertEqual(play_mode.boy.state, 'RUN')
        self.assertEqual(self.balls()[0].velocity, 10)

    def test_sleeping_space_wakes_before_firing(self):
        play_mode.boy.selected_ball = 2
        self.now = 5.0
        play_mode.update()
        self.assertEqual(play_mode.boy.state, 'SLEEP')
        self.events(play_mode, self.key(SDLK_SPACE))
        self.assertEqual(play_mode.boy.state, 'IDLE')
        self.assertEqual(self.balls(), [])
        self.events(play_mode, self.key(SDLK_SPACE))
        self.assertEqual(self.balls()[0].ball_type, 2)

    def test_sleeping_without_ball_can_wake(self):
        self.now = 5.0
        play_mode.update()
        self.events(play_mode, self.key(SDLK_SPACE))
        self.assertEqual(play_mode.boy.state, 'IDLE')
        self.assertEqual(self.balls(), [])


if __name__ == '__main__':
    unittest.main()
