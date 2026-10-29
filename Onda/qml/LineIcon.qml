import QtQuick
Canvas {
    id: icon
    property string glyph: "play"
    property color ink: bridge.palette.text
    implicitWidth: 24; implicitHeight: 24
    onGlyphChanged: requestPaint()
    onInkChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
        var c=getContext("2d");c.reset();c.scale(width/24,height/24);c.strokeStyle=ink;c.lineWidth=1.7;c.lineCap="round";c.lineJoin="round"
        function line(x,y,a,b){c.beginPath();c.moveTo(x,y);c.lineTo(a,b);c.stroke()}
        function path(points,closed){c.beginPath();c.moveTo(points[0],points[1]);for(var i=2;i<points.length;i+=2)c.lineTo(points[i],points[i+1]);if(closed)c.closePath();c.stroke()}
        function circle(x,y,r){c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.stroke()}
        var g=glyph
        if(g==="mini"){c.strokeRect(3,4,18,16);c.strokeRect(11,11,8,7)}
        else if(g==="pause"){line(8,5,8,19);line(16,5,16,19)}
        else if(g==="previous"){line(5,5,5,19);path([18,5,8,12,18,19],true)}
        else if(g==="next"){line(19,5,19,19);path([6,5,16,12,6,19],true)}
        else if(g==="stop")c.strokeRect(6,6,12,12)
        else if(g==="close"){line(6,6,18,18);line(6,18,18,6)}
        else if(g==="check")path([5,12,10,17,20,6])
        else if(g==="warning"){path([12,3,22,21,2,21],true);line(12,9,12,14);line(12,17,12,17.3)}
        else if(g==="add"){line(12,4,12,20);line(4,12,20,12)}
        else if(g==="shuffle"){path([3,6,7,6,17,18,21,18]);path([3,18,7,18,17,6,21,6]);path([18,3,21,6,18,9]);path([18,15,21,18,18,21])}
        else if(g==="repeat"||g==="repeat-one"){path([4,10,4,6,20,6,17,3]);path([20,14,20,18,4,18,7,21]);path([17,9,20,6]);path([7,15,4,18]);if(g==="repeat-one"){path([10,10,12,9,12,15]);line(10,15,14,15)}}
        else if(g==="equalizer"){line(5,3,5,21);line(12,3,12,21);line(19,3,19,21);circle(5,8,2.5);circle(12,16,2.5);circle(19,10,2.5)}
        else if(g==="up"){path([6,10,12,4,18,10]);line(12,4,12,20)}
        else if(g==="down"){path([6,14,12,20,18,14]);line(12,4,12,20)}
        else if(g==="minimize")line(5,12,19,12)
        else if(g==="expand"){path([8,5,19,5,19,16]);line(19,5,5,19)}
        else if(g==="pin"){path([8,3,16,3,15,9,18,13,6,13,9,9],true);line(12,13,12,21)}
        else if(g==="queue"){for(var y=6;y<=18;y+=6){line(8,y,21,y);line(3,y,4,y)}}
        else if(g==="more"){circle(5,12,1);circle(12,12,1);circle(19,12,1)}
        else if(g==="menu"){line(4,6,20,6);line(4,12,20,12);line(4,18,20,18)}
        else if(g==="back")path([15,5,8,12,15,19])
        else if(g==="volume"){path([3,9,7,9,12,5,12,19,7,15,3,15],true);c.beginPath();c.arc(12,12,6,-.8,.8);c.stroke();c.beginPath();c.arc(12,12,10,-.8,.8);c.stroke()}
        else if(g==="catalog"){circle(10,10,6);line(15,15,21,21)}
        else if(g==="downloads"){path([8,8,5,8,2,11,2,15,5,18,10,18,13,15]);path([11,9,14,6,19,6,22,9,22,13,19,16,16,16]);line(8,14,16,10)}
        else if(g==="history"){c.beginPath();c.arc(12,12,9,-2.5,Math.PI*1.4);c.stroke();path([3,3,3,8,8,8]);path([12,7,12,12,16,14])}
        else if(g==="playlists"){c.strokeRect(4,3,16,18);circle(12,12,5);circle(12,12,1)}
        else if(g==="images"){c.strokeRect(3,4,18,16);circle(8,9,2);path([4,18,11,11,20,19])}
        else if(g==="converter"){path([16,3,21,7,3,7]);path([8,21,3,17,21,17])}
        else if(g==="metadata"){path([3,18,8,5,13,18]);line(5,14,11,14);line(16,7,22,7);line(16,12,22,12);line(16,17,20,17)}
        else if(g==="settings"){circle(12,12,4);for(var a=0;a<8;a++){var t=a*Math.PI/4;line(12+8*Math.cos(t),12+8*Math.sin(t),12+10*Math.cos(t),12+10*Math.sin(t))}circle(12,12,8)}
        else if(g==="timer"){circle(12,14,8);line(9,2,15,2);line(12,2,12,6);line(12,14,12,9);line(18,7,20,5)}
        else path([7,5,18,12,7,19],true)
    }
}
