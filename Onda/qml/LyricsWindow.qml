import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    objectName: "lyricsWindow"
    parent: Overlay.overlay; anchors.centerIn: parent
    width: Math.min(740,parent.width-48); height: Math.min(520,parent.height-70)
    modal: false; focus: true; padding: 24
    property var frame: ({text:"",position:0,duration:0,jukebox:true})
    property var lyricLines: []
    property int lyricRevision: -1
    background: Card {}
    Timer { interval: 80; running: popup.opened; repeat: true; onTriggered: { var next=workspace.lyricsClock(true);if(next.revision!==popup.lyricRevision){popup.lyricLines=workspace.lyricsDocument();popup.lyricRevision=next.revision;}popup.frame=next } }
    contentItem: ColumnLayout {
        RowLayout { Layout.fillWidth: true
            Label { text: bridge.translate("Letra"); color: bridge.palette.text; Layout.fillWidth: true; font.pixelSize: 24 }
            TaskButton { idleText: bridge.translate("Buscar letra online"); operation: "lyrics_online" }
            ActionButton { text: bridge.translate("Escolher letra"); onClicked: workspace.invoke("pick",{kind:popup.frame.jukebox ? "jukeboxLyrics" : "effectLyrics"}) }
            ActionButton { text: bridge.translate("Pronto"); onClicked: popup.close() }
        }
        OndaListView {
            id: linesView; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 18
            model: popup.lyricLines
            property int activeLine: popup.frame.active === undefined ? -1 : popup.frame.active
            onActiveLineChanged: if(activeLine>=0)Qt.callLater(function(){linesView.positionViewAtIndex(linesView.activeLine,ListView.Center)})

            delegate: Label {
                required property var modelData; required property int index
                TapHandler { onTapped: workspace.seekLyrics(modelData.time,popup.frame.jukebox) }
                width: linesView.contentAreaWidth; text: index===linesView.activeLine ? popup.frame.text : modelData.text
                textFormat: index===linesView.activeLine ? Text.RichText : Text.PlainText
                wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                color: index===linesView.activeLine ? bridge.palette.accent : bridge.palette.muted
                font.pixelSize: 28; scale: index===linesView.activeLine && workspace.preferences.lyrics_animation === "Zoom" ? 1 : 0.97;
                Behavior on scale { NumberAnimation { duration: workspace.preferences.lyrics_animation === "Desativada" ? 0 : 180 } }
                opacity: index===linesView.activeLine ? 1 : 0.55
                Behavior on opacity { NumberAnimation { duration: workspace.preferences.lyrics_animation === "Desativada" ? 0 : 180 } }
            }
        }
        OndaSlider {
            id:lyricsTimeline;objectName:"lyricsTimeline";property real previewPosition:0;bufferedValue:popup.frame.jukebox?bridge.sourceBufferedEnd:popup.frame.duration
            Layout.fillWidth:true;from:0;to:Math.max(1,popup.frame.duration)
            Binding {target:lyricsTimeline;property:"value";value:popup.frame.position;when:!lyricsTimeline.pressed;restoreMode:Binding.RestoreNone}
            onMoved:{previewPosition=value;if(!pressed)workspace.seekLyrics(value,popup.frame.jukebox)}
            onPressedChanged:{if(pressed)previewPosition=value;else workspace.seekLyrics(previewPosition,popup.frame.jukebox)}
        }
        RowLayout { Layout.fillWidth: true
            Label { text: workspace.clock(lyricsTimeline.pressed?lyricsTimeline.previewPosition:popup.frame.position); color: bridge.palette.muted; Layout.fillWidth: true }
            PlaybackButton { glyph: "previous"; Accessible.name: bridge.translate("Retroceder"); enabled: popup.frame.jukebox ? bridge.stateValue(bridge.stateRevision,"ready") : popup.frame.duration>0; onClicked: { if(popup.frame.jukebox)bridge.previousTrack();else workspace.seekLyrics(0,false) } }
            PlaybackButton { glyph: (popup.frame.jukebox ? bridge.stateValue(bridge.stateRevision,"playing") && !bridge.stateValue(bridge.stateRevision,"paused") : workspace.optionValue(workspace.optionsRevision,"previewActive") && workspace.optionValue(workspace.optionsRevision,"previewKind")==="effects") ? "pause" : "play"; primary: true; Accessible.name: bridge.translate((popup.frame.jukebox ? bridge.stateValue(bridge.stateRevision,"playing") && !bridge.stateValue(bridge.stateRevision,"paused") : workspace.optionValue(workspace.optionsRevision,"previewActive") && workspace.optionValue(workspace.optionsRevision,"previewKind")==="effects") ? "Pausar" : "Reproduzir"); onClicked: { if(popup.frame.jukebox)bridge.playPause();else workspace.invoke("effects_play_pause",{}) } }
            PlaybackButton { glyph: "next"; Accessible.name: bridge.translate("Avançar"); enabled: popup.frame.jukebox && bridge.playbackControls.current+1<bridge.queueCount; onClicked: bridge.nextTrack() }
            PlaybackButton { glyph: "stop"; Accessible.name: bridge.translate("Parar"); onClicked: { if(popup.frame.jukebox)bridge.stop();else workspace.invoke("effects_stop",{}) } }
        }
    }
}
