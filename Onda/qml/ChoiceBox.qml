import QtQuick
import QtQuick.Controls
ComboBox {
    id: control
    displayText: bridge.translate(currentText)
    background: Rectangle {
        radius: 14
        color: bridge.palette.input
        border.color: control.activeFocus ? bridge.palette.accent : bridge.palette.line
        implicitWidth: 140
        implicitHeight: 40
    }
    popup: Popup {
        y: control.height + 4
        width: control.width
        padding: 6
        implicitHeight: Math.min(contentItem.implicitHeight + topPadding + bottomPadding, 320)
        background: Rectangle { radius: 14; color: bridge.palette.surface; border.color: bridge.palette.line }
        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator {}
        }
    }
    delegate: ItemDelegate {
        id: option
        width: control.popup.availableWidth
        highlighted: control.highlightedIndex === index
        readonly property bool selected: control.currentIndex === index
        text: bridge.translate(String(control.textRole ? modelData[control.textRole] : modelData))
        contentItem: Label { text: option.text; font: option.font; color: option.highlighted || option.selected ? bridge.palette.accent_text : bridge.palette.text; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { radius: 9; color: option.highlighted || option.selected ? bridge.palette.accent : bridge.palette.surface }
    }
}
