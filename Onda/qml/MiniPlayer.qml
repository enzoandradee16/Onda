import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ApplicationWindow {
    id: mini
    objectName: "miniPlayer"
    title: "ONDA · Mini player"
    width: 500; height: (queueVisible || lyricsVisible) ? 460 : 250
    minimumWidth: 430; minimumHeight: 250
    maximumHeight: (queueVisible || lyricsVisible) ? 700 : 310
    visible: false
    color: bridge.palette.surface
    property var mainWindow
    property real volumeValue: 80
    property bool queueVisible: false
    property bool lyricsVisible: false
    property bool pinned: false
    property var lyricLines: []
    flags: Qt.Window | (pinned ? Qt.WindowStaysOnTopHint : 0)
    property var frame: ({position:0,duration:0,jukebox:true})
    signal volumeMoved(real value)
    function restoreMain() { if(mainWindow){mainWindow.show();mainWindow.raise();mainWindow.requestActivate()}hide() }
    onClosing: function(close) {close.accepted=false;restoreMain()}
    Timer { interval: 100; running: mini.visible; repeat: true; onTriggered: {var next=workspace.lyricsFrame();if(JSON.stringify(next.lines)!==JSON.stringify(mini.lyricLines))mini.lyricLines=next.lines;mini.frame=next} }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 10
        RowLayout {
            Layout.fillWidth: true; spacing: 14
            Image { source: bridge.state.cover || ""; Layout.preferredWidth: 84; Layout.preferredHeight: 84; fillMode: Image.PreserveAspectFit; asynchronous: true
                Label { anchors.centerIn: parent; visible: !parent.source.toString(); text: "♪"; font.pixelSize: 36; color: bridge.palette.accent }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: bridge.state.title || "ONDA"; color: bridge.palette.text; font.pixelSize: 19; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                Label { text: bridge.state.artist || ""; color: bridge.palette.muted; elide: Text.ElideRight; Layout.fillWidth: true }
                Label { text: bridge.state.album || ""; color: bridge.palette.muted; elide: Text.ElideRight; Layout.fillWidth: true }
            }
            ActionButton { text: "\uE718"; font.family: "Segoe MDL2 Assets"; implicitWidth: 34; primary: mini.pinned; Accessible.name: bridge.translate("Fixar acima de todos"); ToolTip.visible: hovered; ToolTip.text: Accessible.name; onClicked: {mini.pinned=!mini.pinned;mini.show();mini.raise()} }
            ActionButton { text: "↗"; Accessible.name: bridge.translate("Abrir ONDA"); onClicked: mini.restoreMain() }
        }
        RowLayout {
            Layout.fillWidth: true
            Label {text: workspace.clock(mini.frame.position || 0);color: bridge.palette.muted}
            OndaSlider { Layout.fillWidth: true; from: 0; to: Math.max(1,mini.frame.duration || 0); value: mini.frame.position || 0; enabled: mini.frame.duration>0; onMoved: workspace.seekLyrics(value,true) }
            Label {text: "−"+workspace.clock(Math.max(0,(mini.frame.duration || 0)-(mini.frame.position || 0)));color: bridge.palette.muted}
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            ActionButton {text: "↶"; Accessible.name: bridge.translate("Reproduzir"); enabled: bridge.state.ready; onClicked: workspace.seekLyrics(0,true)}
            ActionButton {text: bridge.state.playing && !bridge.state.paused ? "Ⅱ" : "▶"; primary: true; enabled: bridge.state.ready; Accessible.name: bridge.translate(bridge.state.playing && !bridge.state.paused ? "Pausar" : "Reproduzir"); onClicked: bridge.playPause()}
            ActionButton {text: "■"; Accessible.name: bridge.translate("Parar"); onClicked: bridge.stop()}
            ActionButton {text: "▶▶"; Accessible.name: bridge.translate("Próxima música"); enabled: bridge.queuedTracks.length>0; onClicked: bridge.nextTrack()}
            Item {Layout.fillWidth: true}
            MicrophoneButton { primary: mini.lyricsVisible; onClicked: {mini.lyricsVisible=!mini.lyricsVisible;if(mini.lyricsVisible)mini.queueVisible=false} }
            ActionButton {text: "≡"; Accessible.name: bridge.translate("Fila de reprodução"); onClicked: {mini.queueVisible=!mini.queueVisible;if(mini.queueVisible)mini.lyricsVisible=false}}
        }
        RowLayout {
            Layout.fillWidth: true
            Label {text: "\uE767";font.family: "Segoe MDL2 Assets";color: bridge.palette.text}
            OndaSlider {Layout.fillWidth: true;value: mini.volumeValue;Accessible.name: bridge.translate("Volume");onMoved: mini.volumeMoved(value)}
        }
        ListView {
            id: miniLyrics; visible: mini.lyricsVisible; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 14
            model: mini.lyricLines
            property int activeLine: mini.frame.active === undefined ? -1 : mini.frame.active
            onActiveLineChanged: if(activeLine>=0)Qt.callLater(function(){miniLyrics.positionViewAtIndex(miniLyrics.activeLine,ListView.Center)})
            ScrollBar.vertical: ScrollBar {}
            delegate: Label {
                required property var modelData;required property int index
                width: miniLyrics.width;wrapMode: Text.Wrap;horizontalAlignment: Text.AlignHCenter
                text: index===miniLyrics.activeLine ? mini.frame.text : modelData.text
                textFormat: index===miniLyrics.activeLine ? Text.RichText : Text.PlainText
                color: index===miniLyrics.activeLine ? bridge.palette.accent : bridge.palette.muted
                font.pixelSize: 20
                TapHandler {onTapped: workspace.seekLyrics(modelData.time,true)}
            }
            Label {anchors.centerIn: parent;visible: !mini.lyricLines.length;text: bridge.translate("Buscar letra online");color: bridge.palette.muted;TapHandler {onTapped: workspace.invoke("lyrics_online",{jukebox:true})}}
        }
        ListView {
            visible: mini.queueVisible; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            model: bridge.queuedTracks
            ScrollBar.vertical: ScrollBar {}
            delegate: ItemDelegate {
                required property var modelData;required property int index
                width: ListView.view.width
                contentItem: Label {text:modelData.title;color: modelData.current ? bridge.palette.accent : bridge.palette.text;elide: Text.ElideRight}
                onClicked: bridge.playQueued(index)
            }
        }
    }
}
