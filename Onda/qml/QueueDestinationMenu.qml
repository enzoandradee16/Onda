import QtQuick
import QtQuick.Controls
Menu {
    id: destination
    property int recordIndex: -1
    width: Math.round(300*bridge.fontScale)
    background: Card {}
    OndaMenuItem { objectName: "downloadDestination"; text: bridge.translate("Fila de downloads"); onTriggered: workspace.invoke("catalog_add",{index:destination.recordIndex}) }
    OndaMenuItem {objectName:"effectsPlaybackDestination";text:bridge.translate("Fila de reprodução de Efeitos");enabled:!["effects_load","effects_queue_info","effects_collection"].some(function(name){return workspace.activity.busy.indexOf(name)>=0});onTriggered:workspace.invoke("effects_add",{index:destination.recordIndex})}
    OndaMenuItem { objectName: "playbackDestination"; text: bridge.translate("Fila de reprodução do Jukebox"); onTriggered: workspace.invoke("jukebox_add",{index:destination.recordIndex}) }
}
