import QtQuick
import QtQuick.Controls
MenuItem {
    id: control
    leftPadding:12;rightPadding:12;topPadding:8;bottomPadding:8
    font.family:bridge.interfaceFamily
    font.pixelSize:Math.round(14*bridge.fontScale)
    implicitWidth:contentItem.implicitWidth+leftPadding+rightPadding
    implicitHeight: visible ? Math.max(34*bridge.fontScale,implicitContentHeight+topPadding+bottomPadding) : 0
    height: visible ? implicitHeight : 0
    contentItem: Label { text: control.text; font: control.font; elide:Text.ElideRight; color: control.highlighted ? bridge.palette.accent_text : bridge.palette.text; opacity: control.enabled ? 1 : 0.45; verticalAlignment: Text.AlignVCenter }
    background: Rectangle { radius:5; color:control.highlighted?bridge.palette.accent:"transparent" }
}
