import os
import unittest
from unittest.mock import Mock


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class RowsModelTests(unittest.TestCase):
    def setUp(self):
        global RowsModel
        from qt_models_ui import RowsModel

    def test_refresh_updates_only_changed_identity_without_reset(self):
        model = RowsModel()
        model.replace(
            [{'id': 1, 'state': 'waiting', 'old': True}, {'id': 2, 'state': 'waiting'}]
        )
        reset = Mock()
        changed = Mock()
        count = Mock()
        model.modelReset.connect(reset)
        model.dataChanged.connect(changed)
        model.countChanged.connect(count)
        model.replace([{'id': 1, 'state': 'done'}, {'id': 2, 'state': 'waiting'}])
        reset.assert_not_called()
        count.assert_not_called()
        self.assertEqual(changed.call_count, 1)
        self.assertEqual(changed.call_args.args[0].row(), 0)
        self.assertNotIn('old', model.rows[0])

    def test_identical_refresh_and_update_emit_nothing(self):
        model = RowsModel()
        model.replace([{'id': 1, 'state': 'waiting'}])
        changed = Mock()
        reset = Mock()
        model.dataChanged.connect(changed)
        model.modelReset.connect(reset)
        model.replace([{'id': 1, 'state': 'waiting'}])
        model.update(0, state='waiting')
        changed.assert_not_called()
        reset.assert_not_called()

    def test_reordering_resets_but_only_resizing_notifies_count(self):
        model = RowsModel()
        model.replace([{'id': 1}, {'id': 2}])
        reset = Mock()
        count = Mock()
        model.modelReset.connect(reset)
        model.countChanged.connect(count)
        model.replace([{'id': 2}, {'id': 1}])
        reset.assert_called_once()
        count.assert_not_called()
        model.replace([])
        count.assert_called_once()
        self.assertEqual(model.count, 0)
