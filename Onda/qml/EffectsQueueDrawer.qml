import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
Drawer {
    id: drawer
    property bool effects: true
    property bool recent:false
    onRecentChanged:if(bridge.animations&&visible)tabReveal.restart();else {tabReveal.stop();queueList.opacity=1}
    NumberAnimation {id:tabReveal;target:queueList;property:"opacity";from:0.55;to:1;duration:180;easing.type:Easing.OutCubic}
    property bool searchExpanded:false
    property real requestedWidth: workspace.preferences.playback_queue_width || 470
    readonly property real maximumPanelWidth: Math.min(900,parent.width*0.95)
    readonly property real minimumPanelWidth: Math.min(360,maximumPanelWidth)
    function saveWidth(){
        workspace.setSetting("playback_queue_width",Math.round(drawer.width))
        requestedWidth=Qt.binding(function(){return workspace.preferences.playback_queue_width || 470})
    }
    readonly property string openKey: effects ? "effectsQueueOpen" : "jukeboxQueueOpen"
    readonly property var tracks: effects ? workspace.values.effectsQueue : (recent ? bridge.recentTracks : bridge.upcomingTracks)
    readonly property var results: (effects ? workspace.values.effectsQueueResults : workspace.values.jukeboxQueueResults) || []
    readonly property bool searching: ["playback_input","effects_collection","effects_load"].some(function(name){return workspace.activity.busy.indexOf(name)>=0})
    function search(){
        if(searching)["playback_input","effects_collection","effects_load"].forEach(function(name){workspace.invoke("cancel_task",{name:name})})
        else if(queueQuery.text.trim())workspace.invoke("playback_queue_search",{effects:drawer.effects,query:queueQuery.text})
    }
    function closeSearch(){workspace.invoke("playback_queue_close_search",{});queueQuery.clear();searchExpanded=false}
    objectName: effects ? "effectsQueueDrawer" : "jukeboxQueueDrawer"
    edge: Qt.RightEdge
    width: Math.max(minimumPanelWidth,Math.min(requestedWidth,maximumPanelWidth))
    height: parent.height
    interactive: !resizeMouse.pressed
    modal: true
    dim: true
    background: Rectangle {radius:10;color:bridge.palette.surface;border.color:bridge.palette.line;border.width:bridge.palette.flat_black?0:1}
    MouseArea {
        id:resizeMouse;objectName:"playbackQueueResizeHandle"
        anchors.left:parent.left;anchors.top:parent.top;anchors.bottom:parent.bottom
        width:8;z:100;hoverEnabled:true;cursorShape:Qt.SplitHCursor
        preventStealing:true
        property real initialX
        property real initialWidth
        onPressed:function(mouse){initialX=mapToGlobal(mouse.x,mouse.y).x;initialWidth=drawer.width}
        onPositionChanged:function(mouse){
            if(pressed)drawer.requestedWidth=Math.max(drawer.minimumPanelWidth,Math.min(drawer.maximumPanelWidth,initialWidth+initialX-mapToGlobal(mouse.x,mouse.y).x))
        }
        onReleased:drawer.saveWidth()
        onCanceled:drawer.saveWidth()
        Rectangle {anchors.left:parent.left;anchors.verticalCenter:parent.verticalCenter;width:3;height:Math.min(80,parent.height);radius:2;color:bridge.palette.accent;visible:resizeMouse.containsMouse||resizeMouse.pressed}
    }
    onClosed: workspace.setOption(openKey,false)
    Connections {
        target:bridge
        function onTracksAdded(identities){
            if(drawer.effects)return
            drawer.recent=false
            Qt.callLater(function(){
                var added={};identities.forEach(function(id){added[id]=true})
                for(var i=0;i<drawer.tracks.length;++i)if(added[drawer.tracks[i].id]){queueList.positionViewAtIndex(i,ListView.Contain);break}
            })
        }
    }
    Connections {
        target: workspace
        function onOptionsChanged() {
            if(workspace.values[drawer.openKey] && !drawer.opened)drawer.open()
            else if(!workspace.values[drawer.openKey] && drawer.opened)drawer.close()
        }
    }
    function play(index) {
        if(effects)workspace.invoke("effects_queue_play",{index:index})
        else bridge.playQueued(tracks[index].queueIndex)
    }
    function move(index,direction) {
        if(effects)workspace.invoke("effects_queue_move",{index:index,direction:direction})
        else bridge.moveQueued(tracks[index].queueIndex,tracks[index+direction].queueIndex-tracks[index].queueIndex)
    }
    function remove(index) {
        if(effects)workspace.invoke("effects_queue_remove",{index:index})
        else bridge.removeQueued(tracks[index].queueIndex)
    }
    function retry(index) {
        if(effects)workspace.invoke("effects_queue_retry",{index:index})
        else bridge.retryQueued(tracks[index].queueIndex)
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
            Layout.fillWidth:true;spacing:4
            QueueTabs {objectName:"playbackQueueTabs";Layout.fillWidth:true;Layout.rightMargin:12;recent:drawer.recent;onSelected:function(value){drawer.recent=value}}
            QueueIconButton {objectName:"togglePlaybackQueueSearch";glyph:"catalog";text:bridge.translate("Pesquisar");onClicked:{drawer.searchExpanded=!drawer.searchExpanded;if(drawer.searchExpanded)queueQuery.forceActiveFocus();else drawer.closeSearch()}}
            QueueIconButton {glyph:"more";text:bridge.translate("Mais ações");onClicked:queueActions.popup()}
            QueueIconButton {glyph:"close";text:bridge.translate("Fechar fila");onClicked:drawer.close()}
            OndaMenu {id:queueActions
                OndaMenuItem {objectName:"addPlaybackQueueFiles";text:bridge.translate("Adicionar à fila");onTriggered:queueFiles.open()}
                OndaMenuItem {text:bridge.translate("Limpar adições");onTriggered:bridge.clearManualQueue()}
                OndaMenuItem {objectName:"clearPlaybackQueue";text:bridge.translate("Limpar fila");onTriggered:bridge.clearPlaybackQueue()}
            }
        }
        RowLayout {Layout.fillWidth:true;visible:drawer.searchExpanded
            OndaTextField {id:queueQuery;objectName:"playbackQueueSearch";Layout.fillWidth:true;placeholderText:bridge.translate("Música, artista ou link de música, álbum ou playlist");onAccepted:drawer.search();Keys.onEscapePressed:drawer.closeSearch()}
            QueueIconButton {objectName:"playbackQueueSearchButton";glyph:drawer.searching?"close":"catalog";text:bridge.translate(drawer.searching?"Cancelar":"Pesquisar");enabled:drawer.searching||!!queueQuery.text.trim();onClicked:drawer.search()}
            QueueIconButton {objectName:"closePlaybackQueueSearch";glyph:"close";text:bridge.translate("Fechar pesquisa");onClicked:drawer.closeSearch()}
        }
        ListView {Layout.fillWidth:true;Layout.preferredHeight:Math.min(240,contentHeight);visible:drawer.results.length>0;clip:true;spacing:8;model:drawer.results
            delegate:RowLayout {required property var modelData;required property int index;width:ListView.view.width;height:modelData.release_date ? 98 : 78
                Component.onCompleted:workspace.invoke("request_card_details",{model:drawer.effects ? "effectsQueueResults" : "jukeboxQueueResults",source:modelData.source_url || ""})
                RoundedArtwork {Layout.preferredWidth:48;Layout.preferredHeight:48;source:modelData.cover_url || "";asynchronous:true;fillMode:Image.PreserveAspectFit}
                ColumnLayout {Layout.fillWidth:true;Layout.minimumWidth:0;spacing:2
                    Label {Layout.fillWidth:true;text:modelData.title || "";font.weight:Font.DemiBold;elide:Text.ElideRight;color:bridge.palette.text}
                    Label {Layout.fillWidth:true;text:(modelData.artists || []).join(", ");elide:Text.ElideRight;color:bridge.palette.muted}
                    Label {Layout.fillWidth:true;text:workspace.albumReleaseText(modelData);elide:Text.ElideRight;color:bridge.palette.muted}
                }

                QueueIconButton {objectName:"addQueueSearchResult"+index;glyph:"add";text:bridge.translate("Adicionar à fila");enabled:!drawer.searching;onClicked:workspace.invoke("playback_queue_add",{effects:drawer.effects,index:index,source:modelData.source_url || ""})}
            }
        }
        ListView {
            id:queueList
            property var activeDrag:null
            objectName:"playbackQueueList"
            Layout.fillWidth:true;Layout.fillHeight:true;clip:true;spacing:4;model:drawer.tracks
            ScrollBar.vertical:ScrollBar {policy:ScrollBar.AsNeeded}
            section.property:"group"
            section.criteria:ViewSection.FullString
            section.delegate:Item {
                required property string section
                objectName:"playbackQueueSection"+section
                width:queueList.width;height:section&&!drawer.recent?44:0
                Label {anchors.left:parent.left;anchors.right:parent.right;y:16;text:bridge.translate(parent.section);font.bold:true;elide:Text.ElideRight;color:bridge.palette.text}
            }

            delegate:Item {
                id:queueTrack
                objectName:"playbackQueueTrack"+index
                required property var modelData
                required property int index
                readonly property var record:drawer.effects?modelData.record:modelData
                readonly property bool current:drawer.effects?index===workspace.values.effectsQueueIndex:!!modelData.current
                readonly property bool failed:!!modelData.error||modelData.analysis==="error"
                readonly property bool section:!!modelData.section&&!drawer.recent
                width:queueList.width;height:60
                z:playbackDrag.dragging?20:0
                transform:Translate {y:playbackDrag.cardOffset;Behavior on y {enabled:queueList.activeDrag!==null&&!playbackDrag.dragging;NumberAnimation {duration:140;easing.type:Easing.OutCubic}}}
                activeFocusOnTab:true;Accessible.role:Accessible.ListItem;Accessible.name:record.title||""
                Keys.onReturnPressed:failed?drawer.retry(index):drawer.play(index)
                HoverHandler {id:rowHover}
                Rectangle {anchors.fill:parent;radius:5;color:bridge.palette.hover;visible:rowHover.hovered||playbackDrag.dragging||queueTrack.activeFocus}
                QueueDragHandle {doubleClickEnabled:true;showIndicator:false;id:playbackDrag;objectName:"playbackQueueDrag";anchors.right:parent.right;anchors.bottom:parent.bottom;width:16;height:60;opacity:rowHover.hovered||dragging||activeFocus?1:0;enabled:!drawer.recent;dragItem:queueTrack;listView:queueList;rowIndex:queueTrack.index;itemCount:drawer.tracks.length;onMoved:function(target){drawer.move(queueTrack.index,target-queueTrack.index)};onDoubleTapped:queueTrack.failed?drawer.retry(queueTrack.index):drawer.play(queueTrack.index)}
                RowLayout {
                    anchors.fill:parent;anchors.rightMargin:16;spacing:10
                    Rectangle {Layout.preferredWidth:44;Layout.preferredHeight:44;radius:4;color:bridge.palette.input
                        RoundedArtwork {id:artwork;anchors.fill:parent;source:queueTrack.record.cover_url || (drawer.effects?modelData.cover_url||"":modelData.cover||"");fallbackSource:drawer.effects?modelData.cover_url||"":modelData.cover||"";fillMode:Image.PreserveAspectCrop;asynchronous:true;sourceSize.width:192;sourceSize.height:192}
                        Label {anchors.centerIn:parent;visible:artwork.status!==Image.Ready;text:"♪";color:bridge.palette.muted}
                        PreparationProgress {anchors.left:parent.left;anchors.right:parent.right;anchors.bottom:parent.bottom;height:3;preparing:modelData.analysis==="preparing";progress:bridge.queuePreparation[modelData.id] || 0}
                    }
                    ColumnLayout {Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
                        Label {Layout.fillWidth:true;elide:Text.ElideRight;text:record.title||"";font.weight:Font.DemiBold;color:queueTrack.current?bridge.palette.accent:bridge.palette.text}
                        Label {Layout.fillWidth:true;elide:Text.ElideRight;text:drawer.effects?(record.artists||[]).join(", "):modelData.artist||"";color:bridge.palette.muted}
                        Label {visible:queueTrack.failed;Layout.fillWidth:true;elide:Text.ElideRight;text:bridge.translate("Falha na preparação");color:bridge.palette.muted;font.pixelSize:11}
                    }
                    QueueIconButton {glyph:"more";text:bridge.translate("Mais ações");opacity:rowHover.hovered||activeFocus?1:0;onClicked:trackActions.popup()}
                }
                OndaMenu {id:trackActions
                    OndaMenuItem {text:bridge.translate(queueTrack.failed?"Tentar novamente":"Reproduzir");onTriggered:queueTrack.failed?drawer.retry(index):drawer.play(index)}
                    OndaMenuItem {text:bridge.translate("Mover para cima");enabled:!drawer.recent&&index>0;onTriggered:drawer.move(index,-1)}
                    OndaMenuItem {text:bridge.translate("Mover para baixo");enabled:!drawer.recent&&index+1<drawer.tracks.length;onTriggered:drawer.move(index,1)}
                    OndaMenuItem {text:bridge.translate("Remover da fila");onTriggered:drawer.remove(index)}
                }
                TapHandler {acceptedButtons:Qt.RightButton;onTapped:trackActions.popup()}
                TapHandler {acceptedButtons:Qt.LeftButton;enabled:drawer.recent;onDoubleTapped:queueTrack.failed?drawer.retry(index):drawer.play(index)}
                ToolTip.visible:rowHover.hovered&&queueTrack.failed
                ToolTip.text:bridge.translateError(modelData.error||"")
            }
            Label {anchors.centerIn:parent;width:parent.width;horizontalAlignment:Text.AlignHCenter;wrapMode:Text.Wrap;visible:!drawer.tracks.length;text:bridge.translate("Adicione arquivos, músicas, álbuns ou playlists à fila.");color:bridge.palette.muted}
        }
    }
}
