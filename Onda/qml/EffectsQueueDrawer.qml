import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Drawer {
 objectName: "effectsQueueDrawer"
 id: drawer; edge: Qt.RightEdge; width: Math.min(560,parent.width*0.95); height: parent.height; modal: true; dim: true
 background: Rectangle {color: bridge.palette.surface}
 onClosed: workspace.setOption("effectsQueueOpen",false)
 Connections {target: workspace; function onOptionsChanged(){if(workspace.values.effectsQueueOpen && !drawer.opened)drawer.open();else if(!workspace.values.effectsQueueOpen && drawer.opened)drawer.close()}}
                ColumnLayout {id: effectsQueueBody; anchors.fill: parent; anchors.margins: 16; spacing: 10
                    RowLayout {Layout.fillWidth: true; Label {text: bridge.translate("Fila de reprodução");color: bridge.palette.text;Layout.fillWidth: true} ActionButton {text: bridge.translate("Limpar");onClicked: workspace.invoke("effects_queue_clear",{})} PlaybackButton {glyph:"close";Accessible.name:bridge.translate("Fechar fila");onClicked:drawer.close()}}
                    ListView {id: effectsQueueList; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 10; model: workspace.values.effectsQueue; ScrollBar.vertical: ScrollBar {}
                        delegate: RowLayout {required property var modelData;required property int index; width: effectsQueueList.width; height: 132
                            Rectangle {Layout.preferredWidth:48;Layout.preferredHeight:48;radius:8;color:bridge.palette.input
                                RoundedArtwork {id: artwork;anchors.fill:parent;source:modelData.cover_url || "";fillMode:Image.PreserveAspectFit}
                                Label {anchors.centerIn:parent;visible:artwork.status!==Image.Ready;text:"♪";color:bridge.palette.muted}
                            }
                            ColumnLayout {Layout.fillWidth: true;Layout.minimumWidth: 0
                                Label {text: modelData.record.title;Layout.fillWidth: true;elide: Text.ElideRight;color: index===workspace.values.effectsQueueIndex ? bridge.palette.accent : bridge.palette.text}
                                Label {text: (modelData.record.artists || []).join(", ");Layout.fillWidth: true;elide: Text.ElideRight;color: bridge.palette.muted}
                                Label {text: workspace.clock(modelData.duration);color: bridge.palette.muted}
                            }
                            ActionButton {text: "▶";onClicked: workspace.invoke("effects_queue_play",{index:index})}
                            PlaybackButton {implicitWidth:28;glyph:"up";Accessible.name:bridge.translate("Mover para cima");enabled:index>0;onClicked:workspace.invoke("effects_queue_move",{index:index,direction:-1})}
                            PlaybackButton {implicitWidth:28;glyph:"down";Accessible.name:bridge.translate("Mover para baixo");enabled:index+1<workspace.values.effectsQueue.length;onClicked:workspace.invoke("effects_queue_move",{index:index,direction:1})}
                            PlaybackButton {implicitWidth:28;glyph:"close";Accessible.name:bridge.translate("Remover da fila");onClicked:workspace.invoke("effects_queue_remove",{index:index})}
                        }
                        Label {anchors.centerIn: parent;visible: !workspace.values.effectsQueue.length;text:bridge.translate("Adicione arquivos ou músicas dos resultados.");color:bridge.palette.muted}
                    }
                }

}
