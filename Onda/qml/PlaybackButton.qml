import QtQuick
import QtQuick.Layouts
ActionButton {
    id: button
    property string glyph: "play"
    leftPadding: 4; rightPadding: 4; topPadding: 2; bottomPadding: 2
    implicitWidth: text ? contentItem.implicitWidth+32 : 44
    contentItem: RowLayout {
        spacing: 8
        LineIcon { glyph: button.glyph; Layout.preferredWidth: 24; Layout.preferredHeight: 24; Layout.alignment: Qt.AlignHCenter; ink: button.primary ? bridge.palette.accent_text : bridge.palette.text }
        Text { visible: !!button.text; text: button.text; color: button.primary ? bridge.palette.accent_text : bridge.palette.text; font.pixelSize: Math.round(14*bridge.fontScale); Layout.alignment: Qt.AlignVCenter }
    }
}
