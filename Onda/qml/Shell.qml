import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Pane {
    LyricsWindow { id: lyricsWindow }
    MiniPlayer { id: floatingPlayer; mainWindow: app.Window.window; volumeValue: volume.value; onVolumeMoved: function(value){volume.value=value} }

    Connections { target: workspace; function onLyricsRequested() {lyricsWindow.open()} }
    id: app
    width: 1360; height: 900
    readonly property var inlineTasks: ({catalog:["search"],playlists:["collection","compare_collection","check_matches"],converter:["convert","detect_silence"],effects:["effects_export"],images:["image_preview","image_export"],metadata:["audio_edit","normalize_preview"]})[workspace.currentPage] || []
    readonly property var remainingTasks: workspace.activity.busy.filter(function(name) { return app.inlineTasks.indexOf(name)<0 && workspace.activity.background.indexOf(name)<0 })
    padding: 0
    background: Rectangle { color: bridge.palette.bg }
    font.family: workspace.preferences.interface_font === "Padrão do sistema" ? "Segoe UI" : workspace.preferences.interface_font; font.pixelSize: Math.round(14*bridge.fontScale)
    palette.window: bridge.palette.bg
    palette.windowText: bridge.palette.text
    palette.base: bridge.palette.surface
    palette.text: bridge.palette.text
    palette.button: bridge.palette.surface
    palette.buttonText: bridge.palette.text
    palette.highlight: bridge.palette.accent
    palette.highlightedText: bridge.palette.accent_text
    palette.mid: bridge.palette.line
    palette.dark: bridge.palette.muted
    palette.light: bridge.palette.surface
    palette.placeholderText: bridge.palette.muted
    RowLayout {
        id: shell; anchors.fill: parent; spacing: Math.round(0*bridge.spacing)
        opacity: 0
        Component.onCompleted: opacity=1
        Behavior on opacity { NumberAnimation { duration: bridge.animations ? 220 : 0; easing.type: Easing.OutCubic } }
        Sidebar { id: sidebar; resizing: resizeMouse.pressed; onSettingsRequested: workspace.showSettings() }
        Rectangle {
            Layout.preferredWidth: 6; Layout.fillHeight: true; color: resizeMouse.containsMouse ? bridge.palette.accent : bridge.palette.line
            MouseArea { id: resizeMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.SplitHCursor; property real initialX; property real initialWidth
                onPressed: function(mouse) { initialX=mapToGlobal(mouse.x,mouse.y).x;initialWidth=sidebar.width }
                onPositionChanged: function(mouse) { if(pressed) { var requested=initialWidth+mapToGlobal(mouse.x,mouse.y).x-initialX;sidebar.collapsed=requested<160;if(!sidebar.collapsed)workspace.setSetting("sidebar_width",Math.max(160,Math.min(420,requested))) } }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: Math.round(0*bridge.spacing)
            ColumnLayout {
                Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.topMargin: 24; Layout.bottomMargin: 18; spacing: Math.round(5*bridge.spacing)
                RowLayout {
                Layout.fillWidth: true
                Text { Layout.fillWidth: true; text: workspace.title; font.pixelSize: Math.round(28*bridge.fontScale); font.weight: Font.DemiBold; color: bridge.palette.text }
                ActionButton { text: bridge.translate("Aparência"); onClicked: appearance.open() }
                ActionButton { text: bridge.translate("Atalhos"); onClicked: workspace.showShortcuts() }
                ActionButton { text: bridge.translate("Metadados"); onClicked: workspace.showMetadata() }
                }
                Text { visible: workspace.currentPage === "effects" || workspace.currentPage === "jukebox"; text: bridge.translate("Sua música, do seu jeito."); font.pixelSize: Math.round(15*bridge.fontScale); color: bridge.palette.muted }
                RowLayout {
                    visible: workspace.currentPage === "effects" || workspace.currentPage === "jukebox"; Layout.topMargin: 16; spacing: Math.round(12*bridge.spacing)
                    objectName: "playbackTabs"
                    layoutDirection: workspace.preferences.playback_tab_order === "Jukebox infinito primeiro" ? Qt.RightToLeft : Qt.LeftToRight
                    ActionButton { text: bridge.translate("Efeitos"); primary: workspace.currentPage === "effects"; onClicked: workspace.selectPage("effects"); Layout.preferredWidth: 130 }
                    ActionButton { text: bridge.translate("Jukebox infinito"); primary: workspace.currentPage === "jukebox"; onClicked: workspace.selectPage("jukebox"); Layout.preferredWidth: 178 }
                }
            }
            Flow { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; spacing: Math.round(8*bridge.spacing); visible: app.remainingTasks.length > 0
                Repeater { model: app.remainingTasks.filter(function(name) { return name !== "prepare_tools" && name !== "update_tools" }); ActionButton { required property string modelData; text: bridge.translate("Cancelar")+" "+workspace.taskLabel(modelData); onClicked: workspace.invoke("cancel_task",{name:modelData}) } }
            }
            Card {
                objectName: "toolsProgressCard"
                visible: workspace.activity.busy.indexOf("prepare_tools") >= 0 || workspace.activity.busy.indexOf("update_tools") >= 0
                Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.bottomMargin: 16
                implicitHeight: toolProgressBody.implicitHeight+32
                ColumnLayout {
                    id: toolProgressBody; anchors.fill: parent; anchors.margins: 16; spacing: 10
                    Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: bridge.palette.text; text: bridge.translate(workspace.activity.tools.message || "Preparando ferramentas…") }
                    OndaProgressBar { Layout.fillWidth: true; from: 0; to: Math.max(1,workspace.activity.tools.total || 0); value: workspace.activity.tools.done || 0; indeterminate: !(workspace.activity.tools.total > 0) }
                    Label { visible: workspace.activity.tools.total > 0; color: bridge.palette.muted; text: Math.min(100,Math.round(100*(workspace.activity.tools.done || 0)/Math.max(1,workspace.activity.tools.total || 0)))+"%" }
                }
            }
            WorkspaceView { objectName: "workspaceArea"; visible: workspace.currentPage !== "jukebox"; active: visible; Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.bottomMargin: 16 }
            JukeboxView { id: jukebox; visible: workspace.currentPage === "jukebox"; Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 24; Layout.rightMargin: 24; volume: volume.value }
            Card {
                objectName: "jukeboxMiniPlayer"
                visible: workspace.currentPage !== "jukebox" && bridge.state.playing
                Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.bottomMargin: 20
                implicitHeight: 76
                MouseArea {
                    objectName: "openJukeboxFromMiniPlayer"
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    Accessible.role: Accessible.Button
                    Accessible.name: bridge.translate("Jukebox infinito")
                    onClicked: workspace.selectPage("jukebox")
                }
                RowLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 12
                    Rectangle { Layout.preferredWidth: 54; Layout.preferredHeight: 54; radius: 6; color: bridge.palette.input; clip: true
                        Image { id: miniCover; anchors.fill: parent; source: bridge.state.cover; fillMode: Image.PreserveAspectCrop; asynchronous: true }
                        Label { anchors.centerIn: parent; visible: miniCover.status !== Image.Ready; text: "♪"; color: bridge.palette.muted; font.pixelSize: 25 }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 3
                        Label { Layout.fillWidth: true; text: bridge.state.title; color: bridge.palette.text; elide: Text.ElideRight; font.bold: true }
                        Label { Layout.fillWidth: true; text: [bridge.state.artist,bridge.state.album].filter(Boolean).join(" · "); color: bridge.palette.muted; elide: Text.ElideRight }
                    }
                    ActionButton {
                        implicitWidth: 44
                        Accessible.name: bridge.translate(bridge.state.paused ? "Retomar" : "Pausar")
                        ToolTip.visible: hovered; ToolTip.text: Accessible.name
                        onClicked: bridge.playPause()
                        contentItem: Item {
                            Canvas {
                                anchors.centerIn: parent; width: 18; height: 18
                                property bool paused: bridge.state.paused
                                property color ink: bridge.palette.text
                                onPausedChanged: requestPaint()
                                onInkChanged: requestPaint()
                                onPaint: {
                                    const ctx=getContext("2d");ctx.reset();ctx.fillStyle=ink
                                    if(paused) {
                                        ctx.beginPath();ctx.moveTo(3,2);ctx.lineTo(15,9);ctx.lineTo(3,16);ctx.closePath();ctx.fill()
                                    } else {
                                        ctx.fillRect(3,2,4,14);ctx.fillRect(11,2,4,14)
                                    }
                                }
                            }
                        }
                    }
                    ActionButton { symbol: "▶|"; Accessible.name: bridge.translate("Próxima música"); ToolTip.visible: hovered; ToolTip.text: Accessible.name; enabled: bridge.playback.current+1<bridge.queuedTracks.length; onClicked: bridge.nextTrack() }
                    ActionButton { symbol: "■"; Accessible.name: bridge.translate("Parar"); ToolTip.visible: hovered; ToolTip.text: Accessible.name; onClicked: bridge.stop() }
                    ActionButton {
                        implicitWidth: 44; Accessible.name: bridge.translate("Equalizador")
                        ToolTip.visible: hovered; ToolTip.text: Accessible.name
                        onClicked: miniEqualizer.open()
                        contentItem: Item {
                            Canvas {
                                anchors.centerIn: parent; width: 23; height: 23
                                property color ink: bridge.palette.text
                                onInkChanged: requestPaint()
                                onPaint: {
                                    const ctx=getContext("2d");ctx.reset();ctx.scale(width/24,height/24)
                                    ctx.strokeStyle=ink;ctx.fillStyle=ink;ctx.lineWidth=1.7;ctx.lineCap="round"
                                    const xs=[5,12,19],ys=[8,16,10]
                                    for(let i=0;i<3;i++) {
                                        ctx.beginPath();ctx.moveTo(xs[i],3);ctx.lineTo(xs[i],21);ctx.stroke()
                                        ctx.beginPath();ctx.arc(xs[i],ys[i],2.5,0,Math.PI*2);ctx.fill()
                                    }
                                }
                            }
                        }
                    }
                    MicrophoneButton { onClicked: { if (lyricsWindow.visible) lyricsWindow.close(); else lyricsWindow.open() } }
                    ActionButton { text: bridge.translate("Timers"); onClicked: miniTimers.open() }
                    ActionButton { text: bridge.translate("Fila"); onClicked: {workspace.selectPage("jukebox");jukebox.queueExpanded=true} }
                }
            }
            Rectangle {
                visible: workspace.currentPage === "jukebox"; Layout.fillWidth: true; implicitHeight: 78; color: bridge.palette.surface
                Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: bridge.palette.line }
                RowLayout {
                    anchors.fill: parent; anchors.leftMargin: 24; anchors.rightMargin: 24; spacing: Math.round(12*bridge.spacing)
                    ActionButton {
                        primary: true
                        symbol: bridge.state.playing && !bridge.state.paused ? "Ⅱ" : "▶"
                        text: bridge.translate(bridge.state.playing ? (bridge.state.paused ? "Retomar" : "Pausar") : "Reproduzir")
                        enabled: bridge.state.ready && (!bridge.state.busy || bridge.state.playing)
                        onClicked: bridge.playPause()
                    }
                    ActionButton { text: bridge.translate(bridge.state.busy ? "Cancelar" : "Parar"); symbol: "■"; enabled: bridge.state.playing || bridge.state.busy; onClicked: bridge.stop() }
                    MicrophoneButton { onClicked: { if (lyricsWindow.visible) lyricsWindow.close(); else lyricsWindow.open() } }
                    ActionButton { text: bridge.translate("Timers"); onClicked: miniTimers.open() }
                    Text { text: "\uE767"; font.family: "Segoe MDL2 Assets"; font.pixelSize: Math.round(20*bridge.fontScale); color: bridge.palette.text }
                    ActionButton { text: "\uE8A7"; font.family: "Segoe MDL2 Assets"; Accessible.name: bridge.translate("Mini player"); ToolTip.visible: hovered; ToolTip.text: Accessible.name; onClicked: {floatingPlayer.show();floatingPlayer.raise();floatingPlayer.requestActivate();app.Window.window.hide()} }
                    OndaSlider { id: volume; Layout.fillWidth: true; Layout.maximumWidth: 250; Layout.minimumWidth: 70; value: 80; Accessible.name: bridge.translate("Volume") }
                    Item { Layout.fillWidth: true }
                    Column { spacing: Math.round(5*bridge.spacing); Text { text: bridge.translate("Tempo ouvido"); font.pixelSize: Math.round(11*bridge.fontScale); color: bridge.palette.muted } Text { text: bridge.elapsed; font.pixelSize: Math.round(14*bridge.fontScale); color: bridge.palette.text } }
                    Rectangle { width: 1; height: 30; color: bridge.palette.line; Layout.leftMargin: 8; Layout.rightMargin: 8 }
                    Column { spacing: Math.round(5*bridge.spacing); Text { text: bridge.translate("Saltos"); font.pixelSize: Math.round(11*bridge.fontScale); color: bridge.palette.muted } Text { text: bridge.jumps; font.pixelSize: Math.round(14*bridge.fontScale); color: bridge.palette.text } }
                }
            }
        }
    }
    Connections {
        target: app.Window.window
        function onVisibilityChanged() {
            if (app.Window.window.visibility === Window.Minimized || app.Window.window.visibility === Window.Hidden) workspace.pause_background_jukebox()
        }
    }
    EqualizerPopup { id: miniEqualizer }
    TimerPopup { id: miniTimers }
    Popup {
        id: appearance
        objectName: "appearancePopup"
        parent: Overlay.overlay; anchors.centerIn: parent
        width: 390; padding: 24; modal: true; focus: true
        background: Card { }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: bridge.animations ? 160 : 0 } }
        contentItem: ColumnLayout {
            spacing: Math.round(14*bridge.spacing)
            Text { text: bridge.translate("Aparência"); color: bridge.palette.text; font.pixelSize: Math.round(22*bridge.fontScale); font.weight: Font.DemiBold }
            Label { text: bridge.translate("Modo de aparência"); color: bridge.palette.muted }
            ChoiceBox { Layout.fillWidth: true; model: bridge.themes; currentIndex: model.indexOf(bridge.theme); displayText: bridge.translate(bridge.theme); onActivated: bridge.setAppearance(model[index],bridge.accent,bridge.animations) }
            Label { text: bridge.translate("Cor de destaque"); color: bridge.palette.muted }
            ChoiceBox { Layout.fillWidth: true; model: bridge.accents; currentIndex: model.indexOf(bridge.accent); displayText: bridge.translate(bridge.accent); onActivated: bridge.setAppearance(bridge.theme,model[index],bridge.animations) }
            OndaSwitch { text: bridge.translate("Animações da interface"); checked: bridge.animations; onToggled: bridge.setAppearance(bridge.theme,bridge.accent,checked) }
            ActionButton { Layout.alignment: Qt.AlignRight; primary: true; text: bridge.translate("Pronto"); onClicked: appearance.close() }
        }
    }
    SettingsPopup { id: settings }
    ShortcutsPopup { id: shortcuts }
    DecisionPopup {}
    ComparisonPopup {}
    CoverCropPopup {}
    Popup {
        id: messagePopup; objectName: "messagePopup"; parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(parent.width-48,Math.max(300,Math.min(680,messageMeasure.boundingRect.width+60),headingMeasure.boundingRect.width+48)); height: Math.min(500,parent.height-48,messageText.contentHeight+messageHeading.implicitHeight+messageDone.implicitHeight+72); padding: 24; modal: true; focus: true
        property string heading: ""; property string body: ""
        TextMetrics { id: messageMeasure; font: messageText.font; text: messagePopup.body }
        TextMetrics { id: headingMeasure; font: messageHeading.font; text: messagePopup.heading }
        background: Card {}
        contentItem: ColumnLayout { spacing: 12
            Label { id: messageHeading; wrapMode: Text.Wrap; text: messagePopup.heading; font.pixelSize: Math.round(22*bridge.fontScale); color: bridge.palette.text; Layout.fillWidth: true }
            ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth; clip: true; TextArea { id: messageText; width: parent.availableWidth; padding: 0; textFormat: Text.PlainText; text: messagePopup.body; readOnly: true; wrapMode: Text.Wrap; selectByMouse: true; color: bridge.palette.text } }
            ActionButton { id: messageDone; primary: true; text: bridge.translate("Pronto"); Layout.alignment: Qt.AlignRight; onClicked: messagePopup.close() }
        }
    }
    Connections { target: workspace
        function onSettingsRequested() { settings.open() }
        function onSettingsCategoryRequested(category) { settings.category=category;settings.open() }
        function onShortcutsRequested() { shortcuts.open() }
        function onMessage(title,text) { messagePopup.heading=title;messagePopup.body=text;messagePopup.open() }
    }
}
