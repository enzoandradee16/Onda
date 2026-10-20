import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id: root
    required property var field
    property bool settings: false
    readonly property var current: settings ? workspace.preferences[field.key] : workspace.values[field.key]
    function save(value) { if (settings) workspace.setSetting(field.key,value); else workspace.setOption(field.key,value) }
    spacing: Math.round(6*bridge.spacing)
    Label { visible: root.field.kind !== "bool"; text: bridge.translate(root.field.label); color: bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
    OndaSwitch { visible: root.field.kind === "bool"; text: bridge.translate(root.field.label); checked: root.current === true; onToggled: root.save(checked); Layout.fillWidth: true }
    ComboBox { visible: root.field.kind === "select"; Layout.fillWidth: true; model: root.field.choices || []; currentIndex: Math.max(0,model.indexOf(root.current)); displayText: bridge.translate(currentText).replace(" (320 kbps)",""); onActivated: root.save(model[index]); delegate: ItemDelegate { width: parent.width; text: bridge.translate(modelData).replace(" (320 kbps)","") } }
    OndaTextField { visible: root.field.kind !== "bool" && root.field.kind !== "select"; Layout.fillWidth: true; text: root.current === undefined ? "" : String(root.current); echoMode: root.field.key === "spotify_client_secret" ? TextInput.Password : TextInput.Normal; onEditingFinished: root.save(text); selectByMouse: true; color: bridge.palette.text; background: Rectangle { radius: 8; color: bridge.palette.input; border.color: parent.activeFocus ? bridge.palette.accent : bridge.palette.line } }
    Label { visible: !!root.field.hint; text: bridge.translate(root.field.hint || ""); color: bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; font.pixelSize: Math.round(12*bridge.fontScale) }
}
