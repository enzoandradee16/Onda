import QtQuick
Rectangle {
    color: bridge.palette.flat_black ? "#0c0f13" : bridge.palette.surface
    radius: 12
    border.color: bridge.palette.flat_black ? "#303945" : bridge.palette.line
    border.width: 1
    Behavior on color { ColorAnimation { duration: bridge.animations ? 180 : 0 } }
}
