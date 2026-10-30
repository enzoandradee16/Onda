import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    objectName: "customAccentPopup"
    parent: Overlay.overlay
    anchors.centerIn: parent
    width: Math.min(420, parent.width - 32)
    padding: 20
    modal: true
    focus: true
    property string initialColor: "#79E2C4"
    property real hue: 0
    property real saturation: 1
    property real brightness: 1
    readonly property var preview: bridge.previewAccent(hex.text)
    signal selected(string color)
    function readHex(value) {
        var color = bridge.previewAccent(value)
        if (color.valid) {
            hue = color.hue
            saturation = color.saturation
            brightness = color.value
        }
    }
    function writeHex() { hex.text = Qt.hsva(hue / 360, saturation, brightness, 1).toString().toUpperCase() }
    onOpened: { hex.text = initialColor; readHex(initialColor) }
    background: Card {}
    contentItem: ColumnLayout {
        spacing: 12
        Label { text: bridge.translate("Cor personalizada"); color: bridge.palette.text; font.pixelSize: 22; Layout.fillWidth: true }
        Rectangle {
            id: plane
            Layout.fillWidth: true; Layout.preferredHeight: 160
            color: Qt.hsva(popup.hue / 360, 1, 1, 1)
            clip: true
            Accessible.name: bridge.translate("Saturação e brilho")
            Rectangle { anchors.fill: parent; gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0; color: "white" } GradientStop { position: 1; color: "transparent" } } }
            Rectangle { anchors.fill: parent; gradient: Gradient { GradientStop { position: 0; color: "transparent" } GradientStop { position: 1; color: "black" } } }
            Rectangle { x: popup.saturation * plane.width - 7; y: (1-popup.brightness)*plane.height-7; width: 14; height: 14; radius: 7; color: "transparent"; border.width: 2; border.color: "white"; Rectangle { anchors.fill: parent; anchors.margins: 2; radius: 5; color: "transparent"; border.color: "black" } }
            MouseArea {
                anchors.fill: parent
                preventStealing: true
                function pick(mouse) { popup.saturation=Math.max(0,Math.min(1,mouse.x/width));popup.brightness=1-Math.max(0,Math.min(1,mouse.y/height));popup.writeHex() }
                onPressed: function(mouse) { pick(mouse) }
                onPositionChanged: function(mouse) { if (pressed) pick(mouse) }
            }
        }
        Label { text: bridge.translate("Matiz"); color: bridge.palette.muted }
        Slider {
            Layout.fillWidth: true; from: 0; to: 360; value: popup.hue
            Accessible.name: bridge.translate("Matiz")
            onMoved: {popup.hue=value;popup.writeHex()}
            background: Rectangle {
                x: parent.leftPadding; y: parent.topPadding+(parent.availableHeight-height)/2; width: parent.availableWidth; height: 8; radius: 4
                gradient: Gradient { orientation: Gradient.Horizontal
                    GradientStop {position:0;color:"red"} GradientStop {position:1/6;color:"yellow"} GradientStop {position:2/6;color:"lime"} GradientStop {position:.5;color:"cyan"} GradientStop {position:4/6;color:"blue"} GradientStop {position:5/6;color:"magenta"} GradientStop {position:1;color:"red"}
                }
            }
        }
        Label { text: bridge.translate("Hexadecimal"); color: bridge.palette.muted }
        OndaTextField { id: hex; objectName: "customAccentHex"; Layout.fillWidth: true; placeholderText: "#RRGGBB"; maximumLength: 7; Accessible.name: bridge.translate("Hexadecimal"); onTextEdited: popup.readHex(text) }
        Label { visible: !popup.preview.valid; text: bridge.translate("Use o formato #RRGGBB."); color: bridge.palette.error; Layout.fillWidth: true }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 76; radius: 12
            color: popup.preview.valid ? popup.preview.bg : bridge.palette.bg
            border.color: bridge.palette.line
            RowLayout { anchors.fill: parent; anchors.margins: 12
                Label { Layout.fillWidth: true; text: bridge.translate("Prévia"); color: popup.preview.valid ? popup.preview.text : bridge.palette.text }
                Rectangle { Layout.preferredWidth: Math.max(140,exampleText.implicitWidth+24); Layout.preferredHeight: 40; radius: 9; color: popup.preview.valid ? popup.preview.accent : bridge.palette.accent
                    Label { id: exampleText; anchors.centerIn: parent; text: bridge.translate("Texto de exemplo"); color: popup.preview.valid ? popup.preview.accent_text : bridge.palette.accent_text }
                }
            }
        }
        Label { text: bridge.translate("A tonalidade pode ser ajustada para manter o contraste."); color: bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
        RowLayout { Layout.alignment: Qt.AlignRight
            ActionButton { text: bridge.translate("Cancelar"); onClicked: popup.close() }
            ActionButton { objectName: "applyCustomAccent"; primary: true; text: bridge.translate("Aplicar cor"); enabled: popup.preview.valid; onClicked: { popup.selected(popup.preview.hex);popup.close() } }
        }
    }
}
