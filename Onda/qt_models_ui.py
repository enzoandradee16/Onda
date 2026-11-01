"""Qt list models with row updates instead of rebuilding long queues."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, Property, Slot


class RowsModel(QAbstractListModel):
    countChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []
        self._identity_index = None

    def roleNames(self):
        return {Qt.UserRole + 1: b'entry'}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role):
        if index.isValid() and role == Qt.UserRole + 1:
            return dict(self.rows[index.row()])

    @Property(int, notify=countChanged)
    def count(self):
        return len(self.rows)

    @Slot(int, result='QVariantMap')
    def get(self, index):
        return dict(self.rows[index]) if 0 <= index < len(self.rows) else {}

    def index_for_id(self, identity):
        cached = self._identity_index
        index = cached.get(identity, -1) if cached is not None else -1
        if (
            cached is None
            or getattr(self, '_identity_source', None) is not self.rows
            or getattr(self, '_identity_count', -1) != len(self.rows)
            or index >= 0
            and self.rows[index].get('id') != identity
        ):
            self._identity_index = {}
            for index, row in enumerate(self.rows):
                self._identity_index.setdefault(row.get('id'), index)
            self._identity_source = self.rows
            self._identity_count = len(self.rows)
        return self._identity_index.get(identity, -1)

    def replace(self, rows):
        rows = [dict(row) for row in rows]
        if rows == self.rows:
            return
        self._identity_index = None
        old_count = len(self.rows)
        if len(rows) > old_count and rows[:old_count] == self.rows:
            self.beginInsertRows(QModelIndex(), old_count, len(rows) - 1)
            self.rows.extend(rows[old_count:])
            self.endInsertRows()
            self.countChanged.emit()
            return
        if len(rows) < old_count and rows == self.rows[: len(rows)]:
            self.beginRemoveRows(QModelIndex(), len(rows), old_count - 1)
            del self.rows[len(rows) :]
            self.endRemoveRows()
            self.countChanged.emit()
            return
        # Stable identities let QML retain delegates, focus and scroll position.
        if len(rows) == old_count and all(
            'id' in row and row['id'] == old.get('id')
            for row, old in zip(rows, self.rows)
        ):
            for index, row in enumerate(rows):
                if row != self.rows[index]:
                    self.rows[index] = row
                    item = self.index(index)
                    self.dataChanged.emit(item, item, list(self.roleNames()))
            return
        ids = [row.get('id') for row in rows]
        old_ids = [row.get('id') for row in self.rows]
        if (
            len(ids) == len(old_ids)
            and len(ids) > 128
            and None not in ids
            and len(set(ids)) == len(ids)
            and set(ids) == set(old_ids)
        ):
            # A bulk permutation is linear and keeps selections/persistent indexes.
            persistent = self.persistentIndexList()
            positions = {identity: index for index, identity in enumerate(ids)}
            identities = [old_ids[index.row()] for index in persistent]
            self.layoutAboutToBeChanged.emit()
            self.rows = rows
            self.changePersistentIndexList(
                persistent, [self.index(positions[key]) for key in identities]
            )
            self.layoutChanged.emit()
            if rows:
                self.dataChanged.emit(
                    self.index(0), self.index(len(rows) - 1), list(self.roleNames())
                )
            return
        if (
            all(identity is not None for identity in ids + old_ids)
            and len(set(ids)) == len(ids)
            and len(set(old_ids)) == len(old_ids)
        ):
            wanted = set(ids)
            index = len(self.rows) - 1
            while index >= 0:
                if self.rows[index]['id'] in wanted:
                    index -= 1
                    continue
                last = index
                while index >= 0 and self.rows[index]['id'] not in wanted:
                    index -= 1
                self.beginRemoveRows(QModelIndex(), index + 1, last)
                del self.rows[index + 1 : last + 1]
                self.endRemoveRows()
            for target, row in enumerate(rows):
                found = next(
                    (
                        i
                        for i in range(target, len(self.rows))
                        if self.rows[i]['id'] == row['id']
                    ),
                    -1,
                )
                if found < 0:
                    self.beginInsertRows(QModelIndex(), target, target)
                    self.rows.insert(target, row)
                    self.endInsertRows()
                else:
                    if found != target:
                        self.beginMoveRows(
                            QModelIndex(), found, found, QModelIndex(), target
                        )
                        self.rows.insert(target, self.rows.pop(found))
                        self.endMoveRows()
                    if self.rows[target] != row:
                        self.rows[target] = row
                        item = self.index(target)
                        self.dataChanged.emit(item, item, list(self.roleNames()))
            if len(rows) != old_count:
                self.countChanged.emit()
            return
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()
        if len(rows) != old_count:
            self.countChanged.emit()

    def update(self, index, **values):
        if 0 <= index < len(self.rows) and any(
            key not in self.rows[index] or self.rows[index][key] != value
            for key, value in values.items()
        ):
            if 'id' in values and values['id'] != self.rows[index].get('id'):
                self._identity_index = None
            self.rows[index].update(values)
            item = self.index(index)
            self.dataChanged.emit(item, item, list(self.roleNames()))


class QueueRowsModel(RowsModel):
    """Reconcile playback queues in Python, retaining QML delegates."""

    def roleNames(self):
        return {Qt.UserRole + 1: b'modelData', Qt.UserRole + 2: b'group'}

    def data(self, index, role):
        if index.isValid() and role == Qt.UserRole + 2:
            return self.rows[index.row()].get('group', '')
        return super().data(index, role)

    @Slot('QVariantList')
    def setRows(self, rows):
        self.replace(rows)
