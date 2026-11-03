import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Card {
    id:queuePanel
    clip:true
    property bool recent:false
    onRecentChanged:{stableTracks.selectedIds=[];stableTracks.anchorId="";if(bridge.animations&&visible)tabReveal.restart();else {tabReveal.stop();queueList.opacity=1;tabSlide.x=0}}
    ParallelAnimation {
        id:tabReveal
        NumberAnimation {target:queueList;property:"opacity";from:0.6;to:1;duration:200;easing.type:Easing.OutCubic}
        NumberAnimation {target:tabSlide;property:"x";from:queuePanel.recent?queueList.width:-queueList.width;to:0;duration:240;easing.type:Easing.OutCubic}
    }
    readonly property var rows:recent ? bridge.visibleRecentTracks : bridge.visibleUpcomingTracks
    StableQueueModel { id: stableTracks; rows: queuePanel.rows }
    function original(i){return rows[i].queueIndex}
    function move(i,target){bridge.moveQueued(original(i),original(target)-original(i))}
    objectName:"unifiedQueuePanel"
    color:bridge.palette.surface
    border.width:bridge.palette.flat_black?0:1
    implicitHeight:405
    Connections {
        target:bridge
        function onTracksAdded(identities){
            queuePanel.recent=false
            Qt.callLater(function(){
                var added={};identities.forEach(function(id){added[id]=true})
                for(var i=0;i<queuePanel.rows.length;++i)if(added[queuePanel.rows[i].id]){queueList.positionViewAtIndex(i,ListView.Contain);break}
            })
        }
    }
    ColumnLayout {
        anchors.fill:parent;anchors.margins:12;spacing:12
        RowLayout {
            Layout.fillWidth:true
            Label {Layout.fillWidth:true;text:bridge.translate("Fila de reprodução");color:bridge.palette.text;font.bold:true}
            PlaybackButton {glyph:"queue";Accessible.name:bridge.translate("Abrir fila");onClicked:workspace.setOption("jukeboxQueueOpen",true)}
        }
        QueueTabs {recent:queuePanel.recent;onSelected:function(value){queuePanel.recent=value}}
        Label {visible:!queuePanel.rows.length;text:bridge.translate("Adicione arquivos ou músicas dos resultados.");Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.muted}
        OndaListView {
            transform:Translate {id:tabSlide;objectName:"queueTabSlide"}
            id:queueList;property var activeDrag:null;objectName:"unifiedPlaybackQueueList"
            Layout.fillWidth:true;Layout.fillHeight:true;clip:true;model:stableTracks;spacing:6

            ScrollToTop { target: queueList; viewport: queueList }
            section.property:"group"
            section.criteria:ViewSection.FullString
            section.delegate:Item {
                required property string section
                width:queueList.contentAreaWidth;height:section&&!queuePanel.recent?40:0
                Label {anchors.left:parent.left;anchors.right:parent.right;y:12;text:bridge.translate(parent.section);font.bold:true;elide:Text.ElideRight;color:bridge.palette.text}
            }

            delegate:Item {
                id:queueTrack
                objectName:"unifiedQueueTrack"+index
                required property var modelData;required property int index
                width:ListView.view.contentAreaWidth;height:60
                z:drag.dragging || (selected && queueList.activeDrag && queueList.activeDrag.dragItem.selected) ? 20 : 0
                transform:Translate {y:drag.cardOffset;Behavior on y {enabled:queueList.activeDrag!==null&&!drag.dragging;NumberAnimation {duration:140;easing.type:Easing.OutCubic}}}
                activeFocusOnTab:true;Accessible.role:Accessible.ListItem;Accessible.name:modelData.title || ""
                Keys.onReturnPressed:bridge.playQueued(modelData.queueIndex)
                readonly property bool selected: (!queuePanel.recent && !modelData.current) && stableTracks.selected(modelData)
                Accessible.selected: selected
                Keys.onShortcutOverride: function(event) {
                    if ((!queuePanel.recent && !modelData.current) && stableTracks.handlesShortcut(event))
                        event.accepted = true
                }
                Keys.onPressed: function(event) {
                    if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && event.modifiers === Qt.ShiftModifier)) {
                        actions.popup()
                        event.accepted = true
                    } else if (!queuePanel.recent && !modelData.current) {
                        stableTracks.handleKey(event, index, queueList)
                    }
                }
                HoverHandler {id:rowHover}
                Rectangle {anchors.fill:parent;radius:5;color:queueTrack.selected ? bridge.palette.accent : bridge.palette.hover;opacity:queueTrack.selected ? 0.20 : 1;visible:queueTrack.selected||rowHover.hovered||drag.dragging}
                RowLayout {
                    anchors.fill:parent;anchors.margins:6;anchors.topMargin:6;anchors.rightMargin:44
                    QueueDragHandle {doubleClickEnabled:true;opacity:rowHover.hovered||dragging||activeFocus?1:0;Layout.preferredWidth:16;id:drag;selectedRows:queueTrack.selected ? stableTracks.selectedRows : [];objectName:"unifiedQueueDrag"+index;dragItem:queueTrack;listView:queueList;rowIndex:queueTrack.index;enabled:!queuePanel.recent && !modelData.current;itemCount:queuePanel.rows.length;onClickedWithModifiers:function(modifiers){{queueTrack.forceActiveFocus();stableTracks.select(queueTrack.index,modifiers)}};onDoubleTapped:bridge.playQueued(modelData.queueIndex);onMoved:function(target){stableTracks.moveSelection(queueTrack.index,target)}}
                    Rectangle {Layout.preferredWidth:44;Layout.preferredHeight:44;radius:4;color:bridge.palette.input
                        RoundedArtwork {anchors.fill:parent;source:(modelData.record || {}).cover_url || modelData.cover || "";fallbackSource:modelData.cover || "";sourceSize.width:192;sourceSize.height:192;fillMode:Image.PreserveAspectCrop;asynchronous:true}
                        PreparationProgress {anchors.left:parent.left;anchors.right:parent.right;anchors.bottom:parent.bottom;height:3;preparing:modelData.analysis==="preparing";progress:bridge.queuePreparation[modelData.id] || 0}
                    }
                    ColumnLayout {Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
                        Label {Layout.fillWidth:true;text:modelData.title || "";font.weight:Font.DemiBold;elide:Text.ElideRight;color:modelData.current?bridge.palette.accent:bridge.palette.text}
                        Label {Layout.fillWidth:true;text:modelData.artist || "";elide:Text.ElideRight;color:bridge.palette.muted}

                        Label {visible:modelData.analysis==="error";text:bridge.translate("Falha na preparação");color:bridge.palette.muted;font.pixelSize:11}
                    }
                }
                QueueIconButton {
                    anchors.right:parent.right;anchors.verticalCenter:parent.verticalCenter
                    glyph:"more";text:bridge.translate("Mais ações")
                    opacity:rowHover.hovered||activeFocus||queueTrack.selected?1:0
                    onClicked:actions.popup()
                }
                OndaMenu {id:actions
                    OndaMenuItem {text:bridge.translate("Reproduzir");onTriggered:bridge.playQueued(modelData.queueIndex)}
                    OndaMenuItem {text:bridge.translate("Mover para cima");enabled:!queuePanel.recent&&index>0;onTriggered:stableTracks.moveStep(index,-1)}
                    OndaMenuItem {text:bridge.translate("Mover para baixo");enabled:!queuePanel.recent&&index+1<queuePanel.rows.length;onTriggered:stableTracks.moveStep(index,1)}
                    OndaMenuItem {text:bridge.translate("Mover como próxima");enabled:!queuePanel.recent && !modelData.current;onTriggered:stableTracks.moveNext(index)}
                    OndaMenuItem {text:bridge.translate("Remover da fila");enabled:!queuePanel.recent&&!modelData.current;onTriggered:bridge.removeQueuedGroup(stableTracks.actionIndices(index))}
                    OndaMenuItem {visible:modelData.analysis==="error";text:bridge.translate("Tentar novamente");onTriggered:bridge.retryQueued(modelData.queueIndex)}
                }
                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.RightButton
                    onClicked: actions.popup()
                }
                TapHandler {acceptedButtons:Qt.LeftButton;enabled:queuePanel.recent;onDoubleTapped:bridge.playQueued(modelData.queueIndex)}
            }
        }
    }
}
