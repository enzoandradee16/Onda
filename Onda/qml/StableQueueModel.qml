import QtQuick
import Onda 1.0
QueueRowsModel {
    property var rows: []
    readonly property var selectionRows: Array.from(rows || [])
    property var selectedIds: []
    property string anchorId: ""
    function selected(row) {
        return selectedIds.includes(row.id)
    }
    readonly property var selectedRows: {
        const indices = []
        if (selectedIds.length) {
            for (let index = 0; index < rows.length; ++index) {
                if (!rows[index].current && selected(rows[index]))
                    indices.push(index)
            }
        }
        return indices
    }
    function select(index, modifiers) {
        const id = rows[index].id
        const anchor = selectionRows.findIndex(row => row.id === anchorId)
        if ((modifiers & Qt.ShiftModifier) && anchor >= 0) {
            selectedIds = selectionRows.slice(Math.min(anchor, index), Math.max(anchor, index) + 1)
                .filter(row => !row.current).map(row => row.id)
            return
        }
        if (modifiers & Qt.ControlModifier)
            selectedIds = selected(rows[index]) ? selectedIds.filter(value => value !== id) : selectedIds.concat(id)
        else
            selectedIds = [id]
        anchorId = id
    }
    function actionIndices(index) {
        const row = rows[index]
        return selected(row) ? selectionRows.filter(item => !item.current && selected(item)).map(item => item.queueIndex)
                             : [row.queueIndex]
    }
    function moveSelection(index, target) {
        bridge.moveQueuedGroup(actionIndices(index), rows[target].queueIndex, target > index)
    }
    function moveStep(index, step) {
        const indices = actionIndices(index)
        const edge = step < 0 ? indices[0] : indices[indices.length - 1]
        const destination = selectionRows.findIndex(row => row.queueIndex === edge) + step
        if (destination >= 0 && destination < rows.length && !rows[destination].current)
            bridge.moveQueuedGroup(indices, rows[destination].queueIndex, step > 0)
    }
    function moveNext(index) {
        const next = selectionRows.find(row => !row.current)
        if (next) bridge.moveQueuedGroup(actionIndices(index), next.queueIndex, false)
    }
    function handlesShortcut(event) {
        const modifiers = Number(event.modifiers)
        return (modifiers === Number(Qt.ControlModifier) &&
                (event.key === Qt.Key_A || (event.key === Qt.Key_Z && bridge.canUndoQueueRemoval))) ||
               ((modifiers === Number(Qt.AltModifier) || modifiers === Number(Qt.ShiftModifier)) &&
                (event.key === Qt.Key_Up || event.key === Qt.Key_Down))
    }
    function handleKey(event, index, view) {
        const modifiers = Number(event.modifiers)
        if (event.key === Qt.Key_Delete) {
            bridge.removeQueuedGroup(actionIndices(index))
        } else if (event.key === Qt.Key_A && modifiers === Number(Qt.ControlModifier)) {
            selectedIds = selectionRows.filter(row => !row.current).map(row => row.id)
            anchorId = rows[index].id
        } else if (event.key === Qt.Key_Z && modifiers === Number(Qt.ControlModifier) && bridge.canUndoQueueRemoval) {
            bridge.undoQueueRemoval()
        } else if (event.key === Qt.Key_Up || event.key === Qt.Key_Down) {
            const step = event.key === Qt.Key_Up ? -1 : 1
            const target = index + step
            if (target < 0 || target >= rows.length || rows[target].current) return
            if (modifiers === Number(Qt.AltModifier)) {
                moveStep(index, step)
            } else if (modifiers === Number(Qt.ShiftModifier) || modifiers === Number(Qt.NoModifier)) {
                if (modifiers === Number(Qt.ShiftModifier) && !anchorId) select(index, Qt.NoModifier)
                select(target, event.modifiers)
                view.positionViewAtIndex(target, ListView.Contain)
                const item = view.itemAtIndex(target)
                if (item) item.forceActiveFocus()
            } else return
        } else return
        event.accepted = true
    }
    onRowsChanged: setRows(rows)
}
