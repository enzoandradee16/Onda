import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id: root
    property string value: bridge.accent
    readonly property bool custom: /^#[0-9a-fA-F]{6}$/.test(value)
    signal selected(string color)
    ChoiceBox {
        Layout.fillWidth: true
        model: bridge.accents
        currentIndex: root.custom ? -1 : model.indexOf(root.value)
        displayText: bridge.translate(root.custom ? "Cor personalizada" : root.value) + (root.custom ? " · " + root.value : "")
        onActivated: root.selected(model[index])
    }
    ActionButton { objectName: "customAccentButton"; text: bridge.translate("Cor personalizada"); onClicked: picker.open() }
    CustomAccentPopup {
        id: picker
        initialColor: root.custom ? root.value : bridge.accentHex
        onSelected: function(color) { root.selected(color) }
    }
}
