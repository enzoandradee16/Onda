import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ColumnLayout {
    id: root
    objectName: "settingField_" + field.key
    required property var field
    property bool settings: false
    readonly property bool timeField: field.key === "schedule_start" || field.key === "schedule_stop"
    readonly property bool transitionDuration: field.key === "jukebox_transition_seconds"
    readonly property var current: settings ? workspace.preferences[field.key] : workspace.values[field.key]
    function save(value) { if (settings) workspace.setSetting(field.key,value); else workspace.setOption(field.key,value) }
    implicitWidth: 220
    Layout.minimumWidth: 0
    spacing: Math.round(6*bridge.spacing)
    Label { visible: !!root.field.section; text: bridge.translate(root.field.section || ""); color: bridge.palette.text; font.pixelSize: Math.round(18*bridge.fontScale); font.bold: true; Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.bottomMargin: 8 }
    Label { visible: root.field.kind !== "bool"; text: bridge.translate(root.field.label); color: bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; Layout.minimumWidth: 0 }
    OndaSwitch { visible: root.field.kind === "bool"; text: bridge.translate(root.field.label); checked: root.current === true; onToggled: root.save(checked); Layout.fillWidth: true; Layout.minimumWidth: 0 }
    RowLayout {
        visible: root.transitionDuration; Layout.fillWidth: true
        OndaSlider { id: transitionSlider; Layout.fillWidth: true; from: 1; to: 10; stepSize: 1; snapMode: Slider.SnapAlways; value: Number(root.current || 2); onMoved: root.save(Math.round(value)); Accessible.name: bridge.translate(root.field.label) }
        Label { text: Math.round(transitionSlider.value) + " s"; color: bridge.palette.text }
    }
    ChoiceBox { visible: root.field.kind === "select" && !root.transitionDuration; Layout.fillWidth: true; Layout.minimumWidth: 0; model: root.field.choices || []; currentIndex: Math.max(0,model.indexOf(root.current)); displayText: bridge.translate(currentText).replace(" (320 kbps)",""); onActivated: root.save(model[index]) }
    OndaTextField {
        id: scheduleTime
        visible: root.timeField; Layout.fillWidth: true
        inputMask: "99:99"
        inputMethodHints: Qt.ImhTime
        validator: RegularExpressionValidator { regularExpression: /([01][0-9]|2[0-3]):[0-5][0-9]/ }
        text: root.timeField ? String(root.current || (root.field.key === "schedule_start" ? "22:00" : "07:00")) : ""
        Accessible.name: bridge.translate(root.field.label)
        function restoreTime() { text=String(root.current || (root.field.key === "schedule_start" ? "22:00" : "07:00")) }
        onTextEdited: {
            if (acceptableInput) root.save(text)
            else { var position=cursorPosition; restoreTime();cursorPosition=position }
        }
        onEditingFinished: { if (acceptableInput) root.save(text); else restoreTime() }
        Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Delete || event.key === Qt.Key_Backspace || (event.key === Qt.Key_X && (event.modifiers & Qt.ControlModifier))) { event.accepted=true;return }
            if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
                var hour=cursorPosition<3
                var parts=text.split(":")
                var index=hour ? 0 : 1
                var limit=hour ? 24 : 60
                parts[index]=String((Number(parts[index])+(event.key === Qt.Key_Up ? 1 : -1)+limit)%limit).padStart(2,"0")
                text=parts.join(":");root.save(text);select(hour ? 0 : 3,hour ? 2 : 5);event.accepted=true
            }
        }
    }
    OndaTextField { visible: root.field.kind !== "bool" && root.field.kind !== "select" && !root.timeField; Layout.fillWidth: true; Layout.minimumWidth: 0; text: root.current === undefined ? "" : String(root.current); echoMode: root.field.key === "spotify_client_secret" ? TextInput.Password : TextInput.Normal; onEditingFinished: root.save(text); selectByMouse: true; color: bridge.palette.text; background: Rectangle { radius: 14; color: bridge.palette.input; border.color: parent.activeFocus ? bridge.palette.accent : bridge.palette.line } }
    Label { visible: !!root.field.hint; text: bridge.translate(root.field.hint || ""); color: bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true; Layout.minimumWidth: 0; font.pixelSize: Math.round(12*bridge.fontScale) }
}
