import QtQuick
import QtQuick.Controls
TextArea {
    id: control
    leftPadding: 12; rightPadding: 12
    topPadding: 8; bottomPadding: 8
    selectByMouse: true
    color: bridge.palette.text
    placeholderTextColor: bridge.palette.muted
    background: Rectangle {
        radius: 14
        color: bridge.palette.input
        border.color: control.activeFocus ? bridge.palette.accent : bridge.palette.line
        border.width: control.activeFocus ? 2 : 1
    }
}
