import QtQuick
import QtQuick.Controls
ListView {
    readonly property real contentAreaWidth: Math.max(0,width-20)
    contentWidth: contentAreaWidth
    clip: true
    ScrollBar.vertical: OndaScrollBar {}
}
