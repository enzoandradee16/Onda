import QtQuick
import QtQuick.Controls
PlaybackButton {
    id: button
    objectName: "scrollToTop"
    required property var target
    required property Item viewport
    parent: viewport
    anchors.right: parent.right
    anchors.bottom: parent.bottom
    anchors.rightMargin: 20
    anchors.bottomMargin: 16
    z: 100
    glyph: "up"
    primary: true
    visible: !!target && target.contentY - (target.originY || 0) > 0
    Accessible.name: bridge.translate("Voltar ao início")
    ToolTip.visible: hovered
    ToolTip.text: Accessible.name
    onClicked: {
        if (typeof target.positionViewAtBeginning === "function") target.positionViewAtBeginning()
        else target.contentY = target.originY || 0
    }
}
