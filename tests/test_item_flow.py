"""Test game logic with real state transitions, without opening a canvas."""

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

from sdl2 import (SDL_KEYDOWN, SDL_KEYUP, SDL_QUIT, SDLK_0, SDLK_1, SDLK_2,
                  SDLK_ESCAPE, SDLK_LEFT, SDLK_RIGHT, SDLK_SPACE, SDLK_i, SDLK_p)

import ball
import boy
import game_framework
import game_world
import grass
import item_mode
import logo_mode
import pause_mode
import play_mode
import title_mode


class ItemFlowTests(unittest.TestCase):
    def setUp(self):
        self.now = 0.0
        self.images = {}
        self.load_image = Mock(side_effect=self.image_for)
        for module in (ball, boy, grass, item_mode, title_mode, logo_mode):
            self.enterContext(patch.object(module, 'load_image', self.load_image))
        for module in (boy, play_mode, logo_mode):
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

    def open_items(self):
        self.events(play_mode, self.key(SDLK_i))
        self.assertEqual(game_framework.stack, [play_mode, item_mode])

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

    def test_item_digits_update_the_same_character(self):
        character = play_mode.boy
        self.open_items()
        for key, selection in ((SDLK_1, 1), (SDLK_2, 2), (SDLK_0, 0)):
            with self.subTest(selection=selection):
                self.events(item_mode, self.key(key))
                self.assertEqual(character.selected_ball, selection)
                self.assertIs(play_mode.boy, character)

    def test_item_round_trip_preserves_selection_and_world(self):
        character = play_mode.boy
        character.selected_ball = 1
        self.events(play_mode, self.key(SDLK_SPACE))
        objects = [layer[:] for layer in game_world.world]
        self.open_items()
        self.events(item_mode, self.key(SDLK_2), self.key(SDLK_i))
        self.assertEqual(game_framework.stack, [play_mode])
        self.assertIs(play_mode.boy, character)
        self.assertEqual(game_world.world, objects)
        self.assertIsNone(item_mode.image)
        self.open_items()
        self.assertEqual(character.selected_ball, 2)

    def test_return_to_title_then_new_play_resets_selection(self):
        previous = play_mode.boy
        previous.selected_ball = 2
        self.open_items()
        self.events(item_mode, self.key(SDLK_ESCAPE))
        self.assertEqual(game_framework.stack, [title_mode])
        self.assertIsNone(play_mode.boy)
        self.assertIsNone(item_mode.image)
        self.assertTrue(all(not layer for layer in game_world.world))
        self.events(title_mode, self.key(SDLK_SPACE))
        self.assertEqual(game_framework.stack, [play_mode])
        self.assertIsNot(play_mode.boy, previous)
        self.assertEqual(play_mode.boy.selected_ball, 0)
        self.assertEqual([len(layer) for layer in game_world.world], [1, 1, 0])


if __name__ == '__main__':
    unittest.main()
