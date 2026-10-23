import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ApplicationWindow {
    component MiniSlider: OndaSlider {
        id: slider
        implicitHeight: 20
        background: Rectangle {
            x: slider.leftPadding; y: slider.topPadding+slider.availableHeight/2-1.5
            width: slider.availableWidth; height: 3; radius: 2; color: bridge.palette.line
            Rectangle {width: slider.visualPosition*parent.width;height: parent.height;radius: 2;color: bridge.palette.accent}
        }
        handle: Rectangle {
            x: slider.leftPadding+slider.visualPosition*(slider.availableWidth-width)
            y: slider.topPadding+slider.availableHeight/2-height/2
            implicitWidth: slider.hovered || slider.pressed ? 11 : 7;implicitHeight: implicitWidth
            radius: width/2;color: bridge.palette.accent
        }
    }
    component MiniControl: PlaybackButton {
        implicitWidth: 36; implicitHeight: 32
        background: Rectangle { radius: 9; color: parent.primary ? (parent.hovered ? bridge.palette.accent_hover : bridge.palette.accent) : parent.hovered ? bridge.palette.hover : "transparent" }

    }
    id: mini
    objectName: "miniPlayer"
    title: "ONDA · Mini player"
    width: 560; height: (queueVisible || lyricsVisible) ? 460 : 290
    minimumWidth: 490; minimumHeight: 290
    maximumHeight: (queueVisible || lyricsVisible) ? 700 : 310
    visible: false
    color: "transparent"
    property var mainWindow
    property real volumeValue: 80
    property bool queueVisible: false
    property bool lyricsVisible: false
    property bool pinned: false
    property var lyricLines: []
    flags: Qt.Window | Qt.FramelessWindowHint
    readonly property bool glassEnabled: bridge.palette.mode !== "Alto contraste"
    readonly property bool darkGlass: ["Escuro","Preto puro"].indexOf(bridge.palette.mode)>=0
    property var frame: ({position:0,duration:0,jukebox:true})
    signal volumeMoved(real value)
    function restoreMain() { workspace.restore();hide() }
    onVisibleChanged: workspace.setMiniPlayerActive(visible)
    onClosing: function(close) {close.accepted=false;restoreMain()}
    Timer { interval: 100; running: mini.visible; repeat: true; onTriggered: {var next=workspace.lyricsFrame();if(JSON.stringify(next.lines)!==JSON.stringify(mini.lyricLines))mini.lyricLines=next.lines;mini.frame=next} }
    background: Rectangle {
        radius: 18; border.width: 1; border.color: mini.darkGlass ? "#35ffffff" : bridge.palette.line
        color: bridge.palette.surface
        clip: true
        Image { anchors.fill: parent; visible: mini.glassEnabled; source: bridge.state.cover || ""; sourceSize.width: 12; sourceSize.height: 12; smooth: true; fillMode: Image.PreserveAspectCrop; opacity: mini.darkGlass ? 0.55 : 0.35; asynchronous: true }
        Rectangle { anchors.fill: parent; visible: mini.glassEnabled; color: bridge.palette.bg; opacity: mini.darkGlass ? 0.4 : 0.65 }
        Rectangle { anchors.fill: parent; visible: mini.glassEnabled; gradient: Gradient { GradientStop {position:0;color:mini.darkGlass ? "#18ffffff" : "#90ffffff"} GradientStop {position:0.45;color:mini.darkGlass ? "#03ffffff" : "#20ffffff"} GradientStop {position:1;color:mini.darkGlass ? "#20000000" : "#10000000"} } }
        Rectangle { anchors.fill: parent; visible: mini.glassEnabled; color: "transparent"; border.width: 1; border.color: mini.darkGlass ? "#30ffffff" : "#b0ffffff" }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 18; spacing: 8
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 28; Layout.maximumHeight: 28; spacing: 6
            Item { Layout.fillWidth: true; Layout.fillHeight: true
                MouseArea { anchors.fill: parent; onPressed: mini.startSystemMove(); onDoubleClicked: mini.restoreMain() }
            }
            MiniControl { glyph: "pin"; implicitWidth: 32; implicitHeight: 28; primary: mini.pinned; Accessible.name: bridge.translate("Fixar acima de todos"); ToolTip.visible: hovered; ToolTip.text: Accessible.name; onClicked: {mini.pinned=!mini.pinned;workspace.pinPlayer(mini,mini.pinned)} }
            MiniControl { glyph: "expand"; implicitHeight: 28; Accessible.name: bridge.translate("Abrir ONDA"); onClicked: mini.restoreMain() }
            MiniControl {glyph: "minimize"; implicitHeight: 28; Accessible.name: bridge.translate("Minimizar"); onClicked: mini.showMinimized()}
            MiniControl {glyph: "close"; implicitHeight: 28; Accessible.name: bridge.translate("Fechar"); onClicked: mini.restoreMain()}
        }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 96; Layout.maximumHeight: 96; spacing: 14
            RoundedArtwork { source: bridge.state.cover || ""; Layout.preferredWidth: 96; Layout.preferredHeight: 96; fillMode: Image.PreserveAspectFit; asynchronous: true
                Label { anchors.centerIn: parent; visible: !parent.source.toString(); text: "♪"; font.pixelSize: 36; color: bridge.palette.accent }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: bridge.state.title || "ONDA"; color: bridge.palette.text; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 22; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                Label { text: bridge.state.artist || ""; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 17; color: bridge.palette.muted; elide: Text.ElideRight; Layout.fillWidth: true }
                Label { text: bridge.state.album || ""; horizontalAlignment: Text.AlignHCenter; color: bridge.palette.muted; elide: Text.ElideRight; Layout.fillWidth: true }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label {text: workspace.clock(mini.frame.position || 0);color: bridge.palette.muted}
            MiniSlider { Layout.fillWidth: true; from: 0; to: Math.max(1,mini.frame.duration || 0); value: mini.frame.position || 0; enabled: mini.frame.duration>0; onMoved: workspace.seekLyrics(value,true) }
            Label {text: "−"+workspace.clock(Math.max(0,(mini.frame.duration || 0)-(mini.frame.position || 0)));color: bridge.palette.muted}
        }
        RowLayout {
            Layout.fillWidth: true; spacing: 8
            Item {Layout.fillWidth: true}
            PlaybackButton {glyph: "previous"; Accessible.name: bridge.translate("Retroceder"); enabled: bridge.state.ready; onClicked: bridge.previousTrack()}
            PlaybackButton {glyph: bridge.state.playing && !bridge.state.paused ? "pause" : "play"; primary: true; enabled: bridge.state.ready; Accessible.name: bridge.translate(bridge.state.playing && !bridge.state.paused ? "Pausar" : "Reproduzir"); onClicked: bridge.playPause()}
            PlaybackButton {glyph: "next"; Accessible.name: bridge.translate("Avançar"); enabled: bridge.playback.current+1<bridge.queuedTracks.length; onClicked: bridge.nextTrack()}
            MiniControl {glyph: "stop"; Accessible.name: bridge.translate("Parar"); onClicked: bridge.stop()}
            Item {Layout.fillWidth: true}
            MicrophoneButton { implicitHeight: 34; background: Rectangle {radius: 9;color: parent.primary ? bridge.palette.accent : parent.hovered ? bridge.palette.hover : "transparent"} primary: mini.lyricsVisible; onClicked: {mini.lyricsVisible=!mini.lyricsVisible;if(mini.lyricsVisible)mini.queueVisible=false} }
            MiniControl {glyph: "queue"; primary: mini.queueVisible; Accessible.name: bridge.translate("Fila de reprodução"); onClicked: {mini.queueVisible=!mini.queueVisible;if(mini.queueVisible)mini.lyricsVisible=false}}
        }
        RowLayout {
            Layout.fillWidth: true
            LineIcon {glyph: "volume"; Layout.preferredWidth: 24; Layout.preferredHeight: 24}
            MiniSlider {Layout.fillWidth: true;value: mini.volumeValue;Accessible.name: bridge.translate("Volume");onMoved: mini.volumeMoved(value)}
        }
        ListView {
            id: miniLyrics; objectName: "miniPlayerLyrics"; visible: mini.lyricsVisible; Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 0; Layout.preferredHeight: 0; clip: true; spacing: 14
            model: mini.lyricLines
            property int activeLine: mini.frame.active === undefined ? -1 : mini.frame.active
            onActiveLineChanged: if(activeLine>=0)Qt.callLater(function(){miniLyrics.positionViewAtIndex(miniLyrics.activeLine,ListView.Center)})
            ScrollBar.vertical: ScrollBar {}
            delegate: AnimatedLyric {
                required property var modelData;required property int index
                lineKey: String(index===miniLyrics.activeLine)
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
            visible: mini.queueVisible; Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 0; Layout.preferredHeight: 0; clip: true
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
