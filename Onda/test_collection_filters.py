"""Collection filters retain source identity and selected hidden rows."""

import os
import unittest


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt models')
class CollectionFilterTests(unittest.TestCase):
    def test_combined_filters_keep_correct_source_row_and_selection(self):
        from qt_models_ui import RowsModel
        from qt_collection_filter import CollectionFilterModel

        rows = RowsModel()
        rows.replace(
            [
                dict(title='Other', artists=['B'], album='Else', checked=True),
                dict(
                    title='Coração カタカナ',
                    artists=['Cindy'],
                    album='Angel Touch',
                    release_date='1990-05-25',
                    checked=True,
                ),
            ]
        )
        proxy = CollectionFilterModel(rows)
        proxy.collection_kind = 'album'
        proxy.setFilters('coracao かたかな', 'cindy', 'angel', '25/05/1990')
        self.assertEqual(proxy.count, 1)
        self.assertEqual(proxy.sourceRow(0), 1)
        from PySide6.QtCore import Qt

        self.assertEqual(
            proxy.data(proxy.index(0, 0), Qt.UserRole + 1)['_source_row'], 1
        )
        rows.update(proxy.sourceRow(0), checked=False)
        self.assertTrue(rows.rows[0]['checked'])
        self.assertFalse(proxy.visible_rows()[0]['checked'])
        proxy.setFilters('', '', '')
        self.assertEqual(proxy.count, 2)

    def test_playlist_creation_date_never_uses_track_release_date(self):
        from qt_models_ui import RowsModel
        from qt_collection_filter import CollectionFilterModel

        rows = RowsModel()
        rows.replace([dict(title='Song', release_date='1980')])
        proxy = CollectionFilterModel(rows)
        proxy.setFilters('', '', '', '1980')
        self.assertEqual(proxy.count, 0)
        proxy.collection_date = '2020-02-01'
        proxy.setFilters('', '', '', '2020')
        self.assertEqual(proxy.count, 1)

    def test_sorting_keeps_source_indexes_and_unknown_dates_last(self):
        from qt_models_ui import RowsModel
        from qt_collection_filter import CollectionFilterModel

        rows = RowsModel()
        rows.replace(
            [
                dict(title='Unknown'),
                dict(title='Old', release_date='1990'),
                dict(title='New', release_date='2020'),
            ]
        )
        proxy = CollectionFilterModel(rows)
        proxy.setOrdering('release_date', True)
        self.assertEqual([proxy.sourceRow(i) for i in range(3)], [2, 1, 0])
        proxy.setOrdering('release_date', False)
        self.assertEqual([proxy.sourceRow(i) for i in range(3)], [1, 2, 0])
        proxy.setOrdering('', False)
        self.assertEqual([proxy.sourceRow(i) for i in range(3)], [0, 1, 2])
