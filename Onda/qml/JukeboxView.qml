import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Onda 1.0
ScrollView {
    id: page
    objectName: "jukeboxView"
    contentWidth: availableWidth
    clip: true
    FileDialog { id: fileDialog; title: bridge.translate("Abrir arquivo"); nameFilters: [bridge.translate("Áudio")+" (*.mp3 *.m4a *.flac *.wav *.ogg *.opus *.aac *.webm)",bridge.translate("Todos os arquivos")+" (*)"]; onAccepted: bridge.openFile(selectedFile) }
    FileDialog { id: queueFiles; title: bridge.translate("Adicionar músicas à fila"); fileMode: FileDialog.OpenFiles; nameFilters: ["Áudio (*.mp3 *.m4a *.flac *.wav *.ogg *.opus *.aac *.webm)"]; onAccepted: { bridge.enqueueFiles(selectedFiles);page.queueExpanded=true } }
    property string currentLyric: ""
    Timer { interval: 100; running: page.visible; repeat: true; onTriggered: page.currentLyric=workspace.lyricsFrame().text }
    property bool queueExpanded: false
    EqualizerPopup { id: equalizer }
    TimerPopup { id: timerPopup }
    ColumnLayout {
        width: page.availableWidth; spacing: Math.round(16*bridge.spacing)
        AnimatedLyric { Layout.fillWidth: true; text: page.currentLyric; textFormat: Text.RichText; visible: text.length>0 }
        RowLayout {
            Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
            ActionButton { primary: true; text: bridge.translate("Abrir arquivo"); enabled: !bridge.state.busy; onClicked: fileDialog.open() }
            OndaTextField {
                id: query; Layout.fillWidth: true; implicitHeight: 44; placeholderText: bridge.translate("Pesquise uma música ou cole um link"); selectByMouse: true
                color: bridge.palette.text; placeholderTextColor: bridge.palette.muted; font.pixelSize: Math.round(14*bridge.fontScale)
                background: Rectangle { radius: 8; color: bridge.palette.surface; border.color: query.activeFocus ? bridge.palette.accent : bridge.palette.line; border.width: query.activeFocus ? 2 : 1 }
                onAccepted: if (!bridge.state.busy) bridge.search(text)
            }
            ActionButton { primary: true; text: bridge.translate(bridge.state.busy ? "Cancelar" : "Pesquisar"); enabled: bridge.state.busy || query.text.trim().length>0; onClicked: if (bridge.state.busy) bridge.cancelOperation(); else bridge.search(query.text) }
        }
        Flow { Layout.fillWidth: true; spacing: 8
            ActionButton { text: bridge.translate("Adicionar arquivos à fila"); onClicked: queueFiles.open() }
            ActionButton { text: bridge.translate("Fila de reprodução")+" ("+bridge.queuedTracks.length+")"; onClicked: page.queueExpanded=!page.queueExpanded }
            ActionButton { text: bridge.translate("Próxima"); enabled: bridge.queuedTracks.length>0; onClicked: bridge.nextTrack() }
            ActionButton { text: bridge.translate("Timers"); onClicked: timerPopup.open() }

        }
        Card { visible: page.queueExpanded; Layout.fillWidth: true; implicitHeight: bridge.queuedTracks.length ? Math.min(340,bridge.queuedTracks.length*92+64) : 110
            ColumnLayout { anchors.fill: parent; anchors.margins: 10
                RowLayout { Layout.fillWidth: true; Label { Layout.fillWidth: true; text: bridge.translate("Fila de reprodução"); color: bridge.palette.text } ActionButton { text: bridge.translate("Limpar"); enabled: bridge.queuedTracks.length>0; onClicked: bridge.clearPlaybackQueue() } }
                ListView { id: queueList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; model: bridge.queuedTracks; ScrollBar.vertical: ScrollBar {}
                    delegate: RowLayout { required property var modelData; required property int index; width: queueList.width; height: 92
                        Rectangle { Layout.preferredWidth: 80; Layout.preferredHeight: 80; radius: 6; color: bridge.palette.input
                            Image { id: playbackCover; objectName: "playbackQueueArtwork"; anchors.fill: parent; source: modelData.cover || ""; fillMode: Image.PreserveAspectFit; sourceSize.width: 160; sourceSize.height: 160; asynchronous: true }
                            Label { anchors.centerIn: parent; visible: playbackCover.status !== Image.Ready; text: "♪"; color: bridge.palette.muted; font.pixelSize: 30 }
                        }
                        ColumnLayout { Layout.fillWidth: true; spacing: 3
                            Label { Layout.fillWidth: true; text: (modelData.current ? "▶ " : "")+modelData.title; color: modelData.current ? bridge.palette.accent : bridge.palette.text; elide: Text.ElideRight }
                            Label { Layout.fillWidth: true; visible: !!modelData.artist; text: modelData.artist || ""; color: bridge.palette.muted; elide: Text.ElideRight }
                            Label { Layout.fillWidth: true; visible: !!modelData.album; text: modelData.album || ""; color: bridge.palette.muted; elide: Text.ElideRight }
                            Label { Layout.fillWidth: true; elide: Text.ElideRight; text: bridge.translate(({pending:"Aguardando análise",preparing:"Analisando ritmo e trechos…",ready:"Pronta para reproduzir",error:"Erro na análise"})[modelData.analysis] || ""); color: modelData.analysis === "error" ? bridge.palette.accent : bridge.palette.muted }
                            Label { visible: modelData.duration > 0; text: workspace.clock(modelData.duration || 0); color: bridge.palette.muted }
                        }
                        ActionButton { text: bridge.translate(modelData.analysis === "error" ? "Tentar novamente" : "Tocar"); onClicked: bridge.playQueued(index) }
                        ActionButton { text: "↑"; enabled: index>0; onClicked: bridge.moveQueued(index,-1) }
                        ActionButton { text: "↓"; enabled: index+1<bridge.queuedTracks.length; onClicked: bridge.moveQueued(index,1) }
                        ActionButton { text: "×"; Accessible.name: bridge.translate("Remover da fila"); onClicked: bridge.removeQueued(index) }
                    }
                    Label { anchors.centerIn: parent; visible: bridge.queuedTracks.length===0; text: bridge.translate("Adicione arquivos ou músicas dos resultados."); color: bridge.palette.muted }
                }
            }
        }
        Card {
            Layout.fillWidth: true
            implicitHeight: bridge.state.results.length ? Math.min(282,resultList.contentHeight+58) : 0
            visible: implicitHeight>0; clip: true
            Behavior on implicitHeight { NumberAnimation { duration: bridge.animations ? 160 : 0; easing.type: Easing.OutCubic } }
            RowLayout {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 8
                Label { Layout.fillWidth: true; text: bridge.translate("Resultados"); color: bridge.palette.text }
                ActionButton { objectName: "closeJukeboxSearch"; text: "×"; Accessible.name: bridge.translate("Fechar pesquisa"); ToolTip.visible: hovered; ToolTip.text: Accessible.name; onClicked: bridge.closeSearch() }
            }
            ListView {
                id: resultList; anchors.fill: parent; anchors.margins: 6; anchors.topMargin: 56; clip: true; model: bridge.state.results
                delegate: ItemDelegate {
                    required property var modelData; required property int index
                    width: resultList.width; height: 50
                    contentItem: RowLayout {
                        ColumnLayout { Layout.fillWidth: true; Label { Layout.fillWidth: true; text: modelData.title; color: bridge.palette.text; elide: Text.ElideRight } Label { Layout.fillWidth: true; text: modelData.artist; color: bridge.palette.muted; elide: Text.ElideRight } }
                        ActionButton { text: bridge.translate("Adicionar à fila"); onClicked: {bridge.enqueueResult(index);page.queueExpanded=true} }
                    }
                    onClicked: bridge.selectResult(index)
                }
            }
        }
        OndaProgressBar { Layout.fillWidth: true; visible: bridge.state.busy; from: 0; to: 100; value: bridge.state.progress; indeterminate: bridge.state.progress===0 }
        Card {
            Layout.fillWidth: true; implicitHeight: 166
            RowLayout {
                anchors.fill: parent; anchors.margins: 10; spacing: Math.round(16*bridge.spacing)
                Rectangle {
                    Layout.preferredWidth: 146; Layout.preferredHeight: 146; radius: 8; color: bridge.palette.input; clip: true
                    Image { anchors.fill: parent; source: bridge.state.cover; sourceSize.width: 292; sourceSize.height: 292; fillMode: Image.PreserveAspectCrop; visible: source.toString().length>0 }
                    Text { anchors.centerIn: parent; visible: bridge.state.cover.length===0; text: "♪"; color: bridge.palette.muted; font.pixelSize: Math.round(38*bridge.fontScale) }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: Math.round(5*bridge.spacing)
                    Text { Layout.fillWidth: true; text: bridge.state.title; elide: Text.ElideRight; color: bridge.palette.text; font.pixelSize: Math.round(23*bridge.fontScale); font.weight: Font.DemiBold }
                    Text { Layout.fillWidth: true; text: bridge.state.artist; visible: text.length>0; elide: Text.ElideRight; color: bridge.palette.text; font.pixelSize: Math.round(17*bridge.fontScale) }
                    Text { Layout.fillWidth: true; text: bridge.state.album; visible: text.length>0; elide: Text.ElideRight; color: bridge.palette.muted; font.pixelSize: Math.round(16*bridge.fontScale) }
                    Text { Layout.fillWidth: true; text: bridge.state.paused ? bridge.translate("Pausado.") : bridge.state.status; elide: Text.ElideRight; color: bridge.state.playing ? bridge.palette.accent : bridge.palette.muted; font.pixelSize: Math.round(14*bridge.fontScale) }
                }
                ActionButton { primary: true; text: bridge.translate("Equalizador"); onClicked: equalizer.open() }
            }
        }
        GridLayout {
            Layout.fillWidth: true; columns: page.availableWidth>=760 ? 2 : 1; columnSpacing: 16; rowSpacing: 16
            Card {
                Layout.fillWidth: true; Layout.preferredWidth: 430; Layout.preferredHeight: 405
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: Math.round(4*bridge.spacing)
                    Item {
                        id: graphArea; readonly property int beatCount: page.visible ? bridge.graph.count : 64; Layout.fillWidth: true; Layout.fillHeight: true
                        BeatGraph { id: graph; anchors.fill: parent; graphData: page.visible ? bridge.graph : ({count:64,links:[],flow:[]}); accent: bridge.palette.accent; muted: bridge.palette.muted }
                        Rectangle {
                            id: marker
                            property real orbitRadius: Math.min(graphArea.width,graphArea.height)*0.42
                            x: graphArea.width/2+bridge.cursor.x*orbitRadius-width/2
                            y: graphArea.height/2+bridge.cursor.y*orbitRadius-height/2
                            width: 14; height: 14; radius: 7; color: bridge.palette.accent; border.color: bridge.palette.surface; border.width: 2
                            scale: bridge.state.playing ? 1+0.25*Math.pow(1-bridge.phase,3) : 1
                            Behavior on scale { NumberAnimation { duration: bridge.animations ? 55 : 0 } }
                        }
                        MouseArea {
                            anchors.fill: parent; enabled: bridge.state.ready && !bridge.state.busy
                            onClicked: function(mouse) {
                                const dx=mouse.x-width/2,dy=mouse.y-height/2,r=Math.min(width,height)*0.42
                                if(Math.abs(Math.sqrt(dx*dx+dy*dy)-r)<22)bridge.seek(Math.round(((Math.atan2(dy,dx)+Math.PI/2+2*Math.PI)%(2*Math.PI))/(2*Math.PI)*bridge.graph.count)%bridge.graph.count)
                            }
                        }
                    }
                    RowLayout {
                        Layout.alignment: Qt.AlignHCenter; spacing: Math.round(8*bridge.spacing)
                        Rectangle { width: 7; height: 7; radius: 4; color: bridge.palette.muted }
                        Text { text: bridge.translate("Conexões possíveis"); color: bridge.palette.muted; font.pixelSize: Math.round(11*bridge.fontScale) }
                        Item { width: 8 }
                        Rectangle { width: 7; height: 7; radius: 4; color: bridge.palette.accent }
                        Text { text: bridge.translate("Trajeto reproduzido"); color: bridge.palette.muted; font.pixelSize: Math.round(11*bridge.fontScale) }
                    }
                }
            }
            Card {
                Layout.fillWidth: true; Layout.preferredWidth: 350; Layout.preferredHeight: 405
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 22; spacing: Math.round(8*bridge.spacing)
                    Text { text: bridge.translate("Ajustes do Jukebox"); color: bridge.palette.text; font.pixelSize: Math.round(19*bridge.fontScale); font.weight: Font.DemiBold }
                    Item { height: 8 }
                    Text { text: bridge.translate("Variação"); color: bridge.palette.text; font.pixelSize: Math.round(14*bridge.fontScale); font.weight: Font.Medium }
                    OndaSlider { id: variation; Layout.fillWidth: true; value: 45; onMoved: page.updateParams() }
                    RowLayout { Layout.fillWidth: true; Text { text: bridge.translate("Mais fiel"); color: bridge.palette.muted; font.pixelSize: Math.round(12*bridge.fontScale) } Item { Layout.fillWidth: true } Text { text: bridge.translate("Mais saltos"); color: bridge.palette.muted; font.pixelSize: Math.round(12*bridge.fontScale) } }
                    Item { height: 6 }
                    Text { text: bridge.translate("Transição suave"); color: bridge.palette.text; font.pixelSize: Math.round(14*bridge.fontScale); font.weight: Font.Medium }
                    OndaSlider { id: smooth; Layout.fillWidth: true; value: 35; onMoved: page.updateParams() }
                    RowLayout { Layout.fillWidth: true; Text { text: bridge.translate("Curta"); color: bridge.palette.muted; font.pixelSize: Math.round(12*bridge.fontScale) } Item { Layout.fillWidth: true } Text { text: bridge.translate("Longa"); color: bridge.palette.muted; font.pixelSize: Math.round(12*bridge.fontScale) } }
                    Rectangle {
                        Layout.fillWidth: true; implicitHeight: info.implicitHeight+22; color: bridge.palette.input; radius: 8
                        Text { id: info; anchors.fill: parent; anchors.margins: 11; text: bridge.translate("Saltos entre trechos compatíveis.")+"\n"+bridge.translate("A análise fica salva para os próximos usos."); color: bridge.palette.muted; font.pixelSize: Math.round(12*bridge.fontScale); wrapMode: Text.WordWrap }
                    }
                    Item { Layout.fillHeight: true }
                    OndaSwitch { id: normal; Layout.fillWidth: true; text: bridge.translate("Reprodução normal"); onToggled: page.updateParams() }
                }
            }
        }
        Item { height: 8 }
    }
    property real volume: 80
    function updateParams() { bridge.setParams(variation.value,smooth.value,volume,normal.checked) }
    onVolumeChanged: updateParams()
}
