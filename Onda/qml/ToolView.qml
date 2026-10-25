import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
ScrollView {
    property var effectsLyricFrame: ({})
    Timer { interval: 100; running: page.visible; repeat: true; onTriggered: page.effectsLyricFrame=workspace.lyricsFrame() }
    signal lyricsRequested()
    id: page
    property string mode: workspace.currentPage
    readonly property bool effectsSearching: workspace.activity.busy.indexOf("effects_search")>=0 || workspace.activity.busy.indexOf("effects_load")>=0 || workspace.activity.busy.indexOf("effects_queue_info")>=0
    property bool audioOnly: workspace.values.converterSources.some(function(path) { return /\.(mp3|m4a|aac|flac|wav|ogg|opus)$/i.test(path) })
    clip: true
    contentWidth: availableWidth
    ColumnLayout { width: page.availableWidth; spacing: Math.round(18*bridge.spacing)
        Card { visible: page.mode !== "effects"; Layout.fillWidth: true; implicitHeight: sourceBody.implicitHeight+36
            ColumnLayout { id: sourceBody; anchors.fill: parent; anchors.margins: 18; spacing: Math.round(12*bridge.spacing)
                RowLayout { Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
                    ActionButton { primary: true; text: bridge.translate("Escolher arquivo"); onClicked: workspace.invoke("pick",{kind: page.mode === "effects" ? "effects" : page.mode === "images" ? "image" : page.mode}) }
                    Label { Layout.fillWidth: true; wrapMode: Text.Wrap; color: bridge.palette.muted; text: page.mode === "converter" ? workspace.values.converterSources.join(" · ") : page.mode === "metadata" ? workspace.values.metadataSources.join(" · ") : page.mode === "effects" ? workspace.values.effectsSource : workspace.values.imageSource }
                }
                Label { text: bridge.translate(page.mode === "converter" ? "Selecione um ou vários arquivos para converter em lote." : page.mode === "metadata" ? "Edite os metadados e a capa do áudio." : page.mode === "images" ? "Converta imagens ou baixe fotos por link." : "Ajuste os efeitos e exporte a música inteira."); color: bridge.palette.muted; Layout.fillWidth: true; wrapMode: Text.Wrap }
            }
        }
        ColumnLayout { visible: page.mode === "effects"; Layout.fillWidth: true; spacing: 16
            RowLayout { Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
                ActionButton { primary: true; text: bridge.translate("Abrir arquivo"); enabled: !page.effectsSearching; onClicked: workspace.invoke("pick",{kind:"effects"}) }
                OndaTextField {
                    id: effectsQuery; Layout.fillWidth: true; implicitHeight: 44; placeholderText: bridge.translate("Pesquise uma música ou cole um link"); selectByMouse: true
                    color: bridge.palette.text; placeholderTextColor: bridge.palette.muted; font.pixelSize: Math.round(14*bridge.fontScale)
                    background: Rectangle { radius: 8; color: bridge.palette.surface; border.color: effectsQuery.activeFocus ? bridge.palette.accent : bridge.palette.line; border.width: effectsQuery.activeFocus ? 2 : 1 }
                    text: workspace.values.effectsQuery || ""; onTextEdited: workspace.setOption("effectsQuery",text)
                    onAccepted: if(!page.effectsSearching && text.trim().length)workspace.invoke("effects_search",{})
                }
                TaskButton { objectName: "effectsSearchButton"; idleText: bridge.translate("Pesquisar"); primary: true; operation: "effects_search"; taskNames: ["effects_search","effects_load","effects_queue_info"]; enabled: taskRunning || !!(workspace.values.effectsQuery || "").trim() }
            }
            Flow { Layout.fillWidth: true; spacing: 8
                ActionButton {text: bridge.translate("Próxima"); enabled: workspace.values.effectsQueueIndex+1<workspace.values.effectsQueue.length; onClicked: workspace.invoke("effects_next",{})}
                OndaSwitch {text: bridge.translate("Transição gradual"); checked: workspace.preferences.jukebox_gradual_transition; onToggled: workspace.setSetting("jukebox_gradual_transition",checked)}
            }
            Card {
                Layout.fillWidth: true; visible: (workspace.values.effectsResults || []).length>0
                implicitHeight: Math.min(282,effectsResultsList.contentHeight+58); clip: true
                Behavior on implicitHeight { NumberAnimation { duration: bridge.animations ? 160 : 0; easing.type: Easing.OutCubic } }
                RowLayout { anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 8
                    Label { Layout.fillWidth: true; text: bridge.translate("Resultados"); color: bridge.palette.text }
                    PlaybackButton { glyph: "close"; Accessible.name: bridge.translate("Fechar pesquisa"); onClicked: workspace.setOption("effectsResults",[]) }
                }
                ListView {
                    id: effectsResultsList; anchors.fill: parent; anchors.margins: 6; anchors.topMargin: 56; clip: true
                    model: workspace.values.effectsResults || []; ScrollBar.vertical: ScrollBar {}
                    delegate: ItemDelegate {
                        required property var modelData; required property int index
                        width: effectsResultsList.width; height: 84
                        contentItem: RowLayout {
                            Rectangle { Layout.preferredWidth: 64; Layout.preferredHeight: 64; radius: 6; color: bridge.palette.input
                                RoundedArtwork { id: effectResultCover; anchors.fill: parent; source: modelData.cover_url || ""; fillMode: Image.PreserveAspectFit; sourceSize.width: 128; sourceSize.height: 128; asynchronous: true }
                                Label { anchors.centerIn: parent; visible: effectResultCover.status !== Image.Ready; text: "♪"; color: bridge.palette.muted }
                            }
                            ColumnLayout { Layout.fillWidth: true; Layout.minimumWidth: 0; spacing: 4
                                Label { Layout.fillWidth: true; text: modelData.title; color: bridge.palette.text; elide: Text.ElideRight }
                                Label { Layout.fillWidth: true; text: (modelData.artists || []).join(", "); color: bridge.palette.muted; elide: Text.ElideRight }
                                Label { Layout.fillWidth: true; text: modelData.album || ""; color: bridge.palette.muted; elide: Text.ElideRight }
                            }
                            ActionButton { text: bridge.translate("Adicionar à fila"); enabled: workspace.activity.busy.indexOf("effects_load")<0; onClicked: {workspace.invoke("effects_enqueue_result",{index:index});workspace.setOption("effectsQueueOpen",true)} }
                        }
                        enabled: workspace.activity.busy.indexOf("effects_load")<0
                        onClicked: workspace.invoke("effects_load",{index:index})
                    }
                }
            }
            OndaProgressBar { objectName: "effectsSearchProgress"; Layout.fillWidth: true; visible: page.effectsSearching; from: 0; to: 100; indeterminate: true }
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
                    text: modelData.source.split(/[\\/]/).pop()+": "+((modelData.error ? bridge.translateError(modelData.error) : "") || (modelData.silent ? bridge.translate("Arquivo inteiramente silencioso; recorte automático indisponível.") : bridge.translate("Silêncio inicial")+": "+modelData.leading.toFixed(2)+" s · "+bridge.translate("Silêncio final")+": "+modelData.trailing.toFixed(2)+" s"))
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
                        RoundedArtwork { id: effectsArtwork; objectName: "effectsArtwork"; anchors.fill: parent; source: workspace.values.effectsCover || ""; sourceSize.width: 292; sourceSize.height: 292; fillMode: Image.PreserveAspectFit }
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

            RowLayout { Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
                Label { text: bridge.translate("Preset"); color: bridge.palette.text }
                ChoiceBox { id: effectsPreset; objectName: "effectsPreset"; Layout.preferredWidth: Math.round(240*bridge.fontScale); Layout.maximumWidth: Math.max(80,page.availableWidth-80); model: ["Original","Slowed leve","Slowed intenso","Sped Up leve","Sped Up intenso","Sped Up + Reverb","Só Reverb","Clássico","Atmosférico"]
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
            AnimatedLyric { visible: workspace.preferences.synced_lyrics; text: effectsLyricFrame.text || ""; lineKey: String(effectsLyricFrame.active); textFormat: Text.RichText; Layout.fillWidth: true }
            Label { visible: !!workspace.values.effectLyricsName; text: workspace.values.effectLyricsName || ""; color: bridge.palette.muted; Layout.fillWidth: true; elide: Text.ElideMiddle }
            Card { Layout.fillWidth: true; implicitHeight: exportRow.implicitHeight+32
                RowLayout { id: exportRow; anchors.fill: parent; anchors.margins: 16; spacing: 12
                    Label { text: bridge.translate("Exportar música"); color: bridge.palette.text; Layout.fillWidth: true }
                    ChoiceBox { model: ["MP3","M4A","FLAC","WAV"]; onActivated: workspace.setOption("effectFormat",currentText) }
                    TaskButton { primary: true; idleText: bridge.translate("Exportar música"); enabled: taskRunning || !!workspace.values.effectsSource; operation: "effects_export"; taskNames: ["effects_export"] }
                }
            }
        }
        ColumnLayout { visible: page.mode === "images"; Layout.fillWidth: true; spacing: Math.round(14*bridge.spacing)
            OndaTextField { Layout.fillWidth: true; placeholderText: bridge.translate("Link da imagem ou publicação"); text: workspace.values.imageUrl; onTextEdited: workspace.setOption("imageUrl",text) }
            RowLayout { Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
                OptionField { Layout.fillWidth: true; settings: true; field: ({key:"image_format",label:"Formato",kind:"select",choices:["Original","JPG","PNG","WebP","SVG"]}) }
                OptionField { Layout.fillWidth: true; settings: true; field: ({key:"image_size",label:"Tamanho máximo",kind:"select",choices:["Original","Até 1920 × 1080","Até 1280 × 720","Até 1080 × 1080","Personalizado"]}) }
                OptionField { visible: workspace.preferences.image_size === "Personalizado"; settings: true; field: ({key:"image_width",label:"Largura",kind:"text"}) }
                OptionField { visible: workspace.preferences.image_size === "Personalizado"; settings: true; field: ({key:"image_height",label:"Altura",kind:"text"}) }
            }
            OndaSwitch { text: bridge.translate("Manter proporção"); checked: workspace.preferences.image_keep_ratio; onToggled: workspace.setSetting("image_keep_ratio",checked) }
            RowLayout { spacing: Math.round(10*bridge.spacing); TaskButton { idleText: bridge.translate("Visualizar"); operation: "image_preview"; taskNames: ["image_preview"] } TaskButton { primary: true; idleText: bridge.translate("Exportar / baixar"); operation: "image_export"; taskNames: ["image_export"] } }
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
            Flow { Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
                ActionButton { text: bridge.translate("Escolher capa"); onClicked: workspace.invoke("pick",{kind:"cover_path"}) }
                ActionButton { text: bridge.translate("Ajustar capa"); enabled: !!workspace.values.cover_path; onClicked: workspace.invoke("crop_cover",{}) }
                ActionButton { text: bridge.translate("Desfazer capa"); enabled: !!workspace.values.cover_path; onClicked: workspace.invoke("undo_cover",{}) }
                Label { visible: !!workspace.values.cover_path || !!workspace.values.lyrics_path; width: Math.min(implicitWidth,metadataControls.width); wrapMode: Text.WrapAnywhere; text: [workspace.values.cover_path,workspace.values.lyrics_path].filter(function(value) { return !!value }).join(" · "); color: bridge.palette.muted }
            }
            Flow { Layout.fillWidth: true; spacing: Math.round(10*bridge.spacing)
                ActionButton { text: bridge.translate(workspace.values.previewActive && workspace.values.previewKind === "metadata" && !workspace.values.previewProcessed ? "Parar prévia" : "Ouvir original"); enabled: workspace.values.metadataSources.length > 0; onClicked: workspace.invoke("metadata_preview",{normalized:false}) }
                TaskButton { idleText: bridge.translate(workspace.values.previewActive && workspace.values.previewKind === "metadata" && workspace.values.previewProcessed ? "Parar prévia" : "Ouvir normalizado"); enabled: taskRunning || workspace.values.metadataSources.length > 0; operation: "metadata_preview"; parameters: ({normalized:true}); taskNames: ["normalize_preview"] }
                ActionButton { text: bridge.translate("Parar"); onClicked: workspace.invoke("stop_preview",{}) }
            }
            OndaSwitch { text: bridge.translate("Normalizar volume"); checked: workspace.values.normalize_volume; onToggled: workspace.setOption("normalize_volume",checked) }
            OndaSwitch { text: bridge.translate("Substituir arquivo original"); checked: workspace.values.overwrite_original; onToggled: workspace.setOption("overwrite_original",checked) }
            TaskButton { primary: true; idleText: bridge.translate("Salvar alterações"); enabled: taskRunning || workspace.values.metadataSources.length > 0; operation: "audio_edit"; taskNames: ["audio_edit"] }
                }
                RoundedArtwork { objectName: "metadataArtwork"; visible: !!workspace.values.metadataCover; source: workspace.values.metadataCover || ""; Layout.preferredWidth: Math.min(220,page.availableWidth*0.33); Layout.preferredHeight: Layout.preferredWidth; Layout.alignment: Qt.AlignTop; fillMode: Image.PreserveAspectFit }
                Item { Layout.fillWidth: true }
            }
        }
        Item { Layout.preferredHeight: 20 }
    }
}
