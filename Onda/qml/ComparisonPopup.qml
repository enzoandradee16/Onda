import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: compare
    objectName: "comparisonPopup"
    parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(1000,parent.width-60); height: Math.min(650,parent.height-60); modal: true; focus: true; padding: 24
    property int left: 0
    property int right: 1
    background: Card {}
    Connections { target: workspace; function onComparisonRequested(index) { compare.left=index;compare.right=index === 0 ? 1 : 0;compare.open() } }
    contentItem: ColumnLayout { spacing: Math.round(18*bridge.spacing)
        Label { text: bridge.translate("Comparar resultados"); font.pixelSize: Math.round(24*bridge.fontScale); color: bridge.palette.text }
        RowLayout { Layout.fillWidth: true
            ChoiceBox { Layout.fillWidth: true; model: workspace.catalogChoices; textRole: "label"; currentIndex: compare.left; onActivated: compare.left=index }
            ChoiceBox { Layout.fillWidth: true; model: workspace.catalogChoices; textRole: "label"; currentIndex: compare.right; onActivated: compare.right=index }
        }
        ScrollView { Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth
            OndaTextArea { text: workspace.compareText(compare.left,compare.right); readOnly: true; selectByMouse: true; wrapMode: Text.Wrap; color: bridge.palette.text; font.pixelSize: Math.round(16*bridge.fontScale) }
        }
        ActionButton { primary: true; text: bridge.translate("Pronto"); Layout.alignment: Qt.AlignRight; onClicked: compare.close() }
    }
}
