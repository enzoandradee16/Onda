import QtQuick
import QtQuick.Controls
Item {
    id: handle
    property var listView
    property var dragItem: null
    property int rowIndex: -1
    property int targetIndex: -1
    property int itemCount: 0
    property bool dragging: false
    property bool showIndicator: true
    property bool doubleClickEnabled: false
    property real offsetY: 0
    property real pressY: 0
    property real pressContentY: 0
    property real pointerY: 0
    readonly property real cardOffset: {
        if(dragging)return offsetY
        var active=listView ? listView.activeDrag : null
        if(!active || active.targetIndex<0 || !active.dragItem)return 0
        var from=active.rowIndex,to=active.targetIndex
        var distance=active.dragItem.height+listView.spacing
        if(from<to && rowIndex>from && rowIndex<=to)return -distance
        if(from>to && rowIndex>=to && rowIndex<from)return distance
        return 0
    }
    signal moved(int target)
    signal tapped()
    signal doubleTapped()
    implicitWidth: 32; implicitHeight: 44
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: bridge.translate("Arrastar para reorganizar")
    Accessible.description: bridge.translate("Use as setas para mover o item na fila.")
    Keys.onUpPressed: if(rowIndex>0)moved(rowIndex-1)
    Keys.onDownPressed: if(rowIndex+1<itemCount)moved(rowIndex+1)
    function interactiveAt(item,point) {
        if(!item || !item.visible || !item.enabled)return false
        var p=item.mapFromGlobal(point)
        if(p.x<0 || p.y<0 || p.x>item.width || p.y>item.height)return false
        if(item!==handle && typeof item.down==="boolean")return true
        for(var i=0;i<item.children.length;i++)if(interactiveAt(item.children[i],point))return true
        return false
    }
    function begin(point) {
        forceActiveFocus();pressY=point.y;pressContentY=listView.contentY;pointerY=listView.mapFromGlobal(point).y
    }
    function update(point) {
        pointerY=listView.mapFromGlobal(point).y
        var delta=point.y-pressY
        if(!dragging && Math.abs(delta)>=Qt.styleHints.startDragDistance){dragging=true;listView.activeDrag=handle}
        if(dragging) {
            offsetY=delta+listView.contentY-pressContentY
            locateTarget()
        }
    }
    function locateTarget() {
            var center=(dragItem ? dragItem.y+dragItem.height/2 : 0)+offsetY
            var distance=Infinity;targetIndex=rowIndex
            for(var i=0;i<itemCount;i++) {
                var item=listView.itemAtIndex(i)
                if(item && Math.abs(item.y+item.height/2-center)<distance) {
                    targetIndex=i;distance=Math.abs(item.y+item.height/2-center)
                }
            }
    }
    function finish(point) {
        update(point)
        var target=targetIndex, wasDragging=dragging
        cancel()
        if(wasDragging && target>=0 && target!==rowIndex)moved(target)
        else if(!wasDragging)tapped()
    }
    function cancel(){if(listView && listView.activeDrag===handle)listView.activeDrag=null;dragging=false;offsetY=0;targetIndex=-1}
    Rectangle {visible:handle.showIndicator;anchors.fill:parent;radius:6;color:handle.activeFocus || handle.dragging ? bridge.palette.hover : "transparent";border.color:handle.activeFocus ? bridge.palette.accent : "transparent"}
    Label {visible:handle.showIndicator;anchors.centerIn:parent;text:"≡";font.pixelSize:24;color:handle.enabled ? bridge.palette.muted : bridge.palette.line}
    MouseArea {
        id:area;anchors.fill:parent;preventStealing:true;hoverEnabled:true
        cursorShape:pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        onPressed:function(mouse){handle.begin(mapToGlobal(mouse.x,mouse.y))}
        onPositionChanged:function(mouse){if(pressed)handle.update(mapToGlobal(mouse.x,mouse.y))}
        onReleased:function(mouse){handle.finish(mapToGlobal(mouse.x,mouse.y))}
        onDoubleClicked:function(mouse){if(handle.doubleClickEnabled)handle.doubleTapped();else mouse.accepted=false}
        onCanceled:handle.cancel()
    }
    MouseArea {
        objectName:"queueCardDragSurface"
        parent:handle.dragItem;anchors.fill:parent;z:100;enabled:handle.enabled && handle.visible;preventStealing:true
        acceptedButtons:Qt.LeftButton
        cursorShape:pressed ? Qt.ClosedHandCursor : Qt.ArrowCursor
        onPressed:function(mouse){var point=mapToGlobal(mouse.x,mouse.y);if(handle.interactiveAt(handle.dragItem,point)){mouse.accepted=false;return}handle.begin(point)}
        onPositionChanged:function(mouse){if(pressed)handle.update(mapToGlobal(mouse.x,mouse.y))}
        onReleased:function(mouse){handle.finish(mapToGlobal(mouse.x,mouse.y))}
        onDoubleClicked:function(mouse){if(handle.doubleClickEnabled)handle.doubleTapped();else mouse.accepted=false}
        onCanceled:handle.cancel()
    }
    Timer {interval:40;repeat:true;running:handle.dragging
        onTriggered:{
            var view=handle.listView
            var delta=handle.pointerY<40 ? -18 : handle.pointerY>view.height-40 ? 18 : 0
            if(delta) {
                var before=view.contentY
                view.contentY=Math.max(view.originY,Math.min(view.originY+Math.max(0,view.contentHeight-view.height),before+delta))
                handle.offsetY+=view.contentY-before
                handle.locateTarget()
            }
        }
    }
    ToolTip.visible:area.containsMouse && !handle.dragging
    ToolTip.text:Accessible.name
}
