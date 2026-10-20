import QtQuick
import QtQuick.Controls
ApplicationWindow {
    width: 1360; height: 900; minimumWidth: 920; minimumHeight: 680
    visible: true; title: "ONDA"; color: bridge.palette.bg
    onClosing: function(close) { close.accepted=false; workspace.requestClose() }
    palette.window: bridge.palette.bg; palette.windowText: bridge.palette.text; palette.base: bridge.palette.input; palette.text: bridge.palette.text; palette.button: bridge.palette.surface; palette.buttonText: bridge.palette.text; palette.highlight: bridge.palette.accent; palette.highlightedText: bridge.palette.accent_text; palette.placeholderText: bridge.palette.muted
    DropArea { anchors.fill: parent; onDropped: function(drop) { workspace.receiveDrop({urls:drop.urls,text:drop.text || ""});drop.acceptProposedAction() } }
    Shell { anchors.fill: parent }
}
