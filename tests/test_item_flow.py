"""Test game logic with real state transitions, without opening a canvas."""

from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch

import pico2d
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

    def test_item_update_moves_world_exactly_once(self):
        play_mode.boy.selected_ball = 1
        self.events(play_mode, self.key(SDLK_SPACE))
        fired = self.balls()[0]
        start_x = fired.x
        self.open_items()
        with patch.object(game_world, 'update', wraps=game_world.update) as update:
            item_mode.update()
        update.assert_called_once_with()
        self.assertEqual(fired.x, start_x + 10)

    def test_item_update_removes_balls_only_after_crossing_edges(self):
        for x, velocity in ((790, 10), (10, -10)):
            with self.subTest(velocity=velocity):
                fired = ball.Ball(x, 90, velocity, 1)
                game_world.add_oject(fired)
                item_mode.update()
                self.assertIn(fired, self.balls())
                self.assertIn(fired.x, (0, 800))
                item_mode.update()
                self.assertNotIn(fired, self.balls())

    def test_mixed_balls_keep_images_and_reuse_each_cache(self):
        character = play_mode.boy
        for selection in (1, 2, 1, 2):
            character.selected_ball = selection
            self.events(play_mode, self.key(SDLK_SPACE))
        fired = self.balls()
        character.selected_ball = 0
        self.open_items()
        item_mode.update()
        for obj, selection in zip(fired, (1, 2, 1, 2)):
            self.assertEqual(obj.ball_type, selection)
            self.assertIs(obj.image, self.images[ball.BALL_IMAGES[selection]])
            obj.draw()
        self.assertIsNot(fired[0].image, fired[1].image)
        for filename in ball.BALL_IMAGES.values():
            self.assertEqual(self.load_image.call_args_list.count(call(filename)), 1)
            self.images[filename].draw.assert_has_calls([call(410, 90)] * 2)

    def test_invalid_ball_types_are_rejected(self):
        for selection in (0, -1, 3, '1', None):
            with self.subTest(selection=selection):
                with self.assertRaises(ValueError):
                    ball.Ball(400, 90, 10, selection)

    def test_item_time_reaches_sleep_and_is_not_adjusted_on_return(self):
        self.now = 1.0
        self.open_items()
        self.now = 4.99
        item_mode.update()
        self.assertEqual(play_mode.boy.state, 'IDLE')
        self.now = 5.0
        item_mode.update()
        self.assertEqual(play_mode.boy.state, 'SLEEP')
        self.now = 8.0
        self.events(item_mode, self.key(SDLK_i))
        self.assertEqual(play_mode.boy.idle_started_at, 0.0)
        self.assertIsNone(play_mode.pause_started_at)

    def test_item_return_before_sleep_preserves_idle_start(self):
        self.now = 1.0
        self.open_items()
        self.now = 4.0
        self.events(item_mode, self.key(SDLK_i))
        self.assertEqual(play_mode.boy.idle_started_at, 0.0)
        self.now = 5.0
        play_mode.update()
        self.assertEqual(play_mode.boy.state, 'SLEEP')

    def test_pause_freezes_balls_and_excludes_time_from_idle(self):
        play_mode.boy.selected_ball = 1
        self.events(play_mode, self.key(SDLK_SPACE))
        fired = self.balls()[0]
        self.now = 2.0
        self.events(play_mode, self.key(SDLK_p))
        self.assertEqual(game_framework.stack, [play_mode, pause_mode])
        self.now = 20.0
        pause_mode.update()
        self.assertEqual(fired.x, 400)
        self.assertEqual(play_mode.boy.idle_started_at, 0.0)
        self.now = 22.0
        self.events(pause_mode, self.key(SDLK_p))
        self.assertEqual(play_mode.boy.idle_started_at, 20.0)
        self.assertIsNone(play_mode.pause_started_at)
        self.now = 24.99
        play_mode.update()
        self.assertEqual(play_mode.boy.state, 'IDLE')
        self.now = 25.0
        play_mode.update()
        self.assertEqual(play_mode.boy.state, 'SLEEP')

    def test_pause_key_release_excludes_only_the_paused_idle_interval(self):
        self.events(play_mode, self.key(SDLK_RIGHT))
        self.now = 2.0
        self.events(play_mode, self.key(SDLK_p))
        self.now = 5.0
        self.events(pause_mode, self.key(SDLK_RIGHT, SDL_KEYUP))
        self.assertEqual(play_mode.boy.idle_started_at, 5.0)
        self.now = 10.0
        self.events(pause_mode, self.key(SDLK_p))
        self.assertEqual(play_mode.boy.idle_started_at, 10.0)
        self.now = 14.99
        play_mode.update()
        self.assertEqual(play_mode.boy.state, 'IDLE')
        self.now = 15.0
        play_mode.update()
        self.assertEqual(play_mode.boy.state, 'SLEEP')

    def test_pause_timestamp_clears_for_running_and_sleeping_states(self):
        self.events(play_mode, self.key(SDLK_RIGHT))
        self.events(play_mode, self.key(SDLK_p))
        self.now = 4.0
        self.events(pause_mode, self.key(SDLK_p))
        self.assertEqual(play_mode.boy.state, 'RUN')
        self.assertIsNone(play_mode.pause_started_at)
        self.events(play_mode, self.key(SDLK_RIGHT, SDL_KEYUP))
        self.now = 9.0
        play_mode.update()
        self.assertEqual(play_mode.boy.state, 'SLEEP')
        self.events(play_mode, self.key(SDLK_p))
        self.now = 20.0
        self.events(pause_mode, self.key(SDLK_p))
        self.assertEqual(play_mode.boy.state, 'SLEEP')
        self.assertIsNone(play_mode.pause_started_at)

    def test_item_inputs_do_not_fire_move_or_open_pause(self):
        play_mode.boy.selected_ball = 1
        self.events(play_mode, self.key(SDLK_2))
        self.assertEqual(play_mode.boy.selected_ball, 1)
        self.open_items()
        self.events(item_mode, self.key(SDLK_SPACE), self.key(SDLK_p),
                    self.key(SDLK_RIGHT), self.key(SDLK_0, SDL_KEYUP))
        self.assertEqual(game_framework.stack, [play_mode, item_mode])
        self.assertEqual(play_mode.boy.state, 'IDLE')
        self.assertEqual(play_mode.boy.pressed_keys, set())
        self.assertEqual(play_mode.boy.selected_ball, 1)
        self.assertEqual(self.balls(), [])

    def test_item_keeps_movement_until_direction_key_is_released(self):
        self.events(play_mode, self.key(SDLK_RIGHT))
        self.open_items()
        start_x = play_mode.boy.x
        item_mode.update()
        self.assertEqual(play_mode.boy.x, start_x + 5)
        self.events(item_mode, self.key(SDLK_RIGHT, SDL_KEYUP))
        item_mode.update()
        self.assertEqual(play_mode.boy.x, start_x + 5)
        self.assertEqual(play_mode.boy.pressed_keys, set())
        self.assertEqual(play_mode.boy.state, 'IDLE')

    def test_key_release_in_same_batch_as_entering_item_is_not_lost(self):
        self.events(play_mode, self.key(SDLK_RIGHT))
        self.events(play_mode, self.key(SDLK_i), self.key(SDLK_RIGHT, SDL_KEYUP))
        self.assertEqual(game_framework.stack, [play_mode, item_mode])
        self.assertEqual(play_mode.boy.pressed_keys, set())
        self.assertEqual(play_mode.boy.state, 'IDLE')

    def test_key_release_in_same_batch_as_leaving_item_is_not_lost(self):
        self.events(play_mode, self.key(SDLK_RIGHT))
        self.open_items()
        self.events(item_mode, self.key(SDLK_i), self.key(SDLK_RIGHT, SDL_KEYUP))
        self.assertEqual(game_framework.stack, [play_mode])
        self.assertEqual(play_mode.boy.pressed_keys, set())
        self.assertEqual(play_mode.boy.state, 'IDLE')

    def test_repeated_item_switches_do_not_duplicate_objects(self):
        play_mode.boy.selected_ball = 2
        self.events(play_mode, self.key(SDLK_SPACE))
        objects = [layer[:] for layer in game_world.world]
        for _ in range(20):
            self.open_items()
            self.events(item_mode, self.key(SDLK_i))
            self.assertEqual(game_framework.stack, [play_mode])
            self.assertEqual(game_world.world, objects)
            self.assertEqual(play_mode.boy.selected_ball, 2)
            self.assertIsNone(play_mode.pause_started_at)

    def test_item_render_composes_once_and_highlights_selected_row(self):
        self.open_items()
        operations = Mock()
        with patch.multiple(item_mode, image=operations.panel,
                            clear_canvas=operations.clear,
                            update_canvas=operations.swap,
                            draw_rectangle=operations.border,
                            get_canvas_width=Mock(return_value=800),
                            get_canvas_height=Mock(return_value=600)), \
                patch.object(game_world, 'render', operations.world):
            for selection, bottom, top in ((0, 336, 396), (1, 270, 330),
                                           (2, 204, 264)):
                with self.subTest(selection=selection):
                    operations.reset_mock()
                    play_mode.boy.selected_ball = selection
                    item_mode.render()
                    self.assertEqual(operations.mock_calls, [
                        call.clear(), call.world(), call.panel.draw(400, 300),
                        call.border(268, bottom, 532, top, 255, 220, 0, filled=False),
                        call.swap(),
                    ])

    def test_pause_does_not_open_item_and_escape_clears_world(self):
        self.events(play_mode, self.key(SDLK_p))
        self.events(pause_mode, self.key(SDLK_i))
        self.assertEqual(game_framework.stack, [play_mode, pause_mode])
        self.events(pause_mode, self.key(SDLK_ESCAPE))
        self.assertEqual(game_framework.stack, [title_mode])
        self.assertIsNone(play_mode.boy)
        self.assertTrue(all(not layer for layer in game_world.world))

    def test_play_escape_returns_to_title(self):
        self.events(play_mode, self.key(SDLK_ESCAPE))
        self.assertEqual(game_framework.stack, [title_mode])
        self.assertIsNone(play_mode.boy)
        self.assertTrue(all(not layer for layer in game_world.world))

    def test_window_close_in_item_cleans_modes_in_reverse_order(self):
        self.finish_modes()
        cleanups = Mock()
        with patch.object(play_mode, 'get_events', return_value=[self.key(SDLK_i)]), \
                patch.object(item_mode, 'get_events',
                             return_value=[SimpleNamespace(type=SDL_QUIT)]), \
                patch.object(play_mode, 'render'), patch.object(item_mode, 'render'), \
                patch.object(item_mode, 'finish', wraps=item_mode.finish) as item_finish, \
                patch.object(play_mode, 'finish', wraps=play_mode.finish) as play_finish, \
                patch.object(game_framework.time, 'sleep',
                             side_effect=[None, None, AssertionError('Loop did not stop')]):
            cleanups.attach_mock(item_finish, 'item')
            cleanups.attach_mock(play_finish, 'play')
            game_framework.run(play_mode)
        self.assertEqual(cleanups.mock_calls, [call.item(), call.play()])
        self.assertEqual(game_framework.stack, [])
        self.assertFalse(game_framework.running)
        self.assertIsNone(play_mode.boy)
        self.assertIsNone(item_mode.image)
        self.assertTrue(all(not layer for layer in game_world.world))

    def test_main_runs_logo_title_and_play_without_opening_a_window(self):
        self.finish_modes()

        def logo_events():
            self.now += 2.0
            return []

        with patch.object(pico2d, 'open_canvas') as open_canvas, \
                patch.object(pico2d, 'close_canvas') as close_canvas, \
                patch.object(logo_mode, 'get_events', side_effect=logo_events) as logo_events_mock, \
                patch.object(title_mode, 'get_events',
                             return_value=[self.key(SDLK_SPACE)]) as title_events, \
                patch.object(play_mode, 'get_events',
                             return_value=[SimpleNamespace(type=SDL_QUIT)]) as play_events, \
                patch.object(logo_mode, 'render'), patch.object(title_mode, 'render'), \
                patch.object(play_mode, 'render'), \
                patch.object(game_framework.time, 'sleep',
                             side_effect=[None, None, None, AssertionError('Loop did not stop')]):
            runpy.run_path(str(Path(__file__).resolve().parents[1] / 'main.py'),
                           run_name='__main__')
        open_canvas.assert_called_once_with()
        close_canvas.assert_called_once_with()
        logo_events_mock.assert_called_once_with()
        title_events.assert_called_once_with()
        play_events.assert_called_once_with()
        self.assertEqual(game_framework.stack, [])
        self.assertIsNone(play_mode.boy)
        self.assertTrue(all(not layer for layer in game_world.world))

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
