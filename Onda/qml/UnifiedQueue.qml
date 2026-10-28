import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Card {
    implicitHeight:405
    ColumnLayout {
        anchors.fill:parent;anchors.margins:12;spacing:12
        RowLayout {
            Layout.fillWidth:true
            Label {Layout.fillWidth:true;text:bridge.translate("Fila de reprodução");color:bridge.palette.text;font.bold:true}
            PlaybackButton {glyph:"queue";Accessible.name:bridge.translate("Abrir fila");onClicked:workspace.setOption("jukeboxQueueOpen",true)}
        }
        Label {visible:!bridge.queuedTracks.length;text:bridge.translate("Adicione arquivos ou músicas dos resultados.");Layout.fillWidth:true;wrapMode:Text.Wrap;color:bridge.palette.muted}
        ListView {
            id:queueList;property var activeDrag:null;objectName:"unifiedPlaybackQueueList"
            Layout.fillWidth:true;Layout.fillHeight:true;clip:true;model:bridge.queuedTracks;spacing:6
            delegate:Item {
                id:queueTrack
                objectName:"unifiedQueueTrack"+index
                required property var modelData;required property int index
                width:ListView.view.width;height:modelData.analysis==="error"?96:76
                z:drag.dragging?20:0
                transform:Translate {y:drag.cardOffset;Behavior on y {enabled:queueList.activeDrag!==null&&!drag.dragging;NumberAnimation {duration:140;easing.type:Easing.OutCubic}}}
                activeFocusOnTab:true;Accessible.role:Accessible.ListItem;Accessible.name:modelData.title || ""
                Keys.onReturnPressed:bridge.playQueued(index)
                Rectangle {anchors.fill:parent;radius:8;color:drag.dragging?bridge.palette.surface:modelData.current?bridge.palette.input:"transparent"}
                RowLayout {
                    anchors.fill:parent;anchors.margins:6
                    QueueDragHandle {id:drag;objectName:"unifiedQueueDrag"+index;dragItem:queueTrack;listView:queueList;rowIndex:queueTrack.index;itemCount:bridge.queuedTracks.length;onTapped:bridge.playQueued(queueTrack.index);onMoved:function(target){bridge.moveQueued(queueTrack.index,target-queueTrack.index)}}
                    Rectangle {Layout.preferredWidth:48;Layout.preferredHeight:48;radius:6;color:bridge.palette.input
                        RoundedArtwork {anchors.fill:parent;source:modelData.cover || "";fillMode:Image.PreserveAspectCrop;asynchronous:true}
                    }
                    ColumnLayout {Layout.fillWidth:true;Layout.minimumWidth:0;spacing:4
                        Label {Layout.fillWidth:true;text:modelData.title || "";elide:Text.ElideRight;color:modelData.current?bridge.palette.accent:bridge.palette.text}
                        Label {Layout.fillWidth:true;text:modelData.artist || "";elide:Text.ElideRight;color:bridge.palette.muted}
                        Label {text:workspace.clock(modelData.duration || 0);color:bridge.palette.muted;font.pixelSize:11}
                        Label {visible:modelData.analysis==="error";text:bridge.translate("Falha na preparação");color:bridge.palette.muted;font.pixelSize:11}
                    }
                }
                Menu {id:actions
                    OndaMenuItem {text:bridge.translate("Reproduzir");onTriggered:bridge.playQueued(index)}
                    OndaMenuItem {text:bridge.translate("Mover para cima");enabled:index>0;onTriggered:bridge.moveQueued(index,-1)}
                    OndaMenuItem {text:bridge.translate("Mover para baixo");enabled:index+1<bridge.queuedTracks.length;onTriggered:bridge.moveQueued(index,1)}
                    OndaMenuItem {text:bridge.translate("Remover");onTriggered:bridge.removeQueued(index)}
                    OndaMenuItem {visible:modelData.analysis==="error";text:bridge.translate("Tentar novamente");onTriggered:bridge.retryQueued(index)}
                }
                TapHandler {acceptedButtons:Qt.RightButton;onTapped:actions.popup()}
            }
        }
    }
}
