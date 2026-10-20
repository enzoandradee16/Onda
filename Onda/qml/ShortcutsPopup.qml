import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    objectName: "shortcutsPopup"
    parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(760,parent.width-60); height: Math.min(700,parent.height-60); padding: 24; modal: true; focus: true
    background: Card {}
    contentItem: ColumnLayout {
        RowLayout { Layout.fillWidth: true; Label { text: bridge.translate("Atalhos personalizáveis"); color: bridge.palette.text; font.pixelSize: Math.round(24*bridge.fontScale); Layout.fillWidth: true } ActionButton { text: bridge.translate("Pronto"); onClicked: popup.close() } }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
            ColumnLayout { width: parent.availableWidth; spacing: Math.round(12*bridge.spacing)
                Repeater { model: workspace.shortcutFields
                    RowLayout { required property var modelData; Layout.fillWidth: true
                        Label { text: modelData.label; Layout.fillWidth: true; color: bridge.palette.text; wrapMode: Text.Wrap }
                        OndaTextField { text: modelData.sequence; Layout.preferredWidth: 180; onEditingFinished: workspace.invoke("shortcut_set",{key:modelData.key,sequence:text}) }
                    }
                }
            }
        }
    }
}
