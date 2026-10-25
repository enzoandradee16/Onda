import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
Drawer {
    id: drawer
    property bool effects: true
    readonly property string openKey: effects ? "effectsQueueOpen" : "jukeboxQueueOpen"
    readonly property var tracks: effects ? workspace.values.effectsQueue : bridge.queuedTracks
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
        ListView {
            id: queueList
            objectName: "playbackQueueList"
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true; spacing: 10; model: drawer.tracks
            ScrollBar.vertical: ScrollBar {}
            delegate: RowLayout {
                required property var modelData
                required property int index
                readonly property var record: drawer.effects ? modelData.record : modelData
                readonly property bool current: drawer.effects ? index===workspace.values.effectsQueueIndex : !!modelData.current
                width: queueList.width; height: Math.max(110,trackInformation.implicitHeight+20)
                spacing: 8
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
                visible:!drawer.tracks.length;text:bridge.translate("Adicione arquivos ou músicas dos resultados.");color:bridge.palette.muted
            }
        }
    }
}
