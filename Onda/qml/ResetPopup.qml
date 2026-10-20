import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: reset
    objectName: "resetPopup"
    parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(700,parent.width-60); height: Math.min(680,parent.height-60); modal: true; focus: true; padding: 24
    property var selected: []
    background: Card {}
    contentItem: ColumnLayout { spacing: Math.round(14*bridge.spacing)
        Label { text: bridge.translate("Escolher quais configurações restaurar…"); font.pixelSize: Math.round(21*bridge.fontScale); color: bridge.palette.text; Layout.fillWidth: true; wrapMode: Text.Wrap }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth; clip: true
            ColumnLayout { width: parent.availableWidth; spacing: Math.round(9*bridge.spacing)
                Repeater { model: workspace.settingsFields
                    CheckBox { required property var modelData; Layout.fillWidth: true; text: bridge.translate(modelData.label); checked: reset.selected.indexOf(modelData.key) >= 0
                        onToggled: { var values=reset.selected.slice();if (checked) values.push(modelData.key);else values.splice(values.indexOf(modelData.key),1);reset.selected=values }
                    }
                }
            }
        }
        RowLayout { ActionButton { text: bridge.translate("Cancelar");onClicked: reset.close() } ActionButton { primary: true;text: bridge.translate("Restaurar selecionados");enabled: reset.selected.length > 0;onClicked: { workspace.invoke("reset_selected",{keys:reset.selected});reset.close() } } }
    }
}
