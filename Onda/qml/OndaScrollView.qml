import QtQuick
import QtQuick.Controls
ScrollView {
    id: control
    rightPadding: 20
    clip: true
    ScrollBar.vertical: OndaScrollBar {
        parent: control
        x: control.width-width
        y: control.topPadding
        height: control.availableHeight
    }
}
