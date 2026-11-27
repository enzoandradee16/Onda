import QtQuick
import QtQuick.Window
import QtQuick.Controls

TextField {
    id: control
    implicitHeight: Math.max(44, Math.round(44 * bridge.fontScale))
    leftPadding: 12
    rightPadding: 12
    topPadding: 8
    bottomPadding: 8
    selectByMouse: true
    color: bridge.palette.text
    placeholderTextColor: Qt.tint(bridge.palette.muted, Qt.alpha(bridge.palette.text, .45 * (control.Window.window?.controlTintLevel ?? 0)))
    background: Rectangle {
        radius: 14
        color: Qt.alpha(bridge.palette.input, 1 - .36 * (control.Window.window?.controlTintLevel ?? 0))
        border.color: control.activeFocus ? bridge.palette.accent : bridge.palette.line
        border.width: control.activeFocus ? 2 : 1
    }
}
