import QtQuick
import QtQuick.Controls
Slider {
    id: control
    implicitHeight: 34
    from: 0; to: 100
    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        implicitWidth: 180; implicitHeight: 5
        width: control.availableWidth; height: implicitHeight; radius: 3
        color: bridge.palette.mode === "Preto puro" ? "#555b64" : bridge.palette.line
        Rectangle { width: control.visualPosition * parent.width; height: parent.height; radius: 3; color: bridge.palette.accent }
    }
    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        implicitWidth: control.pressed ? 21 : 18; implicitHeight: implicitWidth
        radius: width/2; color: bridge.palette.accent
        border.color: control.activeFocus ? bridge.palette.text : bridge.palette.surface; border.width: 2
        Behavior on implicitWidth { NumberAnimation { duration: bridge.animations ? 90 : 0 } }
    }
}
