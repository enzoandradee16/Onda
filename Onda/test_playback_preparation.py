import unittest
from playback_preparation import preparation_ahead
from preferences import PreferenceStore


class PreparationPreferenceTests(unittest.TestCase):
    def test_choices_are_persisted_and_invalid_values_fall_back_to_two(self):
        for value in (1, 2, 3, 5, '1', '2', '3', '5'):
            self.assertEqual(preparation_ahead(value), int(value))
            self.assertEqual(
                PreferenceStore.clean({'playback_prepare_ahead': value})[
                    'playback_prepare_ahead'
                ],
                int(value),
            )
        for value in (None, True, False, 0, 4, 100, '5000', 2.5, float('inf'), {}, []):
            self.assertEqual(preparation_ahead(value), 2)
            self.assertEqual(
                PreferenceStore.clean({'playback_prepare_ahead': value})[
                    'playback_prepare_ahead'
                ],
                2,
            )
