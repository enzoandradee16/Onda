import QtQuick
import QtQuick.Controls
MenuSeparator {
    topPadding:5;bottomPadding:5;leftPadding:8;rightPadding:8
    implicitHeight:visible?11:0
    height:implicitHeight
    contentItem:Rectangle {implicitWidth:140;implicitHeight:1;color:bridge.palette.line}
}
