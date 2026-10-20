import QtQuick
import QtQuick.Controls
Item {
    id: state
    property string heading: ""
    property string description: ""
    implicitHeight: 180
    Column {
        anchors.centerIn: parent
        width: Math.max(0,Math.min(560,parent.width-32))
        spacing: 10
        Label { width: parent.width; text: state.heading; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter; color: bridge.palette.text; font.pixelSize: Math.round(20*bridge.fontScale); font.weight: Font.DemiBold }
        Label { width: parent.width; text: state.description; wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter; color: bridge.palette.muted; font.pixelSize: Math.round(14*bridge.fontScale) }
    }
}
