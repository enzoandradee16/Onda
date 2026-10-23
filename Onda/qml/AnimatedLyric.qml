import QtQuick
import QtQuick.Controls
Label {
    id: line
    color: bridge.palette.accent; font.pixelSize: Math.round(20*bridge.fontScale); wrapMode: Text.Wrap
    onTextChanged: {
        reveal.stop();opacity=1;scale=1;transformShift.y=0
        if(workspace.preferences.lyrics_animation !== "Desativada")reveal.start()
    }
    transform: Translate { id: transformShift }
    SequentialAnimation { id: reveal
        ParallelAnimation {
            NumberAnimation { target: line; property: "opacity"; to: 0.3; duration: 30 }
            NumberAnimation { target: line; property: "scale"; to: workspace.preferences.lyrics_animation === "Zoom" ? 0.96 : 1; duration: 30 }
            NumberAnimation { target: transformShift; property: "y"; to: workspace.preferences.lyrics_animation === "Deslizar" ? 10 : 0; duration: 30 }
        }
        ParallelAnimation {
            NumberAnimation { target: line; property: "opacity"; to: 1; duration: 180 }
            NumberAnimation { target: line; property: "scale"; to: 1; duration: 180 }
            NumberAnimation { target: transformShift; property: "y"; to: 0; duration: 180 }
        }
    }
}
