import QtQuick
import QtQuick.Controls

Slider {
    id: control
    property real bufferedValue: from
    property var markedRange: []
    property var markedPoints: []
    property int previewMarker: -1
    property real previewMarkerValue: 0
    signal markedPointMoved(int index, real value)
    implicitHeight: 34
    from: 0
    to: 100
    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        implicitWidth: 180
        implicitHeight: 5
        width: control.availableWidth
        height: implicitHeight
        radius: 3
        opacity: control.enabled ? 1 : .5
        color: bridge.palette.mode === "Preto puro" ? "#555b64" : bridge.palette.line
        Rectangle {
            width: Math.max(0, Math.min(1, (control.bufferedValue - control.from) / Math.max(.001, control.to - control.from))) * parent.width
            height: parent.height
            radius: 3
            color: bridge.palette.accent
            opacity: .3
        }
        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: 3
            color: control.enabled ? bridge.palette.accent : bridge.palette.muted
        }
        Rectangle {
            objectName: "playbackMarkedRange"
            readonly property real leftValue: control.previewMarker === 0 ? control.previewMarkerValue : (control.markedRange[0] ?? control.from)
            readonly property real rightValue: control.previewMarker === 1 ? control.previewMarkerValue : (control.markedRange[1] ?? control.to)
            visible: control.markedRange.length === 2
            x: visible ? parent.width * (leftValue - control.from) / (control.to - control.from) : 0
            width: visible ? parent.width * Math.max(0, rightValue - leftValue) / (control.to - control.from) : 0
            height: parent.height + 4
            anchors.verticalCenter: parent.verticalCenter
            radius: 3
            color: "transparent"
            border.color: bridge.palette.accent
        }
    }
    Repeater {
            model: control.markedPoints
            delegate: Item {
                id: marker
                required property int index
                required property real modelData
                objectName: index === 0 ? "sectionStartMarker" : "sectionEndMarker"
                visible: modelData >= control.from
                z: 3
                readonly property real baseX: control.background.width * ((modelData - control.from) / Math.max(.001, control.to - control.from)) - (index === 0 ? 1 : width - 1)
                x: control.background.x + Math.max(0, Math.min(control.background.width - width, baseX + markerDrag.offset))
                y: control.background.y + (control.background.height - height) / 2
                width: 7
                height: 19
                Rectangle {
                    width: 2
                    height: parent.height
                    anchors.left: index === 0 ? parent.left : undefined
                    anchors.right: index === 1 ? parent.right : undefined
                    color: bridge.palette.accent
                }
                Rectangle { width: parent.width; height: 2; color: bridge.palette.accent }
                Rectangle { width: parent.width; height: 2; anchors.bottom: parent.bottom; color: bridge.palette.accent }
                MouseArea {
                    id: markerDrag
                    anchors.fill: parent
                    anchors.margins: -4
                    cursorShape: Qt.SizeHorCursor
                    property real offset: 0
                    property real pressX: 0
                    onPressed: function (mouse) {
                        pressX = mapToItem(marker.parent, mouse.x, mouse.y).x;
                    }
                    onPositionChanged: function (mouse) {
                        if (pressed) {
                            const pixels = Math.max(1, control.background.width);
                            const span = control.to - control.from;
                            const delta = mapToItem(marker.parent, mouse.x, mouse.y).x - pressX;
                            const lower = marker.index === 1 ? Math.max(control.from, control.markedPoints[0]) + .1 : control.from;
                            const upper = marker.index === 0 && control.markedPoints[1] >= 0 ? control.markedPoints[1] - .1 : control.to;
                            const value = Math.min(upper, Math.max(lower, marker.modelData + delta * span / pixels));
                            offset = (value - marker.modelData) * pixels / span;
                            control.previewMarker = marker.index;
                            control.previewMarkerValue = value;
                        }
                    }
                    onReleased: {
                        if (offset !== 0)
                            control.markedPointMoved(marker.index, marker.modelData + offset * (control.to - control.from) / Math.max(1, control.background.width));
                        offset = 0;
                        control.previewMarker = -1;
                    }
                    onCanceled: {
                        offset = 0;
                        control.previewMarker = -1;
                    }
                }
            }
    }
    handle: Rectangle {
        x: control.leftPadding + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        implicitWidth: control.pressed ? 21 : 18
        implicitHeight: implicitWidth
        opacity: control.enabled ? 1 : .5
        radius: width / 2
        color: control.enabled ? bridge.palette.accent : bridge.palette.muted
        border.color: control.activeFocus ? bridge.palette.text : bridge.palette.surface
        border.width: 2
        Behavior on implicitWidth {
            NumberAnimation {
                duration: bridge.animations ? 90 : 0
            }
        }
    }
}
