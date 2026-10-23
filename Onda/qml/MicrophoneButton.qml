import QtQuick
import QtQuick.Controls
ActionButton {
    id: button
    implicitWidth: 44
    Accessible.name: bridge.translate("Letra")
    ToolTip.visible: hovered
    ToolTip.text: Accessible.name
    contentItem: Item {
        implicitWidth: 22; implicitHeight: 22
        Canvas {
            anchors.centerIn: parent; width: 24; height: 24
            property color ink: button.primary ? bridge.palette.accent_text : bridge.palette.text
            onInkChanged: requestPaint()
            onPaint: {
                var ctx=getContext("2d");ctx.reset();ctx.strokeStyle=ink;ctx.fillStyle=ink;ctx.lineWidth=1.4;ctx.lineCap="round";ctx.lineJoin="round"
                ctx.save();ctx.translate(12,12);ctx.rotate(Math.PI/4)
                ctx.beginPath();ctx.ellipse(-5.5,-10,11,10);ctx.stroke()
                ctx.beginPath();ctx.moveTo(-5,-5);ctx.lineTo(5,-5);ctx.stroke()
                ctx.beginPath();ctx.moveTo(-3,0);ctx.lineTo(-2,9);ctx.lineTo(2,9);ctx.lineTo(3,0);ctx.stroke()
                ctx.restore()
            }
        }
    }
}
