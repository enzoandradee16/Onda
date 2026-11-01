import QtQuick
import QtQuick.Controls
ScrollBar {
    id: bar
    objectName: "ondaScrollBar"
    policy: ScrollBar.AsNeeded
    interactive: true
    minimumSize: 0.06
    padding: 2
    contentItem: Rectangle {
        implicitWidth: 8; implicitHeight: 8
        radius: 4
        color: bar.pressed || bar.hovered ? bridge.palette.accent : bridge.palette.muted
        opacity: bar.pressed || bar.hovered ? 1 : 0.65
    }
    background: Rectangle {
        implicitWidth: 12; implicitHeight: 12
        radius: 6
        color: bridge.palette.muted
        opacity: 0.10
    }
}
