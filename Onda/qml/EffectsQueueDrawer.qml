import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
Drawer {
    id: drawer
    property bool effects: true
    readonly property string openKey: effects ? "effectsQueueOpen" : "jukeboxQueueOpen"
    readonly property var tracks: effects ? workspace.values.effectsQueue : bridge.queuedTracks
    readonly property var results: (effects ? workspace.values.effectsQueueResults : workspace.values.jukeboxQueueResults) || []
    readonly property bool searching: ["playback_input","effects_collection","effects_load"].some(function(name){return workspace.activity.busy.indexOf(name)>=0})
    function search(){
        if(searching)["playback_input","effects_collection","effects_load"].forEach(function(name){workspace.invoke("cancel_task",{name:name})})
        else if(queueQuery.text.trim())workspace.invoke("playback_queue_search",{effects:drawer.effects,query:queueQuery.text})
    }
    objectName: effects ? "effectsQueueDrawer" : "jukeboxQueueDrawer"
    edge: Qt.RightEdge
    width: Math.min(560,parent.width*0.95)
    height: parent.height
    modal: true
    dim: true
    background: Rectangle {color: bridge.palette.surface}
    onClosed: workspace.setOption(openKey,false)
    Connections {
        target: workspace
        function onOptionsChanged() {
            if(workspace.values[drawer.openKey] && !drawer.opened)drawer.open()
            else if(!workspace.values[drawer.openKey] && drawer.opened)drawer.close()
        }
    }
    function play(index) {
        if(effects)workspace.invoke("effects_queue_play",{index:index})
        else bridge.playQueued(index)
    }
    function move(index,direction) {
        if(effects)workspace.invoke("effects_queue_move",{index:index,direction:direction})
        else bridge.moveQueued(index,direction)
    }
    function remove(index) {
        if(effects)workspace.invoke("effects_queue_remove",{index:index})
        else bridge.removeQueued(index)
    }
    FileDialog {
        id: queueFiles
        title: bridge.translate("Adicionar músicas à fila")
        fileMode: FileDialog.OpenFiles
        nameFilters: [bridge.translate("Áudio")+" (*.mp3 *.m4a *.flac *.wav *.ogg *.opus *.aac *.webm)",bridge.translate("Todos os arquivos")+" (*)"]
        onAccepted: bridge.enqueueFiles(selectedFiles)
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 16; spacing: 14
        RowLayout {
            ChoiceBox {model:["Desativada","Todas","Uma"];currentIndex:model.indexOf(drawer.effects ? workspace.values.effectsRepeat : bridge.queueRepeat);onActivated:drawer.effects ? workspace.setOption("effectsRepeat",currentText) : bridge.setQueueRepeat(currentText);Accessible.name:bridge.translate("Repetição")}
        }
        RowLayout {
            Layout.fillWidth: true
            Label {text: bridge.translate("Fila de reprodução");color: bridge.palette.text;Layout.fillWidth: true}
            ActionButton {
                objectName: "clearPlaybackQueue"
                text: bridge.translate("Limpar");enabled: drawer.tracks.length>0
                onClicked: drawer.effects ? workspace.invoke("effects_queue_clear",{}) : bridge.clearPlaybackQueue()
            }
            PlaybackButton {glyph:"close";Accessible.name:bridge.translate("Fechar fila");onClicked:drawer.close()}
        }
        ActionButton {
            objectName: "addPlaybackQueueFiles"
            text: bridge.translate("Adicionar à fila")
            enabled: !drawer.effects || workspace.activity.busy.indexOf("effects_queue_info")<0
            onClicked: drawer.effects ? workspace.invoke("pick",{kind:"effects_queue"}) : queueFiles.open()
        }
        RowLayout {Layout.fillWidth:true
            OndaTextField {id:queueQuery;objectName:"playbackQueueSearch";Layout.fillWidth:true;placeholderText:bridge.translate("Música, artista ou link de música, álbum ou playlist");onAccepted:drawer.search()}
            ActionButton {objectName:"playbackQueueSearchButton";text:bridge.translate(drawer.searching ? "Cancelar" : "Pesquisar");enabled:drawer.searching || !!queueQuery.text.trim();onClicked:drawer.search()}
        }
        ListView {Layout.fillWidth:true;Layout.preferredHeight:Math.min(240,contentHeight);visible:drawer.results.length>0;clip:true;spacing:8;model:drawer.results
            delegate:RowLayout {required property var modelData;required property int index;width:ListView.view.width;height:modelData.release_date ? 98 : 78
                Component.onCompleted:workspace.invoke("request_card_details",{model:drawer.effects ? "effectsQueueResults" : "jukeboxQueueResults",source:modelData.source_url || ""})
                RoundedArtwork {Layout.preferredWidth:48;Layout.preferredHeight:48;source:modelData.cover_url || "";asynchronous:true;fillMode:Image.PreserveAspectFit}
                ColumnLayout {Layout.fillWidth:true;Layout.minimumWidth:0;spacing:2
                    Label {Layout.fillWidth:true;text:modelData.title || "";elide:Text.ElideRight;color:bridge.palette.text}
                    Label {Layout.fillWidth:true;text:(modelData.artists || []).join(", ");elide:Text.ElideRight;color:bridge.palette.muted}
                    Label {Layout.fillWidth:true;text:modelData.album || "";elide:Text.ElideRight;color:bridge.palette.muted}
                    Label {Layout.fillWidth:true;elide:Text.ElideRight;visible:!!modelData.release_date;text:bridge.translate("Data de lançamento")+": "+workspace.releaseDateText(modelData.release_date || "");color:bridge.palette.muted}
                }
                PlaybackButton {glyph:"add";Accessible.name:bridge.translate("Adicionar à fila");enabled:!drawer.searching;onClicked:workspace.invoke("playback_queue_add",{effects:drawer.effects,index:index})}
            }
        }
        ListView {
            id: queueList
            objectName: "playbackQueueList"
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; spacing: 10; model: drawer.tracks
            ScrollBar.vertical: ScrollBar {}
            delegate: RowLayout {
                id:queueTrack
                required property var modelData
                required property int index
                readonly property var record: drawer.effects ? modelData.record : modelData
                readonly property bool current: drawer.effects ? index===workspace.values.effectsQueueIndex : !!modelData.current
                width: queueList.width; height: Math.max(110,trackInformation.implicitHeight+20)
                spacing: 8
                Menu {id:trackActions
                    OndaMenuItem {text:bridge.translate("Reproduzir");onTriggered:drawer.play(queueTrack.index)}
                    OndaMenuItem {text:bridge.translate("Mover para cima");enabled:queueTrack.index>0;onTriggered:drawer.move(queueTrack.index,-1)}
                    OndaMenuItem {text:bridge.translate("Mover para baixo");enabled:queueTrack.index+1<drawer.tracks.length;onTriggered:drawer.move(queueTrack.index,1)}
                    OndaMenuItem {text:bridge.translate("Remover da fila");onTriggered:drawer.remove(queueTrack.index)}
                }
                TapHandler {acceptedButtons:Qt.RightButton;onTapped:trackActions.popup()}
                Rectangle {
                    Layout.preferredWidth:48;Layout.preferredHeight:48;radius:8;color:bridge.palette.input
                    RoundedArtwork {id:artwork;anchors.fill:parent;source:drawer.effects ? modelData.cover_url || "" : modelData.cover || "";fillMode:Image.PreserveAspectFit;asynchronous:true;sourceSize.width:96;sourceSize.height:96}
                    Label {anchors.centerIn:parent;visible:artwork.status!==Image.Ready;text:"♪";color:bridge.palette.muted}
                }
                ColumnLayout {
                    id: trackInformation
                    Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 3
                    Label {text:record.title || "";Layout.fillWidth:true;elide:Text.ElideRight;color:current ? bridge.palette.accent : bridge.palette.text}
                    Label {text:drawer.effects ? (record.artists || []).join(", ") : modelData.artist || "";Layout.fillWidth:true;elide:Text.ElideRight;color:bridge.palette.muted}
                    Label {text:record.album || "";visible:!!text;Layout.fillWidth:true;elide:Text.ElideRight;color:bridge.palette.muted}
                    Label {text:workspace.clock(modelData.duration || 0);color:bridge.palette.muted}
                    Label {
                        visible:!drawer.effects && modelData.analysis!=="ready"
                        text:bridge.translate(({pending:"Aguardando análise",preparing:"Analisando ritmo e trechos…",error:"Erro na análise"})[modelData.analysis] || "")
                        Layout.fillWidth:true;elide:Text.ElideRight;color:bridge.palette.muted
                    }
                }
                PlaybackButton {
                    objectName:"playQueueTrack"
                    implicitWidth:32;glyph:"play"
                    Accessible.name:bridge.translate(!drawer.effects && modelData.analysis==="error" ? "Tentar novamente" : "Reproduzir")
                    ToolTip.visible:hovered;ToolTip.text:Accessible.name
                    onClicked:drawer.play(index)
                }
                PlaybackButton {implicitWidth:28;glyph:"up";Accessible.name:bridge.translate("Mover para cima");enabled:index>0;onClicked:drawer.move(index,-1)}
                PlaybackButton {implicitWidth:28;glyph:"down";Accessible.name:bridge.translate("Mover para baixo");enabled:index+1<drawer.tracks.length;onClicked:drawer.move(index,1)}
                PlaybackButton {implicitWidth:28;glyph:"close";Accessible.name:bridge.translate("Remover da fila");onClicked:drawer.remove(index)}
            }
            Label {
                anchors.centerIn:parent;width:parent.width;horizontalAlignment:Text.AlignHCenter;wrapMode:Text.Wrap
                visible:!drawer.tracks.length;text:bridge.translate("Adicione arquivos, músicas, álbuns ou playlists à fila.");color:bridge.palette.muted
            }
        }
    }
}
