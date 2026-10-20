import QtQuick
import QtQuick.Controls
Slider {
    id: control
    orientation: Qt.Vertical; from: -12; to: 12
    implicitHeight: 185; implicitWidth: 40
    background: Rectangle {
        x: control.leftPadding + control.availableWidth / 2 - width / 2
        y: control.topPadding
        width: 4; height: control.availableHeight; radius: 2
        color: bridge.palette.mode === "Preto puro" ? "#555b64" : bridge.palette.line
        Rectangle { x: 0; y: Math.min(0.5, control.visualPosition)*parent.height; width: parent.width; height: Math.abs(control.visualPosition-0.5)*parent.height; radius: 2; color: bridge.palette.accent }
    }
    handle: Rectangle {
        x: control.leftPadding + control.availableWidth/2 - width/2
        y: control.topPadding + control.visualPosition * (control.availableHeight-height)
        implicitWidth: control.pressed ? 21 : 18; implicitHeight: implicitWidth; radius: width/2
        color: bridge.palette.accent; border.color: control.activeFocus ? bridge.palette.text : bridge.palette.surface; border.width: 2
    }
}
