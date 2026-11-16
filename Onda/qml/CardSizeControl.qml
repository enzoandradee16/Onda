import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
RowLayout {
    id: control
    property bool compact: false
    property string settingKey: "queue_card_size"
    readonly property string selectedSize: workspace.preferences[settingKey] || "Grande"
    spacing: 8
    Label { visible: !control.compact; text: bridge.translate("Tamanho dos cards"); color: bridge.palette.muted }
    ChoiceBox {
        objectName: "cardSizeChoice"
        model: ["Muito pequeno","Pequeno","Médio","Grande"]
        currentIndex: Math.max(0,model.indexOf(control.selectedSize))
        implicitWidth: Math.round(150*bridge.fontScale)
        Accessible.name: bridge.translate("Tamanho dos cards")
        onActivated: workspace.setSetting(control.settingKey,currentText)
    }
}
