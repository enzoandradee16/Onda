import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    property bool effects: false
    objectName: "jukeboxTimers"
    parent: Overlay.overlay; anchors.centerIn: parent
    width: Math.min(540,parent.width-40); padding: 22; modal: true; focus: true
    background: Card {}
    contentItem: ColumnLayout {
        spacing: 14
        Label { text: bridge.translate(popup.effects ? "Timers de Efeitos" : "Timers da Jukebox"); color: bridge.palette.text; font.pixelSize: 22 }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: bridge.translate("Os timers funcionam juntos e pausam junto com a música."); color: bridge.palette.muted }
        Label { text: bridge.translate("Trocar de música a cada"); color: bridge.palette.text }
        RowLayout {
            SpinBox { id: trackTime; objectName: "trackTimerMinutes"; from: 1; to: 180; value: (popup.effects ? workspace.values.effectsTrackMinutes : bridge.playback.trackMinutes) || 5; editable: true }
            Label { text: bridge.translate("minutos"); color: bridge.palette.muted }
            ActionButton { text: bridge.translate("Ativar"); enabled: popup.effects ? workspace.values.effectsQueue.length>0 : bridge.queuedTracks.length>0; onClicked: popup.effects ? workspace.invoke("effects_timer",{next:true,minutes:trackTime.value}) : bridge.setTrackMinutes(trackTime.value) }
            ActionButton { text: bridge.translate("Desligar"); enabled: (popup.effects ? workspace.values.effectsTrackMinutes : bridge.playback.trackMinutes)>0; onClicked: popup.effects ? workspace.invoke("effects_timer",{next:true,minutes:0}) : bridge.setTrackMinutes(0) }
        }
        Label { visible: (popup.effects ? workspace.values.effectsTrackMinutes : bridge.playback.trackMinutes)>0; text: bridge.translate("Próxima música em")+" "+workspace.clock((popup.effects ? workspace.values.effectsSwitchRemaining : bridge.playback.switchRemaining)); color: bridge.palette.accent }
        Label { text: bridge.translate("Parar a reprodução após"); color: bridge.palette.text }
        RowLayout {
            SpinBox { id: stopTime; objectName: "stopTimerMinutes"; from: 1; to: 180; value: 30; editable: true }
            Label { text: bridge.translate("minutos"); color: bridge.palette.muted }
            ActionButton { text: bridge.translate("Ativar"); onClicked: popup.effects ? workspace.invoke("effects_timer",{minutes:stopTime.value}) : bridge.setSleep(stopTime.value) }
            ActionButton { text: bridge.translate("Desligar"); enabled: (popup.effects ? workspace.values.effectsStopRemaining>0 : bridge.playback.sleepActive); onClicked: popup.effects ? workspace.invoke("effects_timer",{minutes:0}) : bridge.setSleep(0) }
        }
        Label { visible: (popup.effects ? workspace.values.effectsStopRemaining>0 : bridge.playback.sleepActive); text: bridge.translate("Parar em")+" "+workspace.clock((popup.effects ? workspace.values.effectsStopRemaining : bridge.playback.remaining)); color: bridge.palette.accent }
        OndaSwitch { text: bridge.translate("Transição gradual"); checked: popup.effects ? workspace.preferences.jukebox_gradual_transition : bridge.playback.gradual; onToggled: popup.effects ? workspace.setSetting("jukebox_gradual_transition",checked) : bridge.setGradualTransition(checked) }
        Label { Layout.fillWidth: true; wrapMode: Text.WordWrap; text: bridge.translate(popup.effects ? "Sobrepõe a música atual e a próxima. Ajuste os segundos da transição em Configurações → Áudio." : "Sobrepõe a música atual e a próxima. Ajuste os segundos da transição em Configurações → Áudio. O timer de parada reduz nos últimos 10 segundos."); color: bridge.palette.muted }
        ActionButton { Layout.alignment: Qt.AlignRight; primary: true; text: bridge.translate("Pronto"); onClicked: popup.close() }
    }
}
