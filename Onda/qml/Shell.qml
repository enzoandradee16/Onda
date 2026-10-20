import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Pane {
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
        Sidebar { id: sidebar; onSettingsRequested: workspace.showSettings() }
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
                    visible: workspace.currentPage === "effects" || workspace.currentPage === "jukebox"; Layout.topMargin: 12; spacing: Math.round(0*bridge.spacing)
                    ActionButton { text: bridge.translate("Efeitos"); primary: workspace.currentPage === "effects"; onClicked: workspace.selectPage("effects"); Layout.preferredWidth: 130 }
                    ActionButton { text: bridge.translate("Jukebox infinito"); primary: workspace.currentPage === "jukebox"; onClicked: workspace.selectPage("jukebox"); Layout.preferredWidth: 178 }
                }
            }
            Flow { Layout.fillWidth: true; Layout.leftMargin: 24; Layout.rightMargin: 24; spacing: Math.round(8*bridge.spacing); visible: app.remainingTasks.length > 0
                Repeater { model: app.remainingTasks; ActionButton { required property string modelData; text: bridge.translate("Cancelar")+" "+workspace.taskLabel(modelData); onClicked: workspace.invoke("cancel_task",{name:modelData}) } }
            }
            WorkspaceView { objectName: "workspaceArea"; visible: workspace.currentPage !== "jukebox"; active: visible; Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 24; Layout.rightMargin: 24; Layout.bottomMargin: 16 }
            JukeboxView { id: jukebox; visible: workspace.currentPage === "jukebox"; Layout.fillWidth: true; Layout.fillHeight: true; Layout.leftMargin: 24; Layout.rightMargin: 24; volume: volume.value }
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
                    Text { text: "\uE767"; font.family: "Segoe MDL2 Assets"; font.pixelSize: Math.round(20*bridge.fontScale); color: bridge.palette.text }
                    OndaSlider { id: volume; Layout.fillWidth: true; Layout.maximumWidth: 250; Layout.minimumWidth: 70; value: 80; Accessible.name: bridge.translate("Volume") }
                    Item { Layout.fillWidth: true }
                    Column { spacing: Math.round(5*bridge.spacing); Text { text: bridge.translate("Tempo ouvido"); font.pixelSize: Math.round(11*bridge.fontScale); color: bridge.palette.muted } Text { text: bridge.elapsed; font.pixelSize: Math.round(14*bridge.fontScale); color: bridge.palette.text } }
                    Rectangle { width: 1; height: 30; color: bridge.palette.line; Layout.leftMargin: 8; Layout.rightMargin: 8 }
                    Column { spacing: Math.round(5*bridge.spacing); Text { text: bridge.translate("Saltos"); font.pixelSize: Math.round(11*bridge.fontScale); color: bridge.palette.muted } Text { text: bridge.jumps; font.pixelSize: Math.round(14*bridge.fontScale); color: bridge.palette.text } }
                }
            }
        }
    }
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
            ComboBox { Layout.fillWidth: true; model: bridge.themes; currentIndex: model.indexOf(bridge.theme); displayText: bridge.translate(bridge.theme); onActivated: bridge.setAppearance(model[index],bridge.accent,bridge.animations); delegate: ItemDelegate { width: parent.width; text: bridge.translate(modelData) } }
            Label { text: bridge.translate("Cor de destaque"); color: bridge.palette.muted }
            ComboBox { Layout.fillWidth: true; model: bridge.accents; currentIndex: model.indexOf(bridge.accent); displayText: bridge.translate(bridge.accent); onActivated: bridge.setAppearance(bridge.theme,model[index],bridge.animations); delegate: ItemDelegate { width: parent.width; text: bridge.translate(modelData) } }
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
        function onShortcutsRequested() { shortcuts.open() }
        function onMessage(title,text) { messagePopup.heading=title;messagePopup.body=text;messagePopup.open() }
    }
    Label { anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.leftMargin: 244; anchors.bottomMargin: 2; height: 18; text: workspace.status; color: bridge.palette.muted; font.pixelSize: Math.round(11*bridge.fontScale); elide: Text.ElideRight; visible: workspace.currentPage !== "jukebox" }
}
