import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Card {
    objectName:"playbackEffectsCard"
    implicitHeight: Math.max(405,body.implicitHeight+40)
    ColumnLayout {
        id:body
        anchors.fill: parent; anchors.margins: 20; spacing: 12
        OndaSwitch {objectName:"unifiedEffectsEnabled";Layout.fillWidth:true;text:bridge.translate("Efeitos");checked:!!workspace.optionValue(workspace.optionsRevision,"effectsEnabled");onToggled:workspace.setOption("effectsEnabled",checked)}
        ColumnLayout {
            Layout.fillWidth:true;enabled:!!workspace.optionValue(workspace.optionsRevision,"effectsEnabled");spacing:12
            Label {text:bridge.translate("Preset");color:bridge.palette.muted}
            ChoiceBox {
                Layout.fillWidth:true
                property var pairs:[[100,0],[90,0],[75,0],[115,0],[130,0],[120,25],[100,30],[85,25],[75,50]]
                model:["Original","Slowed leve","Slowed intenso","Sped Up leve","Sped Up intenso","Sped Up + Reverb","Só Reverb","Clássico","Atmosférico","Personalizado"]
                currentIndex:{for(let i=0;i<pairs.length;i++)if(Math.round(workspace.optionValue(workspace.optionsRevision,"speed"))===pairs[i][0]&&Math.round(workspace.optionValue(workspace.optionsRevision,"reverb"))===pairs[i][1])return i;return 9}
                onActivated:{if(index<pairs.length){workspace.setOption("speed",pairs[index][0]);workspace.setOption("reverb",pairs[index][1])}}
            }
            Label {objectName:"unifiedSpeedReadout";text:bridge.translate("Velocidade")+" · "+Math.round(speedControl.value)+"%";color:bridge.palette.text}
            OndaSlider {id:speedControl;objectName:"unifiedSpeedSlider";Layout.fillWidth:true;from:50;to:150;value:workspace.optionValue(workspace.optionsRevision,"speed");Accessible.name:bridge.translate("Velocidade");onMoved:if(!pressed)workspace.setOption("speed",value);onPressedChanged:if(!pressed)workspace.setOption("speed",value)}
            Label {text:bridge.translate("Reverb")+" · "+Math.round(reverbControl.value)+"%";color:bridge.palette.text}
            OndaSlider {id:reverbControl;Layout.fillWidth:true;value:workspace.optionValue(workspace.optionsRevision,"reverb");Accessible.name:bridge.translate("Reverb");onMoved:if(!pressed)workspace.setOption("reverb",value);onPressedChanged:if(!pressed)workspace.setOption("reverb",value)}
            OndaSwitch {Layout.fillWidth:true;text:bridge.translate("Manter tom");checked:workspace.optionValue(workspace.optionsRevision,"keep_pitch");onToggled:workspace.setOption("keep_pitch",checked)}
        }
        Item {
            Layout.fillWidth:true;Layout.preferredHeight:8
            OndaProgressBar {
                objectName:"unifiedEffectsPreparationBar"
                anchors.fill:parent
                visible:!!bridge.stateValue(bridge.stateRevision,"effects_pending")
                indeterminate:visible
                Accessible.name:bridge.translate("Efeitos")
            }
        }
        Label {visible:!!bridge.stateValue(bridge.stateRevision,"effects_error");Layout.fillWidth:true;text:bridge.translateError(bridge.stateValue(bridge.stateRevision,"effects_error") || "");wrapMode:Text.Wrap;color:bridge.palette.text}
        OndaSwitch {text:bridge.translate("Exportar trecho");checked:!!workspace.optionValue(workspace.optionsRevision,"exportSegment");onToggled:workspace.setOption("exportSegment",checked)}
        ColumnLayout {visible:!!workspace.optionValue(workspace.optionsRevision,"exportSegment");Layout.fillWidth:true
            Label {text:bridge.translate("Tempos na música original (min:seg)");color:bridge.palette.muted;Layout.fillWidth:true;wrapMode:Text.Wrap}
            RowLayout {Layout.fillWidth:true
                OndaTextField {Layout.fillWidth:true;placeholderText:bridge.translate("Início · 0:00");text:workspace.optionValue(workspace.optionsRevision,"exportStart") || "";onTextEdited:workspace.setOption("exportStart",text);onEditingFinished:{text=workspace.positionText(text);workspace.setOption("exportStart",text)}}
                OndaTextField {Layout.fillWidth:true;placeholderText:bridge.translate("Fim · até terminar");text:workspace.optionValue(workspace.optionsRevision,"exportEnd") || "";onTextEdited:workspace.setOption("exportEnd",text);onEditingFinished:{text=workspace.positionText(text);workspace.setOption("exportEnd",text)}}
            }
        }
        Item {Layout.fillHeight:true}
        RowLayout {
            Layout.fillWidth:true
            ChoiceBox {model:["MP3","M4A","FLAC","WAV"];Layout.preferredWidth:90;Accessible.name:bridge.translate("Formato");currentIndex:model.indexOf(workspace.optionValue(workspace.optionsRevision,"effectFormat"));onActivated:workspace.setOption("effectFormat",currentText)}
            TaskButton {Layout.fillWidth:true;idleText:bridge.translate("Exportar música");enabled:taskRunning||(bridge.stateValue(bridge.stateRevision,"ready"));operation:"unified_effects_export";taskNames:["effects_export"]}
        }
    }
}
