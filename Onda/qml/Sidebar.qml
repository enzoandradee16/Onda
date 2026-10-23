import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Rectangle {
    id: side
    objectName: "sidebar"
    signal settingsRequested()
    property bool collapsed: false
    property real panelWidth: collapsed ? 76 : (workspace.preferences.sidebar_width || 220)
    Layout.preferredWidth: panelWidth
    Layout.fillHeight: true
    color: bridge.palette.bg
    Behavior on panelWidth { NumberAnimation { duration: bridge.animations ? 240 : 0; easing.type: Easing.InOutCubic } }
    Rectangle { width: 1; color: bridge.palette.line; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 14; spacing: Math.round(12*bridge.spacing)
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 62; spacing: 8
            BrandMark { Layout.preferredWidth: side.collapsed ? 48 : 76; Layout.preferredHeight: side.collapsed ? 38 : 50 }
            Text { text: "ONDA"; color: bridge.palette.accent; font.family: "Century Gothic"; font.pixelSize: 34; font.weight: Font.Bold; font.letterSpacing: -1; opacity: side.collapsed ? 0 : 1; visible: opacity > 0; Behavior on opacity { NumberAnimation { duration: bridge.animations ? 120 : 0 } } }
            Item { Layout.fillWidth: true }
        }
        Button {
            objectName: "sidebarToggle"
            Layout.preferredWidth: 48; Layout.alignment: Qt.AlignLeft; implicitHeight: 32; text: side.collapsed ? "\uE700" : "\uE76B"
            font.family: "Segoe MDL2 Assets"; palette.buttonText: bridge.palette.muted
            background: Rectangle { radius: 6; color: parent.hovered ? bridge.palette.hover : "transparent" }
            onClicked: side.collapsed = !side.collapsed
            Accessible.name: bridge.translate("Recolher menu")
        }
        Column {
            Layout.fillWidth: true; spacing: Math.round(3*bridge.spacing)
            Repeater {
                model: workspace.navigation
                Rectangle {
                    id: nav
                    required property var modelData
                    readonly property bool active: modelData.key === workspace.currentPage || (modelData.key === "effects" && workspace.currentPage === "jukebox")
                    visible: !modelData.key || workspace.hiddenTabs.indexOf(modelData.key) < 0
                    width: parent.width; height: !visible ? 0 : modelData.group ? (modelData.group === "FERRAMENTAS" ? 48 : 30) : 43; radius: 8
                    color: nav.active ? bridge.palette.selected : "transparent"
                    Rectangle { visible: nav.active; width: 3; height: 24; radius: 2; color: bridge.palette.accent; anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter }
                    Rectangle { visible: nav.modelData.group === "FERRAMENTAS"; width: parent.width-20; height: 1; anchors.top: parent.top; anchors.topMargin: 8; anchors.horizontalCenter: parent.horizontalCenter; color: bridge.palette.flat_black ? "#303945" : bridge.palette.line }
                    Text {
                        visible: !!nav.modelData.group && !side.collapsed; text: bridge.translate(nav.modelData.group || "")
                        anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter
                        color: bridge.palette.muted; font.pixelSize: Math.round(10*bridge.fontScale); font.letterSpacing: 1
                    }
                    Row {
                        visible: !nav.modelData.group; anchors.left: parent.left; anchors.leftMargin: side.collapsed ? 15 : 12; height: parent.height; spacing: Math.round(12*bridge.spacing)
                        Text { text: nav.modelData.icon || ""; font.family: "Segoe MDL2 Assets"; font.pixelSize: Math.round(18*bridge.fontScale); anchors.verticalCenter: parent.verticalCenter; color: nav.active ? bridge.palette.accent : bridge.palette.muted }
                        Text { text: bridge.translate(nav.modelData.name || ""); visible: !side.collapsed; font.pixelSize: Math.round(13*bridge.fontScale); font.weight: nav.active ? Font.DemiBold : Font.Normal; anchors.verticalCenter: parent.verticalCenter; color: nav.active ? bridge.palette.accent : bridge.palette.muted }
                    }
                    MouseArea { id: navMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: nav.modelData.key ? Qt.PointingHandCursor : Qt.ArrowCursor; onClicked: if (nav.modelData.key) workspace.selectNavigationPage(nav.modelData.key) }
                    ToolTip.visible: navMouse.containsMouse && side.collapsed && !nav.modelData.group
                    ToolTip.text: bridge.translate(nav.modelData.name || "")
                }
            }
        }
        Item { Layout.fillHeight: true }
        ActionButton { Layout.fillWidth: true; text: side.collapsed ? "⚙" : bridge.translate("Configurações"); onClicked: side.settingsRequested() }
    }
}
