import QtQuick
import QtQuick.Controls
ProgressBar {
    id: control
    property color fillColor: bridge.palette.accent
    property color trackColor: bridge.palette.flat_black ? "#36404c" : bridge.palette.line
    implicitHeight: 8
    background: Rectangle { implicitHeight: 8; radius: height/2; color: control.trackColor }
    contentItem: Item {
        implicitHeight: 8
        clip: true
        Rectangle {
            id: fill
            height: parent.height; radius: height/2; color: control.fillColor
            width: control.indeterminate ? parent.width*0.3 : parent.width*control.visualPosition
            property real phase: 0
            x: control.indeterminate ? (parent.width+width)*phase-width : 0
            NumberAnimation on phase {
                running: control.indeterminate && control.visible
                loops: Animation.Infinite
                from: 0; to: 1; duration: 1200; easing.type: Easing.InOutQuad
            }
        }
    }
}
