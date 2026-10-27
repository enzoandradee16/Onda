import QtQuick
import QtQuick.Controls
MenuItem {
    id: control
    implicitHeight: visible ? Math.max(implicitBackgroundHeight + topInset + bottomInset, implicitContentHeight + topPadding + bottomPadding, implicitIndicatorHeight + topPadding + bottomPadding) : 0
    height: visible ? implicitHeight : 0
    contentItem: Label { text: control.text; font: control.font; color: control.highlighted ? bridge.palette.accent_text : bridge.palette.text; opacity: control.enabled ? 1 : 0.45; verticalAlignment: Text.AlignVCenter }
    background: Rectangle { radius: 4; color: control.highlighted ? bridge.palette.accent : bridge.palette.surface }
}
