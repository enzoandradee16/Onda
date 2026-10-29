import QtQuick
import QtQuick.Controls
ToolButton {
    id:button
    property string glyph:"catalog"
    implicitWidth:32;implicitHeight:32
    Accessible.name:text
    ToolTip.visible:hovered;ToolTip.text:text
    contentItem:Item {LineIcon {anchors.centerIn:parent;width:20;height:20;glyph:button.glyph;ink:bridge.palette.muted}}
    background:Rectangle {radius:5;color:button.hovered||button.activeFocus?bridge.palette.hover:"transparent"}
}
