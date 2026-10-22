import QtQuick
import QtQuick.Controls
import QtQuick.Window
ApplicationWindow {
    width: Math.min(1360,Screen.desktopAvailableWidth); height: Math.min(900,Screen.desktopAvailableHeight); minimumWidth: Math.min(920,Screen.desktopAvailableWidth); minimumHeight: Math.min(680,Screen.desktopAvailableHeight)
    visible: true; title: "ONDA"; color: bridge.palette.bg
    onClosing: function(close) { close.accepted=false; workspace.requestClose() }
    palette.window: bridge.palette.bg; palette.windowText: bridge.palette.text; palette.base: bridge.palette.input; palette.text: bridge.palette.text; palette.button: bridge.palette.surface; palette.buttonText: bridge.palette.text; palette.highlight: bridge.palette.accent; palette.highlightedText: bridge.palette.accent_text; palette.placeholderText: bridge.palette.muted
    DropArea { anchors.fill: parent; onDropped: function(drop) { workspace.receiveDrop({urls:drop.urls,text:drop.text || ""});drop.acceptProposedAction() } }
    Shell { anchors.fill: parent }
}
