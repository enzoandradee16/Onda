"""Qt list models with row updates instead of rebuilding long queues."""

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, Property, Slot


class RowsModel(QAbstractListModel):
    countChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = []

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

    def replace(self, rows):
        rows = [dict(row) for row in rows]
        if rows == self.rows:
            return
        old_count = len(self.rows)
        # Stable identities let QML retain delegates, focus and scroll position.
        if len(rows) == old_count and all(
            'id' in row and row['id'] == old.get('id')
            for row, old in zip(rows, self.rows)
        ):
            for index, row in enumerate(rows):
                if row != self.rows[index]:
                    self.rows[index] = row
                    item = self.index(index)
                    self.dataChanged.emit(item, item, [Qt.UserRole + 1])
            return
        ids = [row.get('id') for row in rows]
        old_ids = [row.get('id') for row in self.rows]
        if (
            all(identity is not None for identity in ids + old_ids)
            and len(set(ids)) == len(ids)
            and len(set(old_ids)) == len(old_ids)
        ):
            wanted = set(ids)
            for index in range(len(self.rows) - 1, -1, -1):
                if self.rows[index]['id'] not in wanted:
                    self.beginRemoveRows(QModelIndex(), index, index)
                    self.rows.pop(index)
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
                        self.dataChanged.emit(item, item, [Qt.UserRole + 1])
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
            self.rows[index].update(values)
            item = self.index(index)
            self.dataChanged.emit(item, item, [Qt.UserRole + 1])
