import QtQuick
import Onda 1.0
QueueRowsModel {
    property var rows: []
    onRowsChanged: setRows(rows)
}
