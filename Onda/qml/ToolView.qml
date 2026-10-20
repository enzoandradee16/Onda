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
            RowLayout {
                TaskButton { objectName: "convertButton"; primary: true; idleText: bridge.translate("Converter em lote"); enabled: taskRunning || workspace.values.converterSources.length > 0; operation: "convert"; taskNames: ["convert"] }
                ActionButton { visible: workspace.values.converterSources.length > 0; text: bridge.translate("Prévia do original"); onClicked: workspace.invoke("open_file",{path:workspace.values.converterSources[0]}) }
            }
        }
        ColumnLayout { visible: page.mode === "effects"; Layout.fillWidth: true; spacing: Math.round(18*bridge.spacing)
            RowLayout { Layout.fillWidth: true
                Label { text: bridge.translate("Preset"); color: bridge.palette.text }
                ComboBox { model: ["Original","Slowed leve","Slowed intenso","Sped Up leve","Sped Up intenso","Sped Up + Reverb","Só Reverb","Clássico","Atmosférico"]
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
                ActionButton { text: bridge.translate("Parar"); onClicked: workspace.invoke("stop_preview",{}) }
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
            Image { source: workspace.values.imagePreview; Layout.fillWidth: true; Layout.preferredHeight: 360; fillMode: Image.PreserveAspectFit; asynchronous: true; cache: false }
        }
        ColumnLayout { visible: page.mode === "metadata"; Layout.fillWidth: true; spacing: Math.round(14*bridge.spacing)
            Image { objectName: "metadataArtwork"; visible: !!workspace.values.metadataCover; source: workspace.values.metadataCover || ""; Layout.preferredWidth: 220; Layout.preferredHeight: 220; fillMode: Image.PreserveAspectFit }
            GridLayout { columns: 2; Layout.fillWidth: true; columnSpacing: 16; rowSpacing: 14
                Repeater { model: [{key:"title",label:"Título"},{key:"artists",label:"Artista"},{key:"album",label:"Álbum"},{key:"genre",label:"Gênero"},{key:"release_date",label:"Data de lançamento"},{key:"track_number",label:"Número da faixa"},{key:"disc_number",label:"Disco"}]
                    ColumnLayout { required property var modelData; Layout.fillWidth: true
                        RowLayout {
                            CheckBox { visible: workspace.values.metadataSources.length > 1; checked: workspace.values.metadataFields[modelData.key] || false; onToggled: { var values=workspace.values.metadataFields;values[modelData.key]=checked;workspace.setOption("metadataFields",values) } }
                            Label { text: bridge.translate(modelData.label); color: bridge.palette.muted }
                        }
                        OndaTextField { Layout.fillWidth: true; text: Array.isArray(workspace.values.metadata[modelData.key]) ? workspace.values.metadata[modelData.key].join(", ") : workspace.values.metadata[modelData.key] || ""; onEditingFinished: { var record=workspace.values.metadata; record[modelData.key]=text;workspace.setOption("metadata",record) } }
                    }
                }
            }
            Flow { Layout.fillWidth: true; spacing: Math.round(8*bridge.spacing)
                ActionButton { text: bridge.translate("Escolher capa"); onClicked: workspace.invoke("pick",{kind:"cover_path"}) }
                ActionButton { text: bridge.translate("Escolher letra"); onClicked: workspace.invoke("pick",{kind:"lyrics_path"}) }
                ActionButton { text: bridge.translate("Ajustar capa"); enabled: !!workspace.values.cover_path; onClicked: workspace.invoke("crop_cover",{}) }
                ActionButton { text: bridge.translate("Desfazer capa"); enabled: !!workspace.values.cover_path; onClicked: workspace.invoke("undo_cover",{}) }
                Label { text: workspace.values.cover_path+" · "+workspace.values.lyrics_path; color: bridge.palette.muted }
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
        Item { Layout.preferredHeight: 20 }
    }
}
