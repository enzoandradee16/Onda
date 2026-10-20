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
            PathSvg { path: "M 4 32 C 8 24 10 25 13 32 S 19 41 22 31 C 25 12 29 11 30 32 C 32 57 37 57 40 21 C 43 -5 48 -3 48 30 C 48 73 54 73 58 28 C 62 3 66 12 67 31 C 68 52 73 50 76 31 C 79 17 82 20 85 31 C 88 39 91 38 96 32" }
        }
    }
}
