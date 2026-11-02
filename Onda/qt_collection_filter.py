"""Filter collection tracks without changing their selection or source indexes."""

from PySide6.QtCore import QSortFilterProxyModel, Property, Signal, Slot, Qt
from text_search import normalize


class CollectionFilterModel(QSortFilterProxyModel):
    countChanged = Signal()
    filtersChanged = Signal()

    def __init__(self, source, parent=None):
        super().__init__(parent)
        self._filters = dict(title='', artist='', album='', date='')
        self._terms = {}
        self.collection_kind = 'playlist'
        self.collection_date = ''
        self.setSourceModel(source)
        self.rowsInserted.connect(self.countChanged)
        self.rowsRemoved.connect(self.countChanged)
        self.modelReset.connect(self.countChanged)

    @Property(int, notify=countChanged)
    def count(self):
        return self.rowCount()

    @Property('QVariantMap', notify=filtersChanged)
    def filters(self):
        return dict(self._filters)

    @Slot(str, str, str)
    @Slot(str, str, str, str)
    def setFilters(self, title, artist, album, date=''):
        self.beginFilterChange()
        self._filters = dict(title=title, artist=artist, album=album, date=date)
        self._terms = {
            key: normalize(value).split()
            for key, value in self._filters.items()
            if key != 'date'
        }
        self.endFilterChange(self.Direction.Rows)
        self.filtersChanged.emit()
        self.countChanged.emit()

    @Slot(str, bool)
    def setOrdering(self, field, descending):
        self._sort_field = field
        self.sort(
            0 if field else -1, Qt.DescendingOrder if descending else Qt.AscendingOrder
        )
        self.invalidate()

    def lessThan(self, left, right):
        field = getattr(self, '_sort_field', '')

        def value(index):
            row = self.sourceModel().rows[index.row()]
            raw = (
                row.get('artists') or row.get('artist')
                if field == 'artist'
                else row.get(field)
            )
            return normalize(str(raw or ''))

        a, b = value(left), value(right)
        if bool(a) != bool(b):
            return bool(a) if self.sortOrder() == Qt.AscendingOrder else not bool(a)
        return a < b

    def filterAcceptsRow(self, row, parent):
        entry = self.sourceModel().rows[row]
        values = dict(
            title=entry.get('title') or '',
            artist=entry.get('artists') or entry.get('artist') or '',
            album=entry.get('album') or '',
        )
        date = self.collection_date or (
            entry.get('release_date') if self.collection_kind == 'album' else ''
        )
        if not date_matches(date, self._filters['date']):
            return False
        return all(
            all(term in normalize(str(values[key])) for term in terms)
            for key, terms in self._terms.items()
        )

    def data(self, index, role):
        value = super().data(index, role)
        if role == Qt.UserRole + 1 and isinstance(value, dict):
            return dict(value, _source_row=self.mapToSource(index).row())
        return value

    @Slot(int, result=int)
    def sourceRow(self, row):
        return (
            self.mapToSource(self.index(row, 0)).row()
            if 0 <= row < self.rowCount()
            else -1
        )

    def visible_rows(self):
        return [
            self.sourceModel().rows[self.sourceRow(row)]
            for row in range(self.rowCount())
        ]


def date_matches(value, query):
    import re

    term = str(query or '').strip()
    if not term:
        return True
    if re.fullmatch(r'\d{2}/\d{2}/\d{4}', term):
        term = '-'.join(reversed(term.split('/')))
    return str(value or '').startswith(term)
