import QtQuick
import QtQuick.Controls
Menu {
    id: destination
    property int recordIndex: -1
    width: Math.round(300*bridge.fontScale)
    background: Card {}
    OndaMenuItem { objectName: "downloadDestination"; text: bridge.translate("Fila de downloads"); onTriggered: workspace.invoke("catalog_add",{index:destination.recordIndex}) }
    OndaMenuItem { objectName: "playbackDestination"; text: bridge.translate("Fila de reprodução"); onTriggered: workspace.invoke("jukebox_add",{index:destination.recordIndex}) }
}
