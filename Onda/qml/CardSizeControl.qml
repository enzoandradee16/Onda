import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
RowLayout {
    id: control
    property string settingKey: "queue_card_size"
    readonly property string selectedSize: workspace.preferences[settingKey] || "Grande"
    spacing: 8
    Label { text: bridge.translate("Tamanho dos cards"); color: bridge.palette.muted }
    ChoiceBox {
        objectName: "cardSizeChoice"
        model: ["Pequeno","Médio","Grande"]
        currentIndex: Math.max(0,model.indexOf(control.selectedSize))
        implicitWidth: Math.round(110*bridge.fontScale)
        Accessible.name: bridge.translate("Tamanho dos cards")
        onActivated: workspace.setSetting(control.settingKey,currentText)
    }
}
