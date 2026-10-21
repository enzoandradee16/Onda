import QtQuick
import QtQuick.Shapes
Item {
    id: mark
    implicitWidth: 76
    implicitHeight: 50
    Shape {
        preferredRendererType: Shape.CurveRenderer
        antialiasing: true
        width: 100; height: 64
        transform: Scale { xScale: mark.width/100; yScale: mark.height/64 }
        ShapePath {
            strokeColor: bridge.palette.accent
            strokeWidth: 4.5
            capStyle: ShapePath.RoundCap
            joinStyle: ShapePath.RoundJoin
            fillColor: "transparent"
            PathSvg { path: bridge.brandPath }
        }
    }
}
