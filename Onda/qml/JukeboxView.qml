import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import Onda 1.0
OndaScrollView {
    id: page

    property var scrollTopButton: ScrollToTop { target: page.contentItem; viewport: page }
    objectName: "jukeboxView"
    contentWidth: availableWidth
    clip: true
    OndaMenu {id:jukeboxActions;objectName:"jukeboxContextMenu"
        OndaMenuItem {text:bridge.translate("Abrir arquivo");onTriggered:fileDialog.open()}
        OndaMenuItem {text:bridge.translate("Fila de reprodução");onTriggered:workspace.setOption("jukeboxQueueOpen",true)}
        OndaMenuItem {text:bridge.translate("Reproduzir / Pausar");enabled:bridge.stateValue(bridge.stateRevision,"ready");onTriggered:bridge.playPause()}
        OndaMenuItem {text:bridge.translate("Buscar letra online");enabled:bridge.stateValue(bridge.stateRevision,"ready");onTriggered:workspace.invoke("lyrics_online",{jukebox:true})}
        OndaMenuItem {text:bridge.translate("Equalizador");onTriggered:equalizer.open()}
    }
    TapHandler {enabled:!workspace.optionValue(workspace.optionsRevision,"jukeboxQueueOpen") && !bridge.stateValue(bridge.stateRevision,"results").length;acceptedButtons:Qt.RightButton;onTapped:jukeboxActions.popup()}

    FileDialog { id: fileDialog; title: bridge.translate("Abrir arquivo"); nameFilters: [bridge.translate("Áudio")+" (*.mp3 *.m4a *.flac *.wav *.ogg *.opus *.aac *.webm)",bridge.translate("Todos os arquivos")+" (*)"]; onAccepted: bridge.openFile(selectedFile) }
    property bool adjustmentsExpanded: true
    property string currentLyric: ""
    property string currentLine: ""
    Timer { interval: 100; running: page.visible; repeat: true; onTriggered: {var frame=workspace.lyricsClock(true);page.currentLyric=frame.text;page.currentLine=String(frame.active)} }
    EqualizerPopup { id: equalizer }
    TimerPopup { id: timerPopup }
    ColumnLayout {
        width: page.availableWidth; spacing: Math.round(16*bridge.spacing)
        GridLayout {
            Layout.fillWidth: true; columns: page.availableWidth < 680*bridge.fontScale ? 2 : 3; columnSpacing: Math.round(10*bridge.spacing); rowSpacing: 8
            OndaTextField {
                id: query; objectName:"playbackSearchField"; Layout.columnSpan: page.availableWidth < 680*bridge.fontScale ? 2 : 1; Layout.minimumWidth: 0; Layout.fillWidth: true; implicitHeight: 44; placeholderText: bridge.translate("Música, artista ou link de música, álbum ou playlist"); selectByMouse: true
                color: bridge.palette.text; placeholderTextColor: bridge.palette.muted; font.pixelSize: Math.round(14*bridge.fontScale)
                background: Rectangle { radius: 8; color: bridge.palette.surface; border.color: query.activeFocus ? bridge.palette.accent : bridge.palette.line; border.width: query.activeFocus ? 2 : 1 }
                onAccepted: if (!bridge.stateValue(bridge.stateRevision,"busy")) bridge.search(text)
            }
            ActionButton { Layout.fillWidth: page.availableWidth < 680*bridge.fontScale; objectName:"playbackSearchButton"; primary: true; text: bridge.translate(bridge.stateValue(bridge.stateRevision,"busy") ? "Cancelar" : "Pesquisar"); enabled: true; onClicked: if (bridge.stateValue(bridge.stateRevision,"busy")) bridge.cancelOperation(); else bridge.search(query.text) }
            ActionButton { Layout.fillWidth: page.availableWidth < 680*bridge.fontScale; text: bridge.translate("Abrir arquivo"); enabled: !bridge.stateValue(bridge.stateRevision,"busy"); onClicked: fileDialog.open() }
        }
        Card {
            Layout.fillWidth: true
            implicitHeight: bridge.stateValue(bridge.stateRevision,"results").length ? Math.min(282,resultList.contentHeight+58) : 0
            visible: implicitHeight>0; clip: true
            Behavior on implicitHeight { NumberAnimation { duration: bridge.animations ? 160 : 0; easing.type: Easing.OutCubic } }
            RowLayout {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 8
                Label { Layout.fillWidth: true; text: bridge.translate("Resultados"); color: bridge.palette.text }
                PlaybackButton { objectName: "closeJukeboxSearch"; glyph: "close"; Accessible.name: bridge.translate("Fechar pesquisa"); ToolTip.visible: hovered; ToolTip.text: Accessible.name; onClicked: bridge.closeSearch() }
            }
            OndaListView {
                id: resultList; anchors.fill: parent; anchors.margins: 6; anchors.topMargin: 56; clip: true; model: bridge.stateValue(bridge.stateRevision,"results")
                delegate: ItemDelegate {
                    required property var modelData; required property int index
                        Component.onCompleted: workspace.invoke("request_card_details",{model:"jukeboxSearch",source:modelData.source_url || ""})
                        ListView.onReused: workspace.invoke("request_card_details",{model:"jukeboxSearch",source:modelData.source_url || ""})
                        OndaMenu {id:resultActions
                            OndaMenuItem {text:bridge.translate("Reproduzir");onTriggered:bridge.selectResult(index)}
                            OndaMenuItem {text:bridge.translate("Adicionar à fila");onTriggered:bridge.enqueueResult(index)}
                            OndaMenuItem {text:bridge.translate("Ver no catálogo");onTriggered:workspace.invoke("open_url",{url:modelData.source_url})}
                            OndaMenuItem {text:bridge.translate("Copiar link");onTriggered:workspace.invoke("copy_link",{url:modelData.source_url})}
                        }
                        TapHandler {acceptedButtons:Qt.RightButton;onTapped:resultActions.popup()}

                    width: resultList.contentAreaWidth; height: 84
                    background: Rectangle {
                        radius: 6
                        color: parent.hovered || parent.down || parent.activeFocus
                               ? bridge.palette.hover : "transparent"
                    }
                    contentItem: RowLayout {
                        Rectangle { Layout.preferredWidth: 56; Layout.preferredHeight: 56; radius: 6; color: bridge.palette.input
                            RoundedArtwork { id: searchCover; objectName: "jukeboxSearchArtwork"; anchors.fill: parent; source: modelData.cover || ""; fillMode: Image.PreserveAspectFit; sourceSize.width: 128; sourceSize.height: 128; asynchronous: true }
                            LineIcon { anchors.centerIn: parent; visible: searchCover.status !== Image.Ready; glyph: "music"; ink: bridge.palette.muted; width: 24; height: 24 }
                        }
                        ColumnLayout { Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 4
                            Label { Layout.fillWidth: true; text: modelData.title; font.weight: Font.DemiBold; color: bridge.palette.text; elide: Text.ElideRight }
                            Label { Layout.fillWidth: true; text: modelData.artist; color: bridge.palette.muted; elide: Text.ElideRight }
                            Label { Layout.fillWidth: true; text: workspace.albumReleaseText(modelData); color: bridge.palette.muted; elide: Text.ElideRight }
                        }
                        ActionButton { text: bridge.translate("Adicionar à fila"); onClicked: {bridge.enqueueResult(index)} }
                    }
                    onClicked: bridge.selectResult(index)
                }
            }
        }
        OndaProgressBar {
            objectName: "playbackPreparationProgress"
            Layout.fillWidth: true
            readonly property var selectedProgress: bridge.queuePreparation[bridge.searchPlaybackEntry]
            visible: bridge.stateValue(bridge.stateRevision, "busy") || selectedProgress !== undefined
            from: 0
            to: 100
            value: selectedProgress === undefined ? bridge.stateValue(bridge.stateRevision, "progress") : selectedProgress
            indeterminate: value === 0
        }
        Card {
            objectName:"playbackTrackCard"
            Layout.fillWidth: true; implicitHeight: trackLayout.implicitHeight+20;clip:true
            GridLayout {
                id: trackLayout; columns: page.availableWidth < 850 ? 2 : 3
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.margins: 10; columnSpacing: Math.round(16*bridge.spacing); rowSpacing: 12
                Rectangle {
                    Layout.preferredWidth: page.availableWidth<600 ? 96 : 146; Layout.preferredHeight: Layout.preferredWidth; radius: 8; color: bridge.palette.input; clip: true
                    RoundedArtwork { id: playbackArtwork; anchors.fill: parent; source: bridge.currentMetadata.cover_url || bridge.stateValue(bridge.stateRevision,"cover"); fallbackSource: bridge.stateValue(bridge.stateRevision,"cover"); sourceSize.width: 768; sourceSize.height: 768; fillMode: Image.PreserveAspectCrop; visible: source.toString().length>0 }
                    LineIcon { anchors.centerIn: parent; visible: playbackArtwork.status !== Image.Ready; glyph: "music"; ink: bridge.palette.muted; width: 38; height: 38 }
                }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: Math.round(5*bridge.spacing)
                    Text { Layout.fillWidth: true; text: bridge.stateValue(bridge.stateRevision,"title"); wrapMode: Text.Wrap; color: bridge.palette.text; font.pixelSize: Math.round(23*bridge.fontScale); font.weight: Font.DemiBold }
                    Text { Layout.fillWidth: true; text: bridge.stateValue(bridge.stateRevision,"artist"); visible: text.length>0; wrapMode: Text.Wrap; color: bridge.palette.text; font.pixelSize: Math.round(17*bridge.fontScale) }
                    Text { Layout.fillWidth: true; text: workspace.albumReleaseText(bridge.currentMetadata); visible: text.length>0; wrapMode: Text.Wrap; color: bridge.palette.muted; font.pixelSize: Math.round(16*bridge.fontScale) }
                    Text { Layout.fillWidth: true; text: bridge.stateValue(bridge.stateRevision,"paused") ? bridge.translate("Pausado.") : bridge.stateValue(bridge.stateRevision,"status"); wrapMode: Text.Wrap; color: bridge.stateValue(bridge.stateRevision,"playing") ? bridge.palette.accent : bridge.palette.muted; font.pixelSize: Math.round(14*bridge.fontScale) }
                }
                AnimatedLyric { Layout.columnSpan: page.availableWidth < 850 ? 2 : 1; Layout.fillWidth: true; Layout.preferredWidth: 300;Layout.maximumHeight:100;Layout.alignment:Qt.AlignVCenter;maximumLineCount:3;elide:Text.ElideRight;clip:true; lineKey: page.currentLine; text: page.currentLyric; textFormat: Text.RichText; visible: text.length>0 }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Label { Layout.fillWidth: true; text: bridge.translate("Ajustes de reprodução"); color: bridge.palette.text; font.weight: Font.DemiBold }
            ActionButton { objectName: "playbackAdjustmentsToggle"; text: bridge.translate(page.adjustmentsExpanded ? "Ocultar ajustes" : "Mostrar ajustes"); onClicked: page.adjustmentsExpanded = !page.adjustmentsExpanded }
        }
        GridLayout {
            Layout.fillWidth:true;columns:page.availableWidth>=1100?3:page.availableWidth>=700?2:1;columnSpacing:16;rowSpacing:16
            UnifiedEffectsCard {visible:page.adjustmentsExpanded;Layout.fillWidth:true;Layout.fillHeight:true;Layout.preferredWidth:330}
            Card {
                objectName:"playbackJukeboxCard";visible:page.adjustmentsExpanded
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
                        MouseArea {anchors.fill:parent;enabled:bridge.stateValue(bridge.stateRevision,"ready");onClicked:function(mouse){const dx=mouse.x-width/2,dy=mouse.y-height/2,r=Math.min(width,height)*.42;if(Math.abs(Math.sqrt(dx*dx+dy*dy)-r)<22)bridge.seek(Math.round(((Math.atan2(dy,dx)+Math.PI/2+2*Math.PI)%(2*Math.PI))/(2*Math.PI)*bridge.graph.count)%bridge.graph.count)}}
                    }
                    Label {text:bridge.translate("Variação")+" · "+Math.round(variation.value)+"%";color:bridge.palette.text}
                    OndaSlider {id:variation;Layout.fillWidth:true;value:bridge.playbackParams.variation;enabled:!bridge.playbackParams.normal;Accessible.name:bridge.translate("Variação");onMoved:if(!pressed)page.updateParams();onPressedChanged:if(!pressed)page.updateParams()}
                    Label {text:bridge.translate("Transição suave")+" · "+Math.round(smooth.value)+"%";color:bridge.palette.text}
                    OndaSlider {id:smooth;Layout.fillWidth:true;value:bridge.playbackParams.smooth;enabled:!bridge.playbackParams.normal;Accessible.name:bridge.translate("Transição suave");onMoved:if(!pressed)page.updateParams();onPressedChanged:if(!pressed)page.updateParams()}
                }
            }
            UnifiedQueue {Layout.fillWidth:true;Layout.fillHeight:true;Layout.preferredWidth:330;Layout.columnSpan:page.availableWidth>=700&&page.availableWidth<1100?2:1}
        }
        Item { height: 8 }
    }
    readonly property real volume: bridge.playbackParams.volume
    function updateParams() { bridge.setParams(variation.value,smooth.value,volume,bridge.playbackParams.normal) }
}
