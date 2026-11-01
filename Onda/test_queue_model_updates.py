"""Queue edits preserve model identity instead of resetting the whole list."""

import os
import unittest


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt models')
class QueueModelUpdateTests(unittest.TestCase):
    def test_reorder_insert_remove_and_edit_without_reset(self):
        from PySide6.QtTest import QSignalSpy
        from qt_models_ui import RowsModel

        model = RowsModel()
        model.replace([dict(id='a'), dict(id='b'), dict(id='c')])
        resets = QSignalSpy(model.modelReset)
        moves = QSignalSpy(model.rowsMoved)
        model.replace([dict(id='c'), dict(id='a', title='Updated'), dict(id='d')])
        self.assertEqual([row['id'] for row in model.rows], ['c', 'a', 'd'])
        self.assertEqual(model.rows[1]['title'], 'Updated')
        self.assertEqual(resets.count(), 0)
        self.assertEqual(moves.count(), 1)
        model.replace([])
        self.assertEqual(model.rowCount(), 0)
        self.assertEqual(resets.count(), 0)
