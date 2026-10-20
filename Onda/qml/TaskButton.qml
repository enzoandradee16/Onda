import QtQuick
ActionButton {
    id: control
    property string operation: ""
    property var parameters: ({})
    property var taskNames: [operation]
    property string idleText: ""
    readonly property bool taskRunning: taskNames.some(function(name) { return workspace.activity.busy.indexOf(name) >= 0 })
    text: taskRunning ? bridge.translate("Cancelar") : idleText
    onClicked: {
        if (taskRunning) taskNames.forEach(function(name) { workspace.invoke("cancel_task",{name:name}) })
        else workspace.invoke(operation,parameters)
    }
}
