import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
RowLayout {
    id: root
    property string value: bridge.accent
    readonly property bool custom: /^#[0-9a-fA-F]{6}$/.test(value)
    signal selected(string color)
    ChoiceBox {
        Layout.fillWidth: true
        model: bridge.accents
        currentIndex: model.indexOf(root.custom ? "Cor personalizada" : root.value)
        displayText: bridge.translate(root.custom ? "Cor personalizada" : root.value) + (root.custom ? " · " + root.value : "")
        onActivated: {
            if (model[index] === "Cor personalizada") picker.open()
            else root.selected(model[index])
        }
    }
    ActionButton { visible: root.custom; text: bridge.translate("Editar"); onClicked: picker.open() }
    CustomAccentPopup {
        id: picker
        initialColor: root.custom ? root.value : bridge.accentHex
        onSelected: function(color) { root.selected(color) }
    }
}
