import QtQuick
import QtQuick.Controls
OndaTextField {
    id: recorder
    property string actionKey: ""
    property string sequence: ""
    property bool recording: false
    objectName: "shortcutRecorder_"+actionKey
    readOnly: true
    selectByMouse: false
    text: recording ? bridge.translate("Pressione o atalho…") : sequence
    Accessible.name: bridge.translate("Escolher atalho")
    Accessible.description: bridge.translate("Clique ou pressione Enter para escolher o atalho. Esc cancela.")
    onActiveFocusChanged: if (!activeFocus) recording=false
    MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: {recorder.forceActiveFocus();recorder.recording=true} }
    Keys.onShortcutOverride: function(event) { if (recording) event.accepted=true }
    Keys.onPressed: function(event) {
        if (!recording) {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                recording=true;event.accepted=true
            }
            return
        }
        event.accepted=true
        if (event.isAutoRepeat) return
        if (event.key === Qt.Key_Escape) { recording=false;return }
        if ([Qt.Key_Control,Qt.Key_Shift,Qt.Key_Alt,Qt.Key_Meta,Qt.Key_AltGr].indexOf(event.key)>=0) return
        if (workspace.captureShortcut(actionKey,event.key,event.modifiers)) recording=false
    }
}
