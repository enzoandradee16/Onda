import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Button {
    id: control
    property bool primary: false
    property string symbol: ""
    implicitHeight: Math.max(34,Math.round(42*bridge.spacing))
    implicitWidth: Math.max(42, label.implicitWidth + 32)
    hoverEnabled: true
    opacity: enabled ? 1 : 0.45
    scale: down ? 0.97 : 1
    Behavior on scale { NumberAnimation { duration: bridge.animations ? 100 : 0; easing.type: Easing.OutCubic } }
    background: Rectangle {
        radius: 8
        color: control.primary ? (control.hovered ? bridge.palette.accent_hover : bridge.palette.accent) : (control.hovered ? bridge.palette.hover : bridge.palette.surface)
        border.color: control.primary ? "transparent" : bridge.palette.line
        Behavior on color { ColorAnimation { duration: bridge.animations ? 120 : 0 } }
    }
    contentItem: Text {
        id: label
        text: (control.symbol ? control.symbol + "  " : "") + control.text
        color: control.primary ? bridge.palette.accent_text : bridge.palette.text
        font.pixelSize: Math.round(14*bridge.fontScale); font.weight: control.primary ? Font.DemiBold : Font.Medium
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
}
