import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Card {
    id:queuePanel
    property bool recent:false
    onRecentChanged:if(bridge.animations&&visible)tabReveal.restart();else {tabReveal.stop();queueList.opacity=1}
    NumberAnimation {id:tabReveal;target:queueList;property:"opacity";from:0.55;to:1;duration:180;easing.type:Easing.OutCubic}
    readonly property var rows:recent ? bridge.recentTracks : bridge.upcomingTracks
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
        ListView {
            id:queueList;property var activeDrag:null;objectName:"unifiedPlaybackQueueList"
            Layout.fillWidth:true;Layout.fillHeight:true;clip:true;model:queuePanel.rows;spacing:6
            section.property:"group"
            section.criteria:ViewSection.FullString
            section.delegate:Item {
                required property string section
                width:queueList.width;height:section&&!queuePanel.recent?40:0
                Label {anchors.left:parent.left;anchors.right:parent.right;y:12;text:bridge.translate(parent.section);font.bold:true;elide:Text.ElideRight;color:bridge.palette.text}
            }

            delegate:Item {
                id:queueTrack
                objectName:"unifiedQueueTrack"+index
                required property var modelData;required property int index
                width:ListView.view.width;height:60
                z:drag.dragging?20:0
                transform:Translate {y:drag.cardOffset;Behavior on y {enabled:queueList.activeDrag!==null&&!drag.dragging;NumberAnimation {duration:140;easing.type:Easing.OutCubic}}}
                activeFocusOnTab:true;Accessible.role:Accessible.ListItem;Accessible.name:modelData.title || ""
                Keys.onReturnPressed:bridge.playQueued(modelData.queueIndex)
                HoverHandler {id:rowHover}
                Rectangle {anchors.fill:parent;radius:5;color:bridge.palette.hover;visible:rowHover.hovered||drag.dragging}
                RowLayout {
                    anchors.fill:parent;anchors.margins:6;anchors.topMargin:6
                    QueueDragHandle {doubleClickEnabled:true;opacity:rowHover.hovered||dragging||activeFocus?1:0;Layout.preferredWidth:16;id:drag;objectName:"unifiedQueueDrag"+index;dragItem:queueTrack;listView:queueList;rowIndex:queueTrack.index;enabled:!queuePanel.recent;itemCount:queuePanel.rows.length;onDoubleTapped:bridge.playQueued(modelData.queueIndex);onMoved:function(target){queuePanel.move(queueTrack.index,target)}}
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
                OndaMenu {id:actions
                    OndaMenuItem {text:bridge.translate("Reproduzir");onTriggered:bridge.playQueued(modelData.queueIndex)}
                    OndaMenuItem {text:bridge.translate("Mover para cima");enabled:!queuePanel.recent&&index>0;onTriggered:queuePanel.move(index,index-1)}
                    OndaMenuItem {text:bridge.translate("Mover para baixo");enabled:!queuePanel.recent&&index+1<queuePanel.rows.length;onTriggered:queuePanel.move(index,index+1)}
                    OndaMenuItem {text:bridge.translate("Remover");onTriggered:bridge.removeQueued(modelData.queueIndex)}
                    OndaMenuItem {visible:modelData.analysis==="error";text:bridge.translate("Tentar novamente");onTriggered:bridge.retryQueued(modelData.queueIndex)}
                }
                TapHandler {acceptedButtons:Qt.RightButton;onTapped:actions.popup()}
                TapHandler {acceptedButtons:Qt.LeftButton;enabled:queuePanel.recent;onDoubleTapped:bridge.playQueued(modelData.queueIndex)}
            }
        }
    }
}
