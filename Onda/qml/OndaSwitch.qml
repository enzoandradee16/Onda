import QtQuick
import QtQuick.Controls
Switch {
    id: control
    implicitHeight: 36
    implicitWidth: Math.max(48, label.implicitWidth+62)
    rightPadding: 62
    indicator: Rectangle {
        x: control.width-width; y: (control.height-height)/2
        width: 44; height: 25; radius: 13
        color: control.checked ? bridge.palette.accent : (bridge.palette.mode === "Preto puro" ? "#40464e" : bridge.palette.line)
        Behavior on color { ColorAnimation { duration: bridge.animations ? 130 : 0 } }
        Rectangle {
            x: control.checked ? parent.width-width-3 : 3; y: 3
            width: 19; height: 19; radius: 10; color: control.checked ? bridge.palette.accent_text : bridge.palette.surface
            Behavior on x { NumberAnimation { duration: bridge.animations ? 150 : 0; easing.type: Easing.OutCubic } }
        }
    }
    contentItem: Text { id: label; text: control.text; color: bridge.palette.text; font.pixelSize: Math.round(13*bridge.fontScale); verticalAlignment: Text.AlignVCenter }
}
