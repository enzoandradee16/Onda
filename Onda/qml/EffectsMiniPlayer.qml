import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ApplicationWindow {
    id: mini
    objectName: "effectsFloatingPlayer"
    LyricsWindow {id: lyrics}
    property var mainWindow
    width: 460; height: 220; minimumWidth: 380; minimumHeight: 220
    title: bridge.translate("Efeitos")+" · ONDA"
    color: bridge.palette.bg
    flags: Qt.Window | Qt.WindowStaysOnTopHint
    onClosing: function(event) {event.accepted=false;hide();if(mainWindow){mainWindow.showNormal();mainWindow.raise();mainWindow.requestActivate()}}
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 14; spacing: 8
        RowLayout {
            Layout.fillWidth: true
            RoundedArtwork {source: workspace.values.effectsCover || "";Layout.preferredWidth:48;Layout.preferredHeight:48;fillMode:Image.PreserveAspectCrop}
            ColumnLayout {Layout.fillWidth:true;Layout.minimumWidth:0
                Label {Layout.fillWidth:true;text:workspace.values.effectsRecord.title || "";elide:Text.ElideRight;color:bridge.palette.text}
                Label {Layout.fillWidth:true;text:(workspace.values.effectsRecord.artists || []).join(", ");elide:Text.ElideRight;color:bridge.palette.muted}
            }
            PlaybackButton {glyph:"mini";Accessible.name:bridge.translate("Restaurar janela");onClicked:mini.close()}
        }
        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            MicrophoneButton {onClicked:lyrics.open()}
            PlaybackButton {glyph:"previous";Accessible.name:bridge.translate("Retroceder");onClicked:workspace.invoke("effects_previous",{})}
            PlaybackButton {primary:true;glyph:workspace.values.previewActive && workspace.values.previewKind==="effects" ? "pause" : "play";Accessible.name:bridge.translate(glyph==="pause" ? "Pausar" : "Reproduzir");enabled:workspace.values.duration>0;onClicked:workspace.invoke("effects_play_pause",{})}
            PlaybackButton {glyph:"next";Accessible.name:bridge.translate("Avançar");enabled:workspace.values.effectsQueueIndex+1<workspace.values.effectsQueue.length;onClicked:workspace.invoke("effects_next",{})}
            PlaybackButton {glyph:"queue";Accessible.name:bridge.translate("Fila");onClicked:{mini.close();workspace.setOption("effectsQueueOpen",true)}}
        }
        RowLayout {Layout.fillWidth:true
            Label {text:workspace.clock(workspace.values.position);color:bridge.palette.muted}
            OndaSlider {Layout.fillWidth:true;from:0;to:Math.max(1,workspace.values.duration);value:workspace.values.position;Accessible.name:bridge.translate("Posição na música");onMoved:workspace.setOption("position",value)}
            Label {text:workspace.clock(workspace.values.duration);color:bridge.palette.muted}
        }
        RowLayout {Layout.fillWidth:true
            LineIcon {glyph:"volume";Layout.preferredWidth:24;Layout.preferredHeight:24}
            OndaSlider {Layout.fillWidth:true;value:workspace.values.effectsVolume;Accessible.name:bridge.translate("Volume");onMoved:workspace.setOption("effectsVolume",value)}
        }
    }
}
