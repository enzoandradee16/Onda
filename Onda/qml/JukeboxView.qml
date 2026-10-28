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
            OndaTextField {
                id: query; Layout.fillWidth: true; implicitHeight: 44; placeholderText: bridge.translate("Música, artista ou link de música, álbum ou playlist"); selectByMouse: true
                color: bridge.palette.text; placeholderTextColor: bridge.palette.muted; font.pixelSize: Math.round(14*bridge.fontScale)
                background: Rectangle { radius: 8; color: bridge.palette.surface; border.color: query.activeFocus ? bridge.palette.accent : bridge.palette.line; border.width: query.activeFocus ? 2 : 1 }
                onAccepted: if (!bridge.state.busy) bridge.search(text)
            }
            ActionButton { primary: true; text: bridge.translate(bridge.state.busy ? "Cancelar" : "Pesquisar"); enabled: bridge.state.busy || query.text.trim().length>0; onClicked: if (bridge.state.busy) bridge.cancelOperation(); else bridge.search(query.text) }
            ActionButton { text: bridge.translate("Abrir arquivo"); enabled: !bridge.state.busy; onClicked: fileDialog.open() }
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
            }
        }
        GridLayout {
            Layout.fillWidth:true;columns:page.availableWidth>=1100?3:page.availableWidth>=700?2:1;columnSpacing:16;rowSpacing:16
            UnifiedEffectsCard {Layout.fillWidth:true;Layout.fillHeight:true;Layout.preferredWidth:330}
            Card {
                Layout.fillWidth:true;Layout.fillHeight:true;Layout.preferredWidth:330;implicitHeight:405
                ColumnLayout {
                    anchors.fill:parent;anchors.margins:20;spacing:12
                    OndaSwitch {objectName:"unifiedJukeboxEnabled";Layout.fillWidth:true;text:bridge.translate("Jukebox infinito");checked:!bridge.playbackParams.normal;onToggled:bridge.setParams(variation.value,smooth.value,page.volume,!checked)}
                    Item {
                        id:sharedGraph;Layout.fillWidth:true;Layout.fillHeight:true;Layout.minimumHeight:100
                        BeatGraph {anchors.fill:parent;graphData:page.visible?bridge.graph:({count:64,links:[],flow:[]});accent:bridge.palette.accent;muted:bridge.palette.muted}
                        Rectangle {
                            readonly property real radiusOrbit:Math.min(sharedGraph.width,sharedGraph.height)*.42
                            x:sharedGraph.width/2+bridge.cursor.x*radiusOrbit-width/2;y:sharedGraph.height/2+bridge.cursor.y*radiusOrbit-height/2
                            width:12;height:12;radius:6;color:bridge.palette.accent
                        }
                        MouseArea {anchors.fill:parent;enabled:bridge.state.ready;onClicked:function(mouse){const dx=mouse.x-width/2,dy=mouse.y-height/2,r=Math.min(width,height)*.42;if(Math.abs(Math.sqrt(dx*dx+dy*dy)-r)<22)bridge.seek(Math.round(((Math.atan2(dy,dx)+Math.PI/2+2*Math.PI)%(2*Math.PI))/(2*Math.PI)*bridge.graph.count)%bridge.graph.count)}}
                    }
                    Label {text:bridge.translate("Variação");color:bridge.palette.text}
                    OndaSlider {id:variation;Layout.fillWidth:true;value:bridge.playbackParams.variation;enabled:!bridge.playbackParams.normal;Accessible.name:bridge.translate("Variação");onMoved:page.updateParams()}
                    Label {text:bridge.translate("Transição suave");color:bridge.palette.text}
                    OndaSlider {id:smooth;Layout.fillWidth:true;value:bridge.playbackParams.smooth;enabled:!bridge.playbackParams.normal;Accessible.name:bridge.translate("Transição suave");onMoved:page.updateParams()}
                }
            }
            UnifiedQueue {Layout.fillWidth:true;Layout.fillHeight:true;Layout.preferredWidth:330;Layout.columnSpan:page.availableWidth>=700&&page.availableWidth<1100?2:1}
        }
        Item { height: 8 }
    }
    property real volume: 80
    function updateParams() { bridge.setParams(variation.value,smooth.value,volume,bridge.playbackParams.normal) }
    onVolumeChanged: updateParams()
}
