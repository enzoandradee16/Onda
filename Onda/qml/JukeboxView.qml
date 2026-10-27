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
    Menu {id:jukeboxActions;objectName:"jukeboxContextMenu"
        OndaMenuItem {text:bridge.translate("Abrir arquivo");onTriggered:fileDialog.open()}
        OndaMenuItem {text:bridge.translate("Fila de reprodução");onTriggered:workspace.setOption("jukeboxQueueOpen",true)}
        OndaMenuItem {text:bridge.translate("Reproduzir / Pausar");enabled:bridge.state.ready;onTriggered:bridge.playPause()}
        OndaMenuItem {text:bridge.translate("Buscar letra online");enabled:bridge.state.ready;onTriggered:workspace.invoke("lyrics_online",{jukebox:true})}
        OndaMenuItem {text:bridge.translate("Equalizador");onTriggered:equalizer.open()}
    }
    TapHandler {enabled:!bridge.state.results.length;acceptedButtons:Qt.RightButton;onTapped:jukeboxActions.popup()}

    FileDialog { id: fileDialog; title: bridge.translate("Abrir arquivo"); nameFilters: [bridge.translate("Áudio")+" (*.mp3 *.m4a *.flac *.wav *.ogg *.opus *.aac *.webm)",bridge.translate("Todos os arquivos")+" (*)"]; onAccepted: bridge.openFile(selectedFile) }
    property string currentLyric: ""
    property string currentLine: ""
    Timer { interval: 100; running: page.visible; repeat: true; onTriggered: {var frame=workspace.lyricsFrame();page.currentLyric=frame.text;page.currentLine=String(frame.active)} }
    EqualizerPopup { id: equalizer }
    TimerPopup { id: timerPopup }
    ColumnLayout {
        width: page.availableWidth; spacing: Math.round(16*bridge.spacing)
        RowLayout {
            Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
            ActionButton { primary: true; text: bridge.translate("Abrir arquivo"); enabled: !bridge.state.busy; onClicked: fileDialog.open() }
            OndaTextField {
                id: query; Layout.fillWidth: true; implicitHeight: 44; placeholderText: bridge.translate("Música, artista ou link de música, álbum ou playlist"); selectByMouse: true
                color: bridge.palette.text; placeholderTextColor: bridge.palette.muted; font.pixelSize: Math.round(14*bridge.fontScale)
                background: Rectangle { radius: 8; color: bridge.palette.surface; border.color: query.activeFocus ? bridge.palette.accent : bridge.palette.line; border.width: query.activeFocus ? 2 : 1 }
                onAccepted: if (!bridge.state.busy) bridge.search(text)
            }
            ActionButton { primary: true; text: bridge.translate(bridge.state.busy ? "Cancelar" : "Pesquisar"); enabled: bridge.state.busy || query.text.trim().length>0; onClicked: if (bridge.state.busy) bridge.cancelOperation(); else bridge.search(query.text) }
        }
        Flow { Layout.fillWidth: true; spacing: 8
            ActionButton { text: bridge.translate("Próxima"); enabled: bridge.playback.current+1<bridge.queuedTracks.length; onClicked: bridge.nextTrack() }
        }
        Card {
            Layout.fillWidth: true
            implicitHeight: bridge.state.results.length ? Math.min(282,resultList.contentHeight+58) : 0
            visible: implicitHeight>0; clip: true
            Behavior on implicitHeight { NumberAnimation { duration: bridge.animations ? 160 : 0; easing.type: Easing.OutCubic } }
            RowLayout {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 8
                Label { Layout.fillWidth: true; text: bridge.translate("Resultados"); color: bridge.palette.text }
                PlaybackButton { objectName: "closeJukeboxSearch"; glyph: "close"; Accessible.name: bridge.translate("Fechar pesquisa"); ToolTip.visible: hovered; ToolTip.text: Accessible.name; onClicked: bridge.closeSearch() }
            }
            ListView {
                id: resultList; anchors.fill: parent; anchors.margins: 6; anchors.topMargin: 56; clip: true; model: bridge.state.results
                delegate: ItemDelegate {
                    required property var modelData; required property int index
                        Component.onCompleted: workspace.invoke("request_card_details",{model:"jukeboxSearch",source:modelData.source_url || ""})
                        ListView.onReused: workspace.invoke("request_card_details",{model:"jukeboxSearch",source:modelData.source_url || ""})
                        Menu {id:resultActions
                            OndaMenuItem {text:bridge.translate("Reproduzir");onTriggered:bridge.selectResult(index)}
                            OndaMenuItem {text:bridge.translate("Adicionar à fila");onTriggered:bridge.enqueueResult(index)}
                            OndaMenuItem {text:bridge.translate("Ver no catálogo");onTriggered:workspace.invoke("open_url",{url:modelData.source_url})}
                            OndaMenuItem {text:bridge.translate("Copiar link");onTriggered:workspace.invoke("copy_link",{url:modelData.source_url})}
                        }
                        TapHandler {acceptedButtons:Qt.RightButton;onTapped:resultActions.popup()}

                    width: resultList.width; height: modelData.release_date ? 108 : 84
                    contentItem: RowLayout {
                        Rectangle { Layout.preferredWidth: 64; Layout.preferredHeight: 64; radius: 6; color: bridge.palette.input
                            RoundedArtwork { id: searchCover; objectName: "jukeboxSearchArtwork"; anchors.fill: parent; source: modelData.cover || ""; fillMode: Image.PreserveAspectFit; sourceSize.width: 128; sourceSize.height: 128; asynchronous: true }
                            Label { anchors.centerIn: parent; visible: searchCover.status !== Image.Ready; text: "♪"; color: bridge.palette.muted }
                        }
                        ColumnLayout { Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 4
                            Label { Layout.fillWidth: true; text: modelData.title; color: bridge.palette.text; elide: Text.ElideRight }
                            Label { Layout.fillWidth: true; text: modelData.artist; color: bridge.palette.muted; elide: Text.ElideRight }
                            Label { Layout.fillWidth: true; text: modelData.album || ""; color: bridge.palette.muted; elide: Text.ElideRight }
                                Label {Layout.fillWidth:true;visible:!!modelData.release_date;text:bridge.translate("Data de lançamento")+": "+workspace.releaseDateText(modelData.release_date || "");color:bridge.palette.muted;elide:Text.ElideRight}
                        }
                        ActionButton { text: bridge.translate("Adicionar à fila"); onClicked: {bridge.enqueueResult(index)} }
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
                    RoundedArtwork { anchors.fill: parent; source: bridge.state.cover; sourceSize.width: 292; sourceSize.height: 292; fillMode: Image.PreserveAspectCrop; visible: source.toString().length>0 }
                    Text { anchors.centerIn: parent; visible: bridge.state.cover.length===0; text: "♪"; color: bridge.palette.muted; font.pixelSize: Math.round(38*bridge.fontScale) }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: Math.round(5*bridge.spacing)
                    Text { Layout.fillWidth: true; text: bridge.state.title; elide: Text.ElideRight; color: bridge.palette.text; font.pixelSize: Math.round(23*bridge.fontScale); font.weight: Font.DemiBold }
                    Text { Layout.fillWidth: true; text: bridge.state.artist; visible: text.length>0; elide: Text.ElideRight; color: bridge.palette.text; font.pixelSize: Math.round(17*bridge.fontScale) }
                    Text { Layout.fillWidth: true; text: bridge.state.album; visible: text.length>0; elide: Text.ElideRight; color: bridge.palette.muted; font.pixelSize: Math.round(16*bridge.fontScale) }
                    Text { Layout.fillWidth: true; text: bridge.state.paused ? bridge.translate("Pausado.") : bridge.state.status; elide: Text.ElideRight; color: bridge.state.playing ? bridge.palette.accent : bridge.palette.muted; font.pixelSize: Math.round(14*bridge.fontScale) }
                }
                AnimatedLyric { Layout.fillWidth: true; Layout.preferredWidth: 300; lineKey: page.currentLine; text: page.currentLyric; textFormat: Text.RichText; visible: text.length>0 }
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
