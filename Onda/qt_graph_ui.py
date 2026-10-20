"""Cached graph layer: phase/marker animation is rendered separately by Qt Quick."""
import math
from PySide6.QtCore import Property, Signal, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtQuick import QQuickPaintedItem

class BeatGraph(QQuickPaintedItem):
    changed=Signal()
    def __init__(self,parent=None):
        super().__init__(parent);self.setAntialiasing(True)
        self._data={'count':64,'links':[],'flow':[]};self._accent=QColor('#bd2738');self._muted=QColor('#91a0b3')
    @Property('QVariantMap',notify=changed)
    def graphData(self):return self._data
    @graphData.setter
    def graphData(self,value):
        if self._data!=value:self._data=value;self.changed.emit();self.update()
    @Property(QColor,notify=changed)
    def accent(self):return self._accent
    @accent.setter
    def accent(self,value):
        if self._accent!=value:self._accent=QColor(value);self.changed.emit();self.update()
    @Property(QColor,notify=changed)
    def muted(self):return self._muted
    @muted.setter
    def muted(self,value):
        if self._muted!=value:self._muted=QColor(value);self.changed.emit();self.update()
    def paint(self,painter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w,h=self.width(),self.height();center=QPointF(w/2,h/2);radius=min(w,h)*.42;n=max(1,int(self._data.get('count',64)))
        def point(i):
            angle=i/n*2*math.pi-math.pi/2;return center+QPointF(math.cos(angle)*radius,math.sin(angle)*radius)
        def curve(a,b):
            path=QPainterPath(point(a));path.quadTo(center,point(b));return path
        ink=QColor(self._accent);ink.setAlphaF(.28);painter.setPen(QPen(ink,1.));painter.setBrush(QColor('transparent'))
        for a,b in self._data.get('links',[]):painter.drawPath(curve(a,b))
        ink=QColor(self._accent);ink.setAlphaF(.7);painter.setPen(QPen(ink,1.8))
        for a,b in self._data.get('used',[]):
            if b!=(a+1)%n:painter.drawPath(curve(a,b))
        painter.setPen(QPen(self._muted,.7));painter.setBrush(self._muted)
        for i in range(0,n,max(1,n//160)):painter.drawEllipse(point(i),2.4,2.4)
        painter.setBrush(QColor('transparent'))
        flow=self._data.get('flow',[])
        for k,(a,b) in enumerate(flow):
            ink=QColor(self._accent);ink.setAlphaF(.75+.25*(k+1)/len(flow));painter.setPen(QPen(ink,2.7))
            if b==(a+1)%n:painter.drawArc(QRectF(w/2-radius,h/2-radius,radius*2,radius*2),round((90-a/n*360)*16),round(-360/n*16))
            else:
                painter.drawPath(curve(a,b));end=point(b);delta=end-center;length=math.hypot(delta.x(),delta.y())
                if length:
                    unit=delta/length;side=QPointF(-unit.y(),unit.x())*4;back=end-unit*10
                    painter.drawLine(back+side,end);painter.drawLine(back-side,end)
