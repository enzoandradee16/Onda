import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    objectName: "jukeboxTimers"
    parent: Overlay.overlay; anchors.centerIn: parent
    width: Math.min(540,parent.width-40); padding: 22; modal: true; focus: true
    background: Card {}
    contentItem: ColumnLayout {
        spacing: 14
        Label { text: bridge.translate("Timers da Jukebox"); color: bridge.palette.text; font.pixelSize: 22 }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: bridge.translate("Os timers funcionam juntos e pausam junto com a música."); color: bridge.palette.muted }
        Label { text: bridge.translate("Trocar de música a cada"); color: bridge.palette.text }
        RowLayout {
            SpinBox { id: trackTime; objectName: "trackTimerMinutes"; from: 1; to: 180; value: bridge.playback.trackMinutes || 5; editable: true }
            Label { text: bridge.translate("minutos"); color: bridge.palette.muted }
            ActionButton { text: bridge.translate("Ativar"); enabled: bridge.queuedTracks.length>0; onClicked: bridge.setTrackMinutes(trackTime.value) }
            ActionButton { text: bridge.translate("Desligar"); enabled: bridge.playback.trackMinutes>0; onClicked: bridge.setTrackMinutes(0) }
        }
        Label { visible: bridge.playback.trackMinutes>0; text: bridge.translate("Próxima música em")+" "+workspace.clock(bridge.playback.switchRemaining); color: bridge.palette.accent }
        Label { text: bridge.translate("Parar a reprodução após"); color: bridge.palette.text }
        RowLayout {
            SpinBox { id: stopTime; objectName: "stopTimerMinutes"; from: 1; to: 180; value: 30; editable: true }
            Label { text: bridge.translate("minutos"); color: bridge.palette.muted }
            ActionButton { text: bridge.translate("Ativar"); onClicked: bridge.setSleep(stopTime.value) }
            ActionButton { text: bridge.translate("Desligar"); enabled: bridge.playback.sleepActive; onClicked: bridge.setSleep(0) }
        }
        Label { visible: bridge.playback.sleepActive; text: bridge.translate("Parar em")+" "+workspace.clock(bridge.playback.remaining); color: bridge.palette.accent }
        OndaSwitch { text: bridge.translate("Transição gradual"); checked: bridge.playback.gradual; onToggled: bridge.setGradualTransition(checked) }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: bridge.translate("Sobrepõe a música atual e a próxima. Ajuste os segundos da transição em Configurações → Áudio. O timer de parada reduz nos últimos 10 segundos."); color: bridge.palette.muted }
        ActionButton { Layout.alignment: Qt.AlignRight; primary: true; text: bridge.translate("Pronto"); onClicked: popup.close() }
    }
}
