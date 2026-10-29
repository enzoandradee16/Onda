import QtQuick
Item {
    id: root
    property url source
    property bool active: false
    property bool animated: true
    property real phase: 0
    property real pulse: 0
    property bool dark: true
    Image { id: dimensions; source: root.source; sourceSize.width: 768; asynchronous: true; visible: false; onStatusChanged: {if(status===Image.Error)painted.clearArtwork();painted.requestPaint()} }
    Canvas {
        id: painted; objectName:"miniBackgroundCanvas";anchors.fill: parent
        renderStrategy: Canvas.Threaded
        property string loadedSource: ""
        property string pendingSource: ""
        property string previousSource: ""
        property real blend: 1
        function clearArtwork(){coverFade.stop();releasePrevious();if(loadedSource)unloadImage(loadedSource);loadedSource="";pendingSource="";blend=1;requestPaint()}
        onBlendChanged: requestPaint()
        function reload() {
            pendingSource=root.source.toString()
            if(!pendingSource){
                coverFade.stop()
                if(previousSource)unloadImage(previousSource)
                if(loadedSource)unloadImage(loadedSource)
                previousSource="";loadedSource="";blend=1
            } else if(pendingSource!==loadedSource)loadImage(pendingSource)
            requestPaint()
        }
        function releasePrevious(){if(previousSource && previousSource!==loadedSource)unloadImage(previousSource);previousSource=""}
        Component.onCompleted: reload()
        onImageLoaded: {
            if(pendingSource && pendingSource!==loadedSource && isImageLoaded(pendingSource)){
                coverFade.stop();releasePrevious();previousSource=loadedSource;loadedSource=pendingSource
                if(previousSource && root.animated && root.active)coverFade.restart()
                else {blend=1;releasePrevious()}
            }
            requestPaint()
        }
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx=getContext("2d");ctx.reset()
            if(!loadedSource || !isImageLoaded(loadedSource))return
            var w=width,h=height,radius=Math.sqrt(w*w+h*h)/2+2
            var ratio=dimensions.implicitWidth/Math.max(1,dimensions.implicitHeight) || 1
            var dw=radius*2*Math.max(1,ratio),dh=dw/ratio
            // Overlapping circular layers produce a small radial twist on the
            // software renderer as well, without depending on GPU shaders.
            function drawCover(url,alpha){
              ctx.globalAlpha=alpha
              for(var ring=20;ring>0;--ring) {
                var depth=1-ring/20
                var angle=Math.sin(root.phase)*0.12+Math.sin(root.phase+depth*2.2)*0.72*depth
                ctx.save();ctx.translate(w/2,h/2)
                ctx.beginPath();ctx.arc(0,0,radius*ring/20+1,0,Math.PI*2);ctx.clip()
                ctx.rotate(angle);ctx.drawImage(url,-dw/2,-dh/2,dw,dh);ctx.restore()
              }
            }
            if(previousSource && isImageLoaded(previousSource))drawCover(previousSource,1)
            drawCover(loadedSource,previousSource ? blend : 1);ctx.globalAlpha=1
            var colors=[]
            for(var c=0;c<3;++c){
                var pixel=ctx.getImageData(Math.max(0,Math.min(w-1,Math.round(w*(0.2+c*0.3)))),Math.max(0,Math.min(h-1,Math.round(h*(c===1?0.7:0.3)))),1,1).data
                colors.push([pixel[0],pixel[1],pixel[2]])
            }
            // Album-colored aurora. Broad gradients keep the movement soft.
            for(var i=0;i<3;++i){
                var x=w*(0.2+i*0.3+Math.sin(root.phase+i*2)*0.14)
                var y=h*(0.45+Math.cos(root.phase*2+i)*0.22)
                var aurora=ctx.createRadialGradient(x,y,0,x,y,Math.max(w,h)*0.7)
                aurora.addColorStop(0,"rgba("+colors[i].join(",")+","+(0.22+root.pulse*0.15)+")")
                aurora.addColorStop(1,"rgba("+colors[i].join(",")+",0)")
                ctx.fillStyle=aurora;ctx.fillRect(0,0,w,h)
            }
            var vignette=ctx.createRadialGradient(w/2,h*0.43,Math.min(w,h)*0.22,w/2,h/2,Math.max(w,h)*0.7)
            vignette.addColorStop(0,"transparent");vignette.addColorStop(1,root.dark?"rgba(0,0,0,0.5)":"rgba(0,0,0,0.13)")
            ctx.fillStyle=vignette;ctx.fillRect(0,0,w,h)
        }
        NumberAnimation {id:coverFade;target:painted;property:"blend";from:0;to:1;duration:700;easing.type:Easing.InOutQuad;onFinished:painted.releasePrevious()}
        // The phase clock also samples the pulse. Avoid repainting this canvas
        // at every interpolation step of the much smaller halo animation.
        Connections {target:root;function onSourceChanged(){painted.reload()} function onPhaseChanged(){painted.requestPaint()} function onDarkChanged(){painted.requestPaint()}}
    }
    Timer {interval:60;repeat:true;running:root.active&&root.animated&&root.source.toString().length>0;onTriggered:root.phase=(root.phase+0.006)%(Math.PI*2)}
}
