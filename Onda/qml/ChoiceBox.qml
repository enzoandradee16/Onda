import QtQuick
import QtQuick.Controls
ComboBox {
    id: control
    displayText: bridge.translate(currentText)
    delegate: ItemDelegate {
        id: option
        width: control.width
        highlighted: control.highlightedIndex === index
        readonly property bool selected: control.currentIndex === index
        text: bridge.translate(modelData)
        contentItem: Label { text: option.text; font: option.font; color: option.highlighted || option.selected ? bridge.palette.accent_text : bridge.palette.text; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { color: option.highlighted || option.selected ? bridge.palette.accent : bridge.palette.surface }
    }
}
