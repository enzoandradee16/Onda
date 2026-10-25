import QtQuick
ActionButton {
    id: tab
    background: Rectangle {
        radius: 12
        color: tab.primary ? (tab.hovered ? bridge.palette.accent_hover : bridge.palette.accent) : (tab.hovered ? bridge.palette.hover : "transparent")
        border.width: tab.visualFocus ? 2 : 0
        border.color: tab.primary ? bridge.palette.accent_text : bridge.palette.accent
        Behavior on color { ColorAnimation { duration: bridge.animations ? 120 : 0 } }
    }
}
