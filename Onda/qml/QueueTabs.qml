import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Item {
    id:tabs
    property bool recent:false
    signal selected(bool recent)
    property bool motionReady:false
    readonly property var activeButton:motionReady&&tabButtons.count>0?tabButtons.itemAt(recent?1:0):null
    implicitWidth:tabRow.implicitWidth
    implicitHeight:42
    Layout.minimumWidth:0
    Component.onCompleted:Qt.callLater(function(){tabs.motionReady=true})
    RowLayout {
      id:tabRow;anchors.fill:parent;spacing:22
      Repeater {
        id:tabButtons
        model:["Fila","Tocado recentemente"]
        ToolButton {
            required property string modelData
            required property int index
            readonly property bool active:tabs.recent===(index===1)
            text:bridge.translate(modelData);checkable:true;checked:active
            implicitWidth:contentItem.implicitWidth;implicitHeight:42
            Layout.minimumWidth:0
            leftPadding:0;rightPadding:0
            onClicked:tabs.selected(index===1)
            contentItem:Label {text:parent.text;color:parent.active?bridge.palette.text:bridge.palette.muted;font.bold:true;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight;clip:true;Behavior on color {ColorAnimation {duration:bridge.animations?140:0}}}
            background:Rectangle {color:"transparent"}
        }
      }
    }
    Rectangle {
        objectName:"queueTabIndicator"
        x:tabs.activeButton?tabs.activeButton.x:0
        y:tabs.height-height
        width:tabs.activeButton?tabs.activeButton.width:0
        height:3;radius:1.5;color:bridge.palette.accent
        Behavior on x {enabled:tabs.motionReady&&bridge.animations;NumberAnimation {duration:180;easing.type:Easing.OutCubic}}
        Behavior on width {enabled:tabs.motionReady&&bridge.animations;NumberAnimation {duration:180;easing.type:Easing.OutCubic}}
    }
}
