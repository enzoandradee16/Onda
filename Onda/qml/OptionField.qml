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
    Label { visible: !!root.field.section; text: bridge.translate(root.field.section || ""); color: bridge.palette.text; font.pixelSize: Math.round(18*bridge.fontScale); font.bold: true; Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.bottomMargin: 8 }
    Label { visible: root.field.kind !== "bool"; text: bridge.translate(root.field.label); color: bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; Layout.minimumWidth: 0 }
    OndaSwitch { visible: root.field.kind === "bool"; text: bridge.translate(root.field.label); checked: root.current === true; onToggled: root.save(checked); Layout.fillWidth: true; Layout.minimumWidth: 0 }
    ChoiceBox { visible: root.field.kind === "select"; Layout.fillWidth: true; Layout.minimumWidth: 0; model: root.field.choices || []; currentIndex: Math.max(0,model.indexOf(root.current)); displayText: bridge.translate(currentText).replace(" (320 kbps)",""); onActivated: root.save(model[index]) }
    OndaTextField { visible: root.field.kind !== "bool" && root.field.kind !== "select"; Layout.fillWidth: true; Layout.minimumWidth: 0; text: root.current === undefined ? "" : String(root.current); echoMode: root.field.key === "spotify_client_secret" ? TextInput.Password : TextInput.Normal; onEditingFinished: root.save(text); selectByMouse: true; color: bridge.palette.text; background: Rectangle { radius: 8; color: bridge.palette.input; border.color: parent.activeFocus ? bridge.palette.accent : bridge.palette.line } }
    Label { visible: !!root.field.hint; text: bridge.translate(root.field.hint || ""); color: bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; Layout.minimumWidth: 0; font.pixelSize: Math.round(12*bridge.fontScale) }
}
