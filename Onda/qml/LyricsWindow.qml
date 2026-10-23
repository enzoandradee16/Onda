import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    objectName: "lyricsWindow"
    parent: Overlay.overlay; anchors.centerIn: parent
    width: Math.min(740,parent.width-48); height: Math.min(520,parent.height-70)
    modal: false; focus: true; padding: 24
    property var frame: ({text:"",position:0,duration:0,jukebox:false})
    property var lyricLines: []
    background: Card {}
    Timer { interval: 80; running: popup.opened; repeat: true; onTriggered: { var next=workspace.lyricsFrame();if(JSON.stringify(next.lines)!==JSON.stringify(popup.lyricLines))popup.lyricLines=next.lines;popup.frame=next } }
    contentItem: ColumnLayout {
        RowLayout { Layout.fillWidth: true
            Label { text: bridge.translate("Letra"); color: bridge.palette.text; Layout.fillWidth: true; font.pixelSize: 24 }
            TaskButton { idleText: bridge.translate("Buscar letra online"); operation: "lyrics_online" }
            ActionButton { text: bridge.translate("Escolher letra"); onClicked: workspace.invoke("pick",{kind:popup.frame.jukebox ? "jukeboxLyrics" : "effectLyrics"}) }
            ActionButton { text: bridge.translate("Pronto"); onClicked: popup.close() }
        }
        ListView {
            id: linesView; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 18
            model: popup.lyricLines
            property int activeLine: popup.frame.active === undefined ? -1 : popup.frame.active
            onActiveLineChanged: if(activeLine>=0)Qt.callLater(function(){linesView.positionViewAtIndex(linesView.activeLine,ListView.Center)})
            ScrollBar.vertical: ScrollBar {}
            delegate: Label {
                required property var modelData; required property int index
                TapHandler { onTapped: workspace.seekLyrics(modelData.time,popup.frame.jukebox) }
                width: linesView.width; text: index===linesView.activeLine ? popup.frame.text : modelData.text
                textFormat: index===linesView.activeLine ? Text.RichText : Text.PlainText
                wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                color: index===linesView.activeLine ? bridge.palette.accent : bridge.palette.muted
                font.pixelSize: 28; scale: index===linesView.activeLine && workspace.preferences.lyrics_animation === "Zoom" ? 1 : 0.97;
                Behavior on scale { NumberAnimation { duration: workspace.preferences.lyrics_animation === "Desativada" ? 0 : 180 } }
                opacity: index===linesView.activeLine ? 1 : 0.55
                Behavior on opacity { NumberAnimation { duration: workspace.preferences.lyrics_animation === "Desativada" ? 0 : 180 } }
            }
        }
        OndaSlider { Layout.fillWidth: true; from: 0; to: Math.max(1,popup.frame.duration); value: popup.frame.position; onMoved: workspace.seekLyrics(value,popup.frame.jukebox) }
        RowLayout { Layout.fillWidth: true
            Label { text: Math.floor(popup.frame.position/60)+":"+String(Math.floor(popup.frame.position%60)).padStart(2,"0"); color: bridge.palette.muted; Layout.fillWidth: true }
            ActionButton { text: bridge.translate("Reproduzir"); onClicked: { if(popup.frame.jukebox)bridge.playPause();else workspace.invoke("effects_preview",{}) } }
            ActionButton { text: bridge.translate("Parar"); onClicked: { if(popup.frame.jukebox)bridge.stop();else workspace.invoke("stop_preview",{}) } }
        }
    }
}
