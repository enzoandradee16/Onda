import QtQuick
Item {
    id: root
    property alias source: image.source
    property alias sourceSize: image.sourceSize
    property alias fillMode: image.fillMode
    property alias asynchronous: image.asynchronous
    property alias cache: image.cache
    property alias smooth: image.smooth
    readonly property int status: image.status
    property real cornerRadius: Math.min(12,width*0.12,height*0.12)
    implicitWidth: image.implicitWidth
    implicitHeight: image.implicitHeight
    Image { id: image; anchors.fill: parent; opacity: 0; onStatusChanged: painted.requestPaint() }
    Canvas {
        id: painted; anchors.fill: parent
        property string loadedSource: ""
        function reload() {
            if(loadedSource)unloadImage(loadedSource)
            loadedSource=root.source.toString()
            if(loadedSource)loadImage(loadedSource)
            requestPaint()
        }
        Component.onCompleted: reload()
        onImageLoaded: requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx=getContext("2d");ctx.reset()
            if(!loadedSource || !isImageLoaded(loadedSource))return
            var w=width,h=height,r=root.cornerRadius
            ctx.beginPath();ctx.moveTo(r,0);ctx.lineTo(w-r,0);ctx.quadraticCurveTo(w,0,w,r);ctx.lineTo(w,h-r);ctx.quadraticCurveTo(w,h,w-r,h);ctx.lineTo(r,h);ctx.quadraticCurveTo(0,h,0,h-r);ctx.lineTo(0,r);ctx.quadraticCurveTo(0,0,r,0);ctx.closePath();ctx.clip()
            var pw=image.paintedWidth,ph=image.paintedHeight
            if(pw>0 && ph>0)ctx.drawImage(loadedSource,(w-pw)/2,(h-ph)/2,pw,ph)
        }
        Connections {target: root;function onSourceChanged(){painted.reload()} function onCornerRadiusChanged(){painted.requestPaint()}}
        Connections {target: image;function onPaintedWidthChanged(){painted.requestPaint()} function onPaintedHeightChanged(){painted.requestPaint()}}
    }
}
