import QtQuick
import QtQuick.Window

Rectangle {
    id: card
    property bool tintPopup: false

    Repeater {
        model: card.tintPopup && card.visible && card.Window.window ? card.Window.window.popupTintLayers || [] : []
        delegate: Canvas {
            required property var modelData
            readonly property url artworkSource: modelData.source
            property url loadedSource
            anchors.fill: parent
            anchors.margins: card.border.width
            opacity: modelData.opacity * .60
            z: modelData.z
            onArtworkSourceChanged: {
                if (loadedSource.toString())
                    unloadImage(loadedSource)
                loadedSource = artworkSource
                if (artworkSource.toString())
                    loadImage(artworkSource)
                requestPaint()
            }
            onImageLoaded: requestPaint()
            onPaint: {
                const ctx = getContext("2d")
                ctx.reset()
                ctx.clearRect(0, 0, width, height)
                if (!artworkSource.toString() || !isImageLoaded(artworkSource))
                    return
                const corner = Math.max(0, card.radius - card.border.width)
                ctx.beginPath()
                ctx.roundedRect(0, 0, width, height, corner, corner)
                ctx.clip()
                ctx.drawImage(artworkSource, 0, 0, width, height)
            }
        }
    }
    color: bridge.palette.surface
    radius: 12
    border.color: bridge.palette.line
    border.width: bridge.palette.flat_black ? 0 : 1
    Behavior on color {
        ColorAnimation {
            duration: bridge.animations ? 180 : 0
        }
    }
}
