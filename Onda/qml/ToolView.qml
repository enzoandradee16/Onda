import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ScrollView {
    id: page
    property string mode: workspace.currentPage
    property bool audioOnly: workspace.values.converterSources.some(function(path) { return /\.(mp3|m4a|aac|flac|wav|ogg|opus)$/i.test(path) })
    clip: true
    contentWidth: availableWidth
    ColumnLayout { width: page.availableWidth; spacing: Math.round(18*bridge.spacing)
        Card { Layout.fillWidth: true; implicitHeight: sourceBody.implicitHeight+36
            ColumnLayout { id: sourceBody; anchors.fill: parent; anchors.margins: 18; spacing: Math.round(12*bridge.spacing)
                RowLayout { Layout.fillWidth: true
                    ActionButton { primary: true; text: bridge.translate("Escolher arquivo"); onClicked: workspace.invoke("pick",{kind: page.mode === "effects" ? "effects" : page.mode === "images" ? "image" : page.mode}) }
                    Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: bridge.palette.muted; text: page.mode === "converter" ? workspace.values.converterSources.join(" · ") : page.mode === "metadata" ? workspace.values.metadataSources.join(" · ") : page.mode === "effects" ? workspace.values.effectsSource : workspace.values.imageSource }
                }
                Label { text: bridge.translate(page.mode === "converter" ? "Selecione um ou vários arquivos para converter em lote." : page.mode === "metadata" ? "Edite os metadados e a capa do áudio." : page.mode === "images" ? "Converta imagens ou baixe fotos por link." : "Ajuste os efeitos e exporte a música inteira."); color: bridge.palette.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
            }
        }
        ColumnLayout { visible: page.mode === "converter"; Layout.fillWidth: true; spacing: Math.round(16*bridge.spacing)
            GridLayout { Layout.fillWidth: true; columns: page.availableWidth > 800 ? 3 : 2; columnSpacing: 16; rowSpacing: 16
                OptionField { Layout.fillWidth: true; field: ({key:"converterFormat",label:"Formato",kind:"select",choices:page.audioOnly ? ["MP3","M4A","AAC"] : ["MP4","MKV","MOV","MP3","M4A","AAC"]}) }
                OptionField { visible: !page.audioOnly && ["MP4","MKV","MOV"].indexOf(workspace.values.converterFormat) >= 0; Layout.fillWidth: true; field: ({key:"video_quality",label:"Qualidade",kind:"select",choices:["Equilibrada","Alta qualidade","Arquivo menor"]}) }
                OptionField { visible: !page.audioOnly && ["MP4","MKV","MOV"].indexOf(workspace.values.converterFormat) >= 0; Layout.fillWidth: true; field: ({key:"video_resolution",label:"Resolução máxima",kind:"select",choices:["Original","1080p","720p","480p"]}) }
                OptionField { visible: !page.audioOnly && ["MP4","MKV","MOV"].indexOf(workspace.values.converterFormat) >= 0; Layout.fillWidth: true; field: ({key:"video_bitrate",label:"Bitrate de vídeo",kind:"select",choices:["Automático","1000k","2500k","5000k","8000k","12000k","20000k"]}) }
                OptionField { Layout.fillWidth: true; field: ({key:"audio_bitrate",label:"Bitrate de áudio",kind:"select",choices:["96k","128k","192k","256k","320k"]}) }
                OptionField { visible: !page.audioOnly && ["MP4","MKV","MOV"].indexOf(workspace.values.converterFormat) >= 0; Layout.fillWidth: true; field: ({key:"video_fps",label:"FPS",kind:"select",choices:["Original","24","25","30","50","60"]}) }
                OptionField { visible: !page.audioOnly; Layout.fillWidth: true; field: ({key:"video_audio",label:"Áudio",kind:"select",choices:["Manter áudio","Sem áudio"]}) }
            }
            OndaSwitch { text: bridge.translate("Remover silêncio no início e no fim ao converter"); checked: workspace.values.trimSilence; onToggled: workspace.setOption("trimSilence",checked) }
            Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: bridge.palette.muted; text: bridge.translate("Detecta trechos abaixo de −45 dB por pelo menos 0,3 segundo. O corte é opcional, preserva as pausas internas e mantém o arquivo original.") }
            TaskButton { idleText: bridge.translate("Detectar silêncio"); operation: "detect_silence"; enabled: taskRunning || workspace.values.converterSources.length > 0 }
            Repeater { model: workspace.values.silenceResults || []
                Label { required property var modelData; Layout.fillWidth: true; wrapMode: Text.Wrap; color: modelData.error ? bridge.palette.error : bridge.palette.muted
                    text: modelData.source.split(/[\\/]/).pop()+": "+(modelData.error || (modelData.silent ? bridge.translate("Arquivo inteiramente silencioso; recorte automático indisponível.") : bridge.translate("Silêncio inicial")+": "+modelData.leading.toFixed(2)+" s · "+bridge.translate("Silêncio final")+": "+modelData.trailing.toFixed(2)+" s"))
                }
            }
            RowLayout {
                TaskButton { objectName: "convertButton"; primary: true; idleText: bridge.translate("Converter em lote"); enabled: taskRunning || workspace.values.converterSources.length > 0; operation: "convert"; taskNames: ["convert"] }
                ActionButton { visible: workspace.values.converterSources.length > 0; text: bridge.translate("Prévia do original"); onClicked: workspace.invoke("open_file",{path:workspace.values.converterSources[0]}) }
            }
        }
        ColumnLayout { visible: page.mode === "effects"; Layout.fillWidth: true; spacing: Math.round(18*bridge.spacing)
            Card {
                visible: !!workspace.values.effectsSource
                Layout.fillWidth: true; implicitHeight: 166
                RowLayout {
                    anchors.fill: parent; anchors.margins: 10; spacing: 16
                    Rectangle {
                        Layout.preferredWidth: 146; Layout.preferredHeight: 146; radius: 8; color: bridge.palette.input
                        Image { id: effectsArtwork; objectName: "effectsArtwork"; anchors.fill: parent; source: workspace.values.effectsCover || ""; sourceSize.width: 292; sourceSize.height: 292; fillMode: Image.PreserveAspectFit }
                        Label { anchors.centerIn: parent; visible: !workspace.values.effectsCover; text: "♪"; color: bridge.palette.muted; font.pixelSize: 40 }
                    }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 7
                        Label { Layout.fillWidth: true; text: (workspace.values.effectsRecord || {}).title || ""; color: bridge.palette.text; font.pixelSize: Math.round(19*bridge.fontScale); font.weight: Font.DemiBold; elide: Text.ElideRight }
                        Label { Layout.fillWidth: true; visible: !!text; text: ((workspace.values.effectsRecord || {}).artists || []).join(", "); color: bridge.palette.muted; elide: Text.ElideRight }
                        Label { Layout.fillWidth: true; visible: !!text; text: (workspace.values.effectsRecord || {}).album || ""; color: bridge.palette.muted; elide: Text.ElideRight }
                        Label { visible: workspace.values.duration > 0; text: workspace.clock(Math.floor(workspace.values.duration)); color: bridge.palette.muted }
                    }
                }
            }

            RowLayout { Layout.fillWidth: true
                Label { text: bridge.translate("Preset"); color: bridge.palette.text }
                ComboBox { id: effectsPreset; objectName: "effectsPreset"; Layout.preferredWidth: Math.round(240*bridge.fontScale); Layout.maximumWidth: Math.max(80,page.availableWidth-80); model: ["Original","Slowed leve","Slowed intenso","Sped Up leve","Sped Up intenso","Sped Up + Reverb","Só Reverb","Clássico","Atmosférico"]
                    delegate: ItemDelegate {
                        id: presetOption
                        width: effectsPreset.width
                        text: bridge.translate(modelData)
                        highlighted: effectsPreset.highlightedIndex === index
                        readonly property bool selected: effectsPreset.currentIndex === index
                        contentItem: Label { text: presetOption.text; font: presetOption.font; color: presetOption.highlighted || presetOption.selected ? bridge.palette.accent_text : bridge.palette.text; verticalAlignment: Text.AlignVCenter }
                        background: Rectangle { color: presetOption.highlighted || presetOption.selected ? bridge.palette.accent : bridge.palette.surface }
                    }
                    onActivated: { var values=[[100,0],[90,0],[75,0],[115,0],[130,0],[120,25],[100,30],[85,25],[75,50]]; workspace.setOption("speed",values[index][0]); workspace.setOption("reverb",values[index][1]) }
                }
            }
            Label { text: bridge.translate("Velocidade")+" · "+Math.round(workspace.values.speed)+"%"; color: bridge.palette.text }
            OndaSlider { Layout.fillWidth: true; from: 50; to: 150; value: workspace.values.speed; onMoved: workspace.setOption("speed",value) }
            Label { text: bridge.translate("Reverb")+" · "+Math.round(workspace.values.reverb)+"%"; color: bridge.palette.text }
            OndaSlider { Layout.fillWidth: true; value: workspace.values.reverb; onMoved: workspace.setOption("reverb",value) }
            OndaSwitch { text: bridge.translate("Manter tom (pitch) ao alterar a velocidade"); checked: workspace.values.keep_pitch; onToggled: workspace.setOption("keep_pitch",checked) }
            Label { visible: workspace.preferences.synced_lyrics; text: workspace.values.lyricText || ""; color: bridge.palette.accent; font.pixelSize: Math.round(20*bridge.fontScale); Layout.fillWidth: true; wrapMode: Text.Wrap }
            ActionButton { visible: workspace.preferences.synced_lyrics; text: bridge.translate("Escolher letra"); onClicked: workspace.invoke("pick",{kind:"effectLyrics"}) }
            Label { text: bridge.translate("Posição na música")+" · "+Math.floor(workspace.values.position)+" / "+Math.floor(workspace.values.duration)+" s"; color: bridge.palette.muted }
            OndaSlider { Layout.fillWidth: true; enabled: workspace.values.duration > 0; from: 0; to: Math.max(1,workspace.values.duration); value: workspace.values.position; onMoved: workspace.setOption("position",value) }
            Flow { Layout.fillWidth: true; spacing: Math.round(8*bridge.spacing)
                ActionButton { text: bridge.translate(workspace.values.previewActive && workspace.values.previewKind === "effects" && !workspace.values.previewProcessed ? "Parar prévia" : "Ouvir original"); enabled: !!workspace.values.effectsSource; onClicked: workspace.invoke("effects_preview",{processed:false}) }
                ActionButton { primary: true; text: bridge.translate(workspace.values.previewActive && workspace.values.previewKind === "effects" && workspace.values.previewProcessed ? "Parar prévia" : "Ouvir com efeitos"); enabled: !!workspace.values.effectsSource; onClicked: workspace.invoke("effects_preview",{processed:true}) }
                ComboBox { model: ["MP3","M4A","FLAC","WAV"]; onActivated: workspace.setOption("effectFormat",currentText) }
                TaskButton { idleText: bridge.translate("Exportar música inteira"); enabled: taskRunning || !!workspace.values.effectsSource; operation: "effects_export"; taskNames: ["effects_export"] }
            }
        }
        ColumnLayout { visible: page.mode === "images"; Layout.fillWidth: true; spacing: Math.round(14*bridge.spacing)
            OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate("Link da imagem ou publicação"); text: workspace.values.imageUrl; onTextEdited: workspace.setOption("imageUrl",text) }
            RowLayout { Layout.fillWidth: true
                OptionField { Layout.fillWidth: true; settings: true; field: ({key:"image_format",label:"Formato",kind:"select",choices:["Original","JPG","PNG","WebP","SVG"]}) }
                OptionField { Layout.fillWidth: true; settings: true; field: ({key:"image_size",label:"Tamanho máximo",kind:"select",choices:["Original","Até 1920 × 1080","Até 1280 × 720","Até 1080 × 1080","Personalizado"]}) }
                OptionField { visible: workspace.preferences.image_size === "Personalizado"; settings: true; field: ({key:"image_width",label:"Largura",kind:"text"}) }
                OptionField { visible: workspace.preferences.image_size === "Personalizado"; settings: true; field: ({key:"image_height",label:"Altura",kind:"text"}) }
            }
            OndaSwitch { text: bridge.translate("Manter proporção"); checked: workspace.preferences.image_keep_ratio; onToggled: workspace.setSetting("image_keep_ratio",checked) }
            RowLayout { TaskButton { idleText: bridge.translate("Visualizar"); operation: "image_preview"; taskNames: ["image_preview"] } TaskButton { primary: true; idleText: bridge.translate("Exportar / baixar"); operation: "image_export"; taskNames: ["image_export"] } }
            Label {
                objectName: "imageInformation"
                readonly property var original: (workspace.values.imageInfo || {}).source || ({})
                readonly property var output: (workspace.values.imageInfo || {}).output || ({})
                function summary(info) { return info.width+" × "+info.height+" px · "+info.format }
                visible: !!original.width || !!output.width
                Layout.fillWidth: true; wrapMode: Text.Wrap; color: bridge.palette.muted
                text: (original.width ? bridge.translate("Original")+": "+summary(original) : "")+(output.width ? "\n"+bridge.translate("Resultado")+": "+summary(output) : "")
            }
            EmptyState { Layout.fillWidth: true; Layout.preferredHeight: 220; visible: !workspace.values.imagePreview; heading: bridge.translate(workspace.activity.busy.indexOf("image_preview")>=0 ? "Carregando imagem…" : "Sua imagem aparecerá aqui"); description: bridge.translate("Escolha um arquivo ou cole um link e clique em Visualizar. A resolução e o formato serão mostrados quando disponíveis.") }
            Image { visible: !!workspace.values.imagePreview; source: workspace.values.imagePreview; Layout.fillWidth: true; Layout.preferredHeight: 360; fillMode: Image.PreserveAspectFit; asynchronous: true; cache: false }
        }
        ColumnLayout { visible: page.mode === "metadata"; Layout.fillWidth: true; spacing: Math.round(14*bridge.spacing)
            GridLayout { columns: 2; Layout.fillWidth: true; columnSpacing: 16; rowSpacing: 14
                Repeater { model: [{key:"title",label:"Título"},{key:"artists",label:"Artista"},{key:"album",label:"Álbum"},{key:"genre",label:"Gênero"},{key:"release_date",label:"Data de lançamento"},{key:"track_number",label:"Número da faixa"},{key:"disc_number",label:"Disco"}]
                    ColumnLayout { required property var modelData; Layout.fillWidth: true
                        RowLayout {
                            CheckBox { visible: workspace.values.metadataSources.length > 1; checked: workspace.values.metadataFields[modelData.key] || false; onToggled: { var values=workspace.values.metadataFields;values[modelData.key]=checked;workspace.setOption("metadataFields",values) } }
                            Label { text: bridge.translate(modelData.label); color: bridge.palette.muted }
                        }
                        OndaTextField { objectName: "metadataField_"+modelData.key; Layout.fillWidth: true; text: workspace.values.metadata[modelData.key] && typeof workspace.values.metadata[modelData.key].join === "function" ? workspace.values.metadata[modelData.key].join(", ") : workspace.values.metadata[modelData.key] || ""; onEditingFinished: { var record=workspace.values.metadata; record[modelData.key]=text;workspace.setOption("metadata",record) } }
                    }
                }
            }
            RowLayout { Layout.fillWidth: true; spacing: 22; Layout.alignment: Qt.AlignTop
                ColumnLayout { id: metadataControls; Layout.minimumWidth: 0; Layout.maximumWidth: Layout.preferredWidth; Layout.preferredWidth: Math.min(520,page.availableWidth-(workspace.values.metadataCover ? Math.min(220,page.availableWidth*0.33)+22 : 0)); Layout.alignment: Qt.AlignTop; spacing: 14
            Flow { Layout.fillWidth: true; spacing: Math.round(8*bridge.spacing)
                ActionButton { text: bridge.translate("Escolher capa"); onClicked: workspace.invoke("pick",{kind:"cover_path"}) }
                ActionButton { text: bridge.translate("Escolher letra"); onClicked: workspace.invoke("pick",{kind:"lyrics_path"}) }
                ActionButton { text: bridge.translate("Ajustar capa"); enabled: !!workspace.values.cover_path; onClicked: workspace.invoke("crop_cover",{}) }
                ActionButton { text: bridge.translate("Desfazer capa"); enabled: !!workspace.values.cover_path; onClicked: workspace.invoke("undo_cover",{}) }
                Label { visible: !!workspace.values.cover_path || !!workspace.values.lyrics_path; width: Math.min(implicitWidth,metadataControls.width); wrapMode: Text.WrapAnywhere; text: [workspace.values.cover_path,workspace.values.lyrics_path].filter(function(value) { return !!value }).join(" · "); color: bridge.palette.muted }
            }
            Flow { Layout.fillWidth: true; spacing: Math.round(8*bridge.spacing)
                ActionButton { text: bridge.translate(workspace.values.previewActive && workspace.values.previewKind === "metadata" && !workspace.values.previewProcessed ? "Parar prévia" : "Ouvir original"); enabled: workspace.values.metadataSources.length > 0; onClicked: workspace.invoke("metadata_preview",{normalized:false}) }
                TaskButton { idleText: bridge.translate(workspace.values.previewActive && workspace.values.previewKind === "metadata" && workspace.values.previewProcessed ? "Parar prévia" : "Ouvir normalizado"); enabled: taskRunning || workspace.values.metadataSources.length > 0; operation: "metadata_preview"; parameters: ({normalized:true}); taskNames: ["normalize_preview"] }
                ActionButton { text: bridge.translate("Parar"); onClicked: workspace.invoke("stop_preview",{}) }
            }
            OndaSwitch { text: bridge.translate("Normalizar volume"); checked: workspace.values.normalize_volume; onToggled: workspace.setOption("normalize_volume",checked) }
            OndaSwitch { text: bridge.translate("Substituir arquivo original"); checked: workspace.values.overwrite_original; onToggled: workspace.setOption("overwrite_original",checked) }
            TaskButton { primary: true; idleText: bridge.translate("Salvar alterações"); enabled: taskRunning || workspace.values.metadataSources.length > 0; operation: "audio_edit"; taskNames: ["audio_edit"] }
                }
                Image { objectName: "metadataArtwork"; visible: !!workspace.values.metadataCover; source: workspace.values.metadataCover || ""; Layout.preferredWidth: Math.min(220,page.availableWidth*0.33); Layout.preferredHeight: Layout.preferredWidth; Layout.alignment: Qt.AlignTop; fillMode: Image.PreserveAspectFit }
                Item { Layout.fillWidth: true }
            }
        }
        Item { Layout.preferredHeight: 20 }
    }
}
