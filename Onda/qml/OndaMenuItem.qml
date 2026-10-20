import QtQuick
import QtQuick.Controls
MenuItem {
    id: control
    contentItem: Label { text: control.text; font: control.font; color: control.highlighted ? bridge.palette.accent_text : bridge.palette.text; opacity: control.enabled ? 1 : 0.45; verticalAlignment: Text.AlignVCenter }
    background: Rectangle { radius: 4; color: control.highlighted ? bridge.palette.accent : bridge.palette.surface }
}
