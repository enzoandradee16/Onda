import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
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
    readonly property bool expanded: queueVisible || lyricsVisible
    readonly property bool scrolling: miniLyrics.moving || miniQueue.moving || scrollPause.running
    width: 560; height: expanded ? Math.max(360,Math.min(560,Screen.desktopAvailableHeight-32)) : 290
    minimumWidth: 490; minimumHeight: 290
    maximumHeight: Math.max(290,Screen.desktopAvailableHeight-32)
    Behavior on height { enabled: mini.visible&&bridge.animations; NumberAnimation {id:expandAnimation;duration:220;easing.type:Easing.OutCubic} }
    visible: false
    color: "transparent"
    property var mainWindow
    transientParent: null
    readonly property string artwork: bridge.state.cover || ""
    readonly property string trackTitle: bridge.state.title || "ONDA"
    readonly property string trackArtist: bridge.state.artist || ""
    readonly property string trackAlbum: bridge.state.album || ""
    readonly property bool playing: bridge.state.playing && !bridge.state.paused
    readonly property bool ready: bridge.state.ready
    readonly property bool hasNext: bridge.playback.current+1<bridge.queuedTracks.length || bridge.queueRepeat==="Todas" && bridge.queuedTracks.length>0
    property real volumeValue: 80
    property bool queueVisible: false
    property bool lyricsVisible: false
    property bool pinned: false
    property var lyricLines: []
    flags: Qt.Window | Qt.FramelessWindowHint
    readonly property bool glassEnabled: workspace.preferences.translucent_effects !== false && bridge.palette.mode !== "Alto contraste"
    readonly property bool darkGlass: ["Escuro","Preto puro"].indexOf(bridge.palette.mode)>=0
    readonly property bool motionEnabled: mini.visible&&mini.glassEnabled&&bridge.animations&&!mini.scrolling&&!expandAnimation.running
    property real musicPulse: motionEnabled&&playing ? Math.min(1,Math.sqrt(bridge.audioLevel)) : 0
    Behavior on musicPulse { NumberAnimation {duration:140;easing.type:Easing.OutQuad} }
    property var frame: ({position:0,duration:0,jukebox:true})
    signal volumeMoved(real value)
    function openPlayer() { workspace.openMiniPlayer(mini) }
    function restoreMain() { workspace.restore();hide() }
    function scrollList(list,event) {
        var delta=event.pixelDelta.y || event.angleDelta.y/120*84
        if(!delta){event.accepted=false;return}
        list.cancelFlick()
        list.contentY=Math.max(0,Math.min(Math.max(0,list.contentHeight-list.height),list.contentY-delta))
        scrollPause.restart()
        if(list===miniLyrics)manualLyricsPause.restart()
        event.accepted=true
    }
    onVisibleChanged: {workspace.setMiniPlayerActive(visible);if(visible)workspace.roundMiniPlayer(mini)}
    onWidthChanged: if(visible)workspace.roundMiniPlayer(mini)
    onHeightChanged: if(visible)workspace.roundMiniPlayer(mini)
    onClosing: function(close) {close.accepted=false;restoreMain()}
    Timer {id:scrollPause;interval:250}
    Timer {id:manualLyricsPause;interval:5000}
    Timer { interval: 100; running: mini.visible; repeat: true; onTriggered: {var next=workspace.lyricsFrame(true);if(JSON.stringify(next.lines)!==JSON.stringify(mini.lyricLines))mini.lyricLines=next.lines;mini.frame=next} }
    background: Rectangle {
        radius: 20; border.width: 1; border.color: mini.darkGlass ? "#35ffffff" : bridge.palette.line
        color: bridge.palette.surface
        clip: true
        SwirlBackdrop { objectName:"miniSwirlBackdrop"; anchors.fill: parent; visible: mini.glassEnabled; active: mini.visible&&mini.glassEnabled; animated: mini.motionEnabled; source: mini.visible&&mini.glassEnabled ? workspace.backdropUrl(mini.artwork) : ""; pulse:mini.musicPulse;dark:mini.darkGlass;opacity: (mini.darkGlass ? 0.62 : 0.4)+mini.musicPulse*0.07 }
        Rectangle { anchors.fill: parent; visible: mini.glassEnabled; color: bridge.palette.bg; opacity: mini.darkGlass ? 0.48 : 0.6 }
        Rectangle { anchors.fill: parent; visible: mini.glassEnabled; gradient: Gradient { GradientStop {position:0;color:mini.darkGlass ? "#18ffffff" : "#90ffffff"} GradientStop {position:0.45;color:mini.darkGlass ? "#03ffffff" : "#20ffffff"} GradientStop {position:1;color:mini.darkGlass ? "#20000000" : "#10000000"} } }
        Rectangle { anchors.fill: parent; radius: 20; visible: mini.glassEnabled; color: "transparent"; border.width: 1; border.color: mini.darkGlass ? "#30ffffff" : "#b0ffffff" }
    }
    MouseArea {
        id: headerDragArea; objectName: "miniPlayerDragArea"
        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
        height: 160
        onPressed: mini.startSystemMove()
        onDoubleClicked: mini.restoreMain()
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 18; spacing: 8
        ColumnLayout {
            Layout.fillWidth:true;Layout.preferredHeight:250;Layout.minimumHeight:250;Layout.maximumHeight:250;Layout.alignment:Qt.AlignTop;spacing:8
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 28; Layout.maximumHeight: 28; spacing: 6
            Item { Layout.fillWidth: true; Layout.fillHeight: true }
            MiniControl { glyph: "pin"; implicitWidth: 32; implicitHeight: 28; primary: mini.pinned; Accessible.name: bridge.translate("Fixar acima de todos"); ToolTip.visible: hovered; ToolTip.text: Accessible.name; onClicked: {mini.pinned=!mini.pinned;workspace.pinPlayer(mini,mini.pinned)} }
            MiniControl { glyph: "expand"; implicitHeight: 28; Accessible.name: bridge.translate("Abrir ONDA"); onClicked: mini.restoreMain() }
            MiniControl {glyph: "minimize"; implicitHeight: 28; Accessible.name: bridge.translate("Minimizar"); onClicked: mini.showMinimized()}
            MiniControl {glyph: "close"; implicitHeight: 28; Accessible.name: bridge.translate("Fechar"); onClicked: mini.restoreMain()}
        }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 96; Layout.maximumHeight: 96; spacing: 14
            Item {Layout.preferredWidth:96;Layout.preferredHeight:96
              Repeater {model:[28,18,10]
                Rectangle {required property int modelData;objectName:"miniAlbumHalo";anchors.centerIn:parent;width:96+modelData+mini.musicPulse*7;height:width;radius:14+modelData/2;visible:mini.glassEnabled;color:bridge.palette.accent;opacity:0.04+mini.musicPulse*0.05}
              }
              RoundedArtwork { source: mini.artwork; anchors.fill:parent;fillMode: Image.PreserveAspectFit; asynchronous: true
                Label { anchors.centerIn: parent; visible: !parent.source.toString(); text: "♪"; font.pixelSize: 36; color: bridge.palette.accent }
              }
            }
            ColumnLayout {
                Layout.fillWidth: true
                Label { text: mini.trackTitle; color: bridge.palette.text; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 22; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                Label { text: mini.trackArtist; horizontalAlignment: Text.AlignHCenter; font.pixelSize: 17; color: bridge.palette.muted; elide: Text.ElideRight; Layout.fillWidth: true }
                Label { text: mini.trackAlbum; horizontalAlignment: Text.AlignHCenter; color: bridge.palette.muted; elide: Text.ElideRight; Layout.fillWidth: true }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight:20;Layout.maximumHeight:20
            Label {text: workspace.clock(mini.frame.position || 0);color: bridge.palette.muted}
            MiniSlider { Layout.fillWidth: true; from: 0; to: Math.max(1,mini.frame.duration || 0); value: mini.frame.position || 0; enabled: mini.frame.duration>0; onMoved: workspace.seekLyrics(value,true) }
            Label {text: "−"+workspace.clock(Math.max(0,(mini.frame.duration || 0)-(mini.frame.position || 0)));color: bridge.palette.muted}
        }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight:42;Layout.maximumHeight:42;spacing: 8
            Item {Layout.fillWidth: true}
            MiniControl {objectName:"miniShuffle";glyph:"shuffle";primary:bridge.queueShuffle;Accessible.name:bridge.translate("Reprodução aleatória");ToolTip.visible:hovered;ToolTip.text:Accessible.name;onClicked:bridge.setQueueShuffle(!bridge.queueShuffle)}
            PlaybackButton {objectName: "miniPrevious"; glyph: "previous"; Accessible.name: bridge.translate("Retroceder"); enabled: mini.ready; onClicked: bridge.previousTrack()}
            PlaybackButton {objectName: "miniPlayPause"; glyph: mini.playing ? "pause" : "play"; primary: true; enabled: mini.ready; Accessible.name: bridge.translate(mini.playing ? "Pausar" : "Reproduzir"); onClicked: bridge.playPause()}
            PlaybackButton {objectName: "miniNext"; glyph: "next"; Accessible.name: bridge.translate("Avançar"); enabled: mini.hasNext; onClicked: bridge.nextTrack()}
            MiniControl {objectName: "miniStop"; glyph: "stop"; Accessible.name: bridge.translate("Parar"); onClicked: bridge.stop()}
            Item {Layout.fillWidth: true}
            MicrophoneButton { implicitHeight: 34; background: Rectangle {radius: 9;color: parent.primary ? bridge.palette.accent : parent.hovered ? bridge.palette.hover : "transparent"} primary: mini.lyricsVisible; onClicked: {mini.lyricsVisible=!mini.lyricsVisible;if(mini.lyricsVisible)mini.queueVisible=false} }
            MiniControl {glyph: "queue"; primary: mini.queueVisible; Accessible.name: bridge.translate("Fila de reprodução"); onClicked: {mini.queueVisible=!mini.queueVisible;if(mini.queueVisible)mini.lyricsVisible=false}}
        }
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight:24;Layout.maximumHeight:24
            LineIcon {glyph: "volume"; Layout.preferredWidth: 24; Layout.preferredHeight: 24}
            MiniSlider {objectName: "miniVolume"; Layout.fillWidth: true;value: mini.volumeValue;Accessible.name: bridge.translate("Volume");onMoved: mini.volumeMoved(value)}
        }
        }
        ListView {
            id: miniLyrics; objectName: "miniPlayerLyrics"; visible: mini.lyricsVisible; Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 0; Layout.preferredHeight: 0; clip: true; spacing: 14
            reuseItems:true;cacheBuffer:300;pixelAligned:true;boundsBehavior:Flickable.StopAtBounds;maximumFlickVelocity:3500;flickDeceleration:1800
            onMovementStarted:manualLyricsPause.restart()
            onMovementEnded:scrollPause.restart()
            WheelHandler {target:null;onWheel:function(event){mini.scrollList(miniLyrics,event)}}
            model: mini.lyricLines
            property int activeLine: mini.frame.active === undefined ? -1 : mini.frame.active
            onActiveLineChanged: if(activeLine>=0&&!moving&&!manualLyricsPause.running)Qt.callLater(function(){if(!miniLyrics.moving&&!manualLyricsPause.running)miniLyrics.positionViewAtIndex(miniLyrics.activeLine,ListView.Center)})
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
            id:miniQueue;objectName:"miniPlayerQueue"
            visible: mini.queueVisible; Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 0; Layout.preferredHeight: 0; clip: true
            spacing:4;reuseItems:true;cacheBuffer:300;pixelAligned:true;boundsBehavior:Flickable.StopAtBounds;maximumFlickVelocity:3500;flickDeceleration:1800
            onMovementEnded:scrollPause.restart()
            WheelHandler {target:null;onWheel:function(event){mini.scrollList(miniQueue,event)}}
            model: bridge.queuedTracks
            ScrollBar.vertical: ScrollBar {}
            delegate: ItemDelegate {
                id:miniQueueTrack
                objectName:"miniQueueTrack"+index
                required property var modelData;required property int index
                width: ListView.view.width;height:60
                readonly property var record:modelData.record || {}
                readonly property bool current:!!modelData.current
                contentItem: RowLayout {
                    spacing:12
                    RoundedArtwork {objectName:"miniQueueArtwork";Layout.preferredWidth:44;Layout.preferredHeight:44;source:record.cover_url || modelData.cover || "";fallbackSource:modelData.cover || "";sourceSize.width:192;sourceSize.height:192;asynchronous:true;fillMode:Image.PreserveAspectCrop
                        Label {anchors.centerIn:parent;visible:parent.status!==Image.Ready;text:"♪";color:bridge.palette.muted}
                        PreparationProgress {anchors.left:parent.left;anchors.right:parent.right;anchors.bottom:parent.bottom;height:3;preparing:modelData.analysis==="preparing";progress:bridge.queuePreparation[modelData.id] || 0}
                    }
                    ColumnLayout {Layout.fillWidth:true;Layout.minimumWidth:0;spacing:3
                        Label {Layout.fillWidth:true;text:modelData.title || "";color:miniQueueTrack.current ? bridge.palette.accent : bridge.palette.text;font.weight:Font.DemiBold;elide:Text.ElideRight}
                        Label {Layout.fillWidth:true;text:modelData.artist || "";color:bridge.palette.muted;elide:Text.ElideRight}
                    }
                }
                background:Rectangle {radius:8;color:parent.highlighted||parent.hovered ? bridge.palette.hover : "transparent"}
                onDoubleClicked: bridge.playQueued(index)
            }
        }
    }
}
