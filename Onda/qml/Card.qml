import QtQuick
Rectangle {
    color: bridge.palette.surface
    radius: 12
    border.color: bridge.palette.line
    border.width: bridge.palette.flat_black ? 0 : 1
    Behavior on color { ColorAnimation { duration: bridge.animations ? 180 : 0 } }
}
