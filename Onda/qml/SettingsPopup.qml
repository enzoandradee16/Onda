import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Popup {
    id: popup
    objectName: "settingsPopup"
    parent: Overlay.overlay; anchors.centerIn: parent; width: Math.min(1050,parent.width-60); height: Math.min(780,parent.height-50)
    padding: 24; modal: true; focus: true
    onOpened: workspace.invoke("tools_status",{})
    property string category: "Geral"
    readonly property int actionColumns: settingsScroll.availableWidth >= 560*bridge.fontScale ? 2 : 1
    readonly property bool searching: search.text.trim().length>0
    readonly property int resultCount: workspace.settingsFields.filter(function(field) {
        return (field.key!=="pure_black_separators" || workspace.preferences.theme_mode==="Preto puro") && (field.key!=="pure_light_borders" || workspace.preferences.theme_mode==="Claro puro") && workspace.settingsSearchMatches(search.text,field)
    }).length
    background: Card {}
    enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: bridge.animations ? 150 : 0 } }
    ResetPopup { id: reset }
    contentItem: ColumnLayout { spacing: Math.round(16*bridge.spacing)
        RowLayout { Layout.fillWidth: true
            ColumnLayout { Layout.fillWidth: true; spacing: 4
                Label { text: bridge.translate("Configurações"); font.pixelSize: Math.round(26*bridge.fontScale); color: bridge.palette.text; Layout.fillWidth: true }
                Label { objectName: "settingsAppVersion"; text: "ONDA " + workspace.appVersion; color: bridge.palette.muted; font.pixelSize: Math.round(13*bridge.fontScale) }
            }
            ActionButton { text: bridge.translate("Pronto"); primary: true; onClicked: popup.close() }
        }
        OndaTextField { id: search; objectName: "settingsSearch"; Layout.fillWidth: true; placeholderText: bridge.translate("Pesquisar configurações") }
        RowLayout { Layout.fillWidth: true; Layout.fillHeight: true; spacing: Math.round(22*bridge.spacing)
            ColumnLayout { Layout.preferredWidth: 160; Layout.maximumWidth: 160; Layout.minimumWidth: 160; Layout.alignment: Qt.AlignTop; spacing: Math.round(5*bridge.spacing)
                Repeater { model: ["Geral","Aparência","Downloads","Imagens","Áudio","Contas","Ferramentas","Desempenho"]
                    ActionButton { required property string modelData; Layout.fillWidth: true; text: bridge.translate(modelData); primary: !popup.searching && popup.category === modelData; onClicked: { popup.category=modelData;search.clear() } }
                }
                Item { Layout.fillHeight: true }
            }
            OndaScrollView {
                id: settingsScroll

                property var scrollTopButton: ScrollToTop { target: settingsScroll.contentItem; viewport: settingsScroll }
                Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumWidth: 0; Layout.preferredWidth: 700
                clip: true; contentWidth: availableWidth
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ColumnLayout { width: settingsScroll.availableWidth; spacing: Math.round(18*bridge.spacing)
                    Label {objectName: "settingsSearchEmpty"; visible: popup.searching && popup.resultCount===0; text: bridge.translate("Nenhuma configuração encontrada."); color: bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true}
                    Repeater { model: workspace.settingsFields
                        OptionField { required property var modelData; Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.maximumWidth: parent.width; field: modelData; settings: true; showCategory: popup.searching; onCategoryRequested: function(category) {popup.category=category;search.clear()}; visible: (modelData.key !== "pure_black_separators" || workspace.preferences.theme_mode === "Preto puro") && (modelData.key !== "pure_light_borders" || workspace.preferences.theme_mode === "Claro puro") && (popup.searching ? workspace.settingsSearchMatches(search.text,modelData) : modelData.category === popup.category) }
                    }
                    ColumnLayout { visible: popup.category === "Geral" && !popup.searching; Layout.fillWidth: true; spacing: 8
                        Label { text: bridge.translate("Sobre o ONDA"); color: bridge.palette.text; font.weight: Font.DemiBold }
                        Label { text: bridge.translate("Versão, atualizações e licenças"); color: bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        ColumnLayout {visible:!!workspace.optionValue(workspace.optionsRevision,"appUpdate") && !!workspace.optionValue(workspace.optionsRevision,"appUpdate").available;Layout.fillWidth:true
                            Label {text:workspace.optionValue(workspace.optionsRevision,"appUpdate") ? workspace.optionValue(workspace.optionsRevision,"appUpdate").message : "";color:bridge.palette.text;wrapMode:Text.Wrap;Layout.fillWidth:true}
                            Label {text:workspace.optionValue(workspace.optionsRevision,"appUpdate") ? workspace.optionValue(workspace.optionsRevision,"appUpdate").notes || "" : "";color:bridge.palette.muted;wrapMode:Text.Wrap;Layout.fillWidth:true;maximumLineCount:8;elide:Text.ElideRight}
                            Label {visible:!!workspace.optionValue(workspace.optionsRevision,"appUpdate") && workspace.optionValue(workspace.optionsRevision,"appUpdate").size>0;text:workspace.optionValue(workspace.optionsRevision,"appUpdate") ? (workspace.optionValue(workspace.optionsRevision,"appUpdate").size/1048576).toFixed(1)+" MB" : "";color:bridge.palette.muted}
                            TaskButton {idleText:bridge.translate("Baixar nova versão");operation:"app_update_download";taskNames:["app_update_download"]}
                        }
                        GridLayout { Layout.fillWidth: true; columns: popup.actionColumns; uniformCellWidths: true; columnSpacing: 8; rowSpacing: 8
                            TaskButton { Layout.fillWidth: true; Layout.minimumWidth: 0; idleText: bridge.translate("Verificar atualização do ONDA"); operation: "app_update"; taskNames: ["app_update"] }
                            ActionButton { Layout.fillWidth: true; Layout.minimumWidth: 0; text: bridge.translate("Licenças e fontes"); onClicked: workspace.invoke("open_file", {path: workspace.licensePath}) }
                        }
                    }
                    GridLayout { visible: popup.category === "Geral" && !popup.searching; Layout.fillWidth: true; columns: popup.actionColumns; uniformCellWidths: true; columnSpacing: 8; rowSpacing: 8
                        Repeater { model: [{name:"Exportar configurações…",key:"export_settings"},{name:"Importar configurações…",key:"import_settings"}]
                            TaskButton { required property var modelData; Layout.fillWidth: true; Layout.minimumWidth: 0; objectName: modelData.key; idleText: bridge.translate(modelData.name); operation: modelData.key }
                        }
                        ActionButton { objectName: "settingsRestoreButton"; Layout.fillWidth: true; Layout.columnSpan: popup.actionColumns; text: bridge.translate("Restaurar configurações…"); onClicked: reset.open() }
                    }
                    ColumnLayout { visible: popup.category === "Aparência" && !popup.searching; Layout.fillWidth: true
                        Label { text: bridge.translate("Ordem das categorias"); color: bridge.palette.text; font.pixelSize: Math.round(19*bridge.fontScale) }
                        Label { text: bridge.translate("Escolha qual categoria aparece primeiro na barra lateral."); color: bridge.palette.muted; wrapMode: Text.Wrap; Layout.fillWidth: true }
                        Repeater { model: workspace.navigation.filter(function(row){return !!row.group})
                            RowLayout { required property var modelData; required property int index; Layout.fillWidth: true; spacing: 10
                                Label { text: (index+1)+"."; color: bridge.palette.muted; Layout.preferredWidth: 22 }
                                Label { Layout.fillWidth: true; text: bridge.translate(modelData.groupKey==="library" ? "Biblioteca" : "Ferramentas"); color: bridge.palette.text; font.weight: Font.DemiBold }
                                PlaybackButton { objectName: "moveCategoryUp_"+modelData.groupKey; glyph: "up"; enabled: !!modelData.canMoveUp; Accessible.name: bridge.translate("Mover para cima")+": "+bridge.translate(modelData.group || ""); ToolTip.visible: hovered; ToolTip.text: Accessible.name; onClicked: workspace.invoke("tab_group_move",{key:modelData.groupKey,direction:-1}) }
                                PlaybackButton { objectName: "moveCategoryDown_"+modelData.groupKey; glyph: "down"; enabled: !!modelData.canMoveDown; Accessible.name: bridge.translate("Mover para baixo")+": "+bridge.translate(modelData.group || ""); ToolTip.visible: hovered; ToolTip.text: Accessible.name; onClicked: workspace.invoke("tab_group_move",{key:modelData.groupKey,direction:1}) }
                            }
                        }
                        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; Layout.topMargin: 12; Layout.bottomMargin: 12; color: bridge.palette.line }
                        Label { text: bridge.translate("Ordem e visibilidade das abas"); color: bridge.palette.text; font.pixelSize: Math.round(19*bridge.fontScale) }
                        Repeater { model: workspace.navigation
                            ColumnLayout { required property var modelData; Layout.fillWidth: true; spacing: 6
                                RowLayout { visible: !!modelData.group; Layout.fillWidth: true; Layout.topMargin: 12; Layout.bottomMargin: 4
                                    Label { objectName: "appearanceTabGroup"; Layout.fillWidth: true; text: modelData.group ? bridge.translate(modelData.groupKey==="library" ? "Biblioteca" : "Ferramentas") : ""; color: bridge.palette.muted; font.pixelSize: Math.round(13*bridge.fontScale); font.weight: Font.DemiBold }
                                }
                                RowLayout { visible: !!modelData.key; Layout.fillWidth: true
                                    CheckBox { checked: workspace.hiddenTabs.indexOf(modelData.key) < 0; enabled: ["catalog","downloads","queue"].indexOf(modelData.key) < 0; onToggled: workspace.invoke("toggle_tab",{key:modelData.key}) }
                                    Label { Layout.fillWidth: true; text: modelData.key ? workspace.pageLabel(modelData.key) : ""; color: bridge.palette.text }
                                    PlaybackButton { glyph: "up"; enabled: !!modelData.canMoveUp; Accessible.name: bridge.translate("Mover para cima"); onClicked: workspace.invoke("tab_move",{key:modelData.key,direction:-1}) }
                                    PlaybackButton { glyph: "down"; enabled: !!modelData.canMoveDown; Accessible.name: bridge.translate("Mover para baixo"); onClicked: workspace.invoke("tab_move",{key:modelData.key,direction:1}) }
                                }
                            }
                        }
                        ActionButton { text: bridge.translate("Restaurar ordem das abas"); onClicked: workspace.invoke("reset_tab_order",{}) }
                    }
                    GridLayout { objectName: "settingsAccountActions"; columns: popup.actionColumns; uniformCellWidths: true; columnSpacing: 8; rowSpacing: 8; visible: popup.category === "Contas" && !popup.searching; Layout.fillWidth: true;
                        Repeater { model: [{name:"Remover credenciais",key:"forget_credentials"},{name:workspace.activityValue(workspace.statusRevision,"spotify") ? "Desconectar Spotify" : "Conectar Spotify",key:workspace.activityValue(workspace.statusRevision,"spotify") ? "spotify_disconnect" : "spotify_connect"},{name:"Abrir Spotify Developers",key:"spotify_developers"}].filter(function(action) { return action.key !== "forget_credentials" || workspace.activityValue(workspace.statusRevision,"spotify") })
                            TaskButton { required property var modelData; Layout.fillWidth: true; Layout.minimumWidth: 0; objectName: modelData.key; idleText: bridge.translate(modelData.name); operation: modelData.key }
                        }
                        ActionButton { Layout.fillWidth: true; Layout.minimumWidth: 0; text: bridge.translate(workspace.preferences.youtube_cookies ? "Remover cookies do YouTube" : "Importar cookies do YouTube"); onClicked: { if (workspace.preferences.youtube_cookies) workspace.setSetting("youtube_cookies",""); else workspace.invoke("pick",{kind:"youtube_cookies"}) } }
                        ActionButton { Layout.fillWidth: true; Layout.minimumWidth: 0; text: bridge.translate(workspace.preferences.social_cookies ? "Remover cookies.txt" : "Importar cookies.txt"); onClicked: { if (workspace.preferences.social_cookies) workspace.setSetting("social_cookies",""); else workspace.invoke("pick",{kind:"social_cookies"}) } }
                        ActionButton { Layout.fillWidth: true; Layout.minimumWidth: 0; text: bridge.translate(workspace.preferences.instagram_cookies ? "Atualizar sessão do Instagram" : "Conectar ao Instagram"); onClicked: workspace.invoke("instagram_connect",{}) }
                        ActionButton { Layout.fillWidth: true; Layout.minimumWidth: 0; visible: !!workspace.preferences.instagram_cookies; text: bridge.translate("Desconectar Instagram"); onClicked: workspace.invoke("instagram_disconnect",{}) }
                    }
                    ColumnLayout { visible: popup.category === "Ferramentas" && !popup.searching; Layout.fillWidth: true; spacing: Math.round(12*bridge.spacing)
                        ToolStatusPanel {Layout.fillWidth:true}
                        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: bridge.translate("Verificar consulta as versões instaladas; Atualizar instala novas versões dos componentes."); color: bridge.palette.muted }
                        GridLayout { objectName: "settingsToolActions"; Layout.fillWidth: true; columns: popup.actionColumns; uniformCellWidths: true; columnSpacing: 8; rowSpacing: 8
                            Repeater { model: [{name:"Preparar FFmpeg",key:"prepare_tools"},{name:"Verificar ferramentas",key:"verify_tools"},{name:"Atualizar ferramentas",key:"update_tools"}]
                                TaskButton { required property var modelData; Layout.fillWidth: true; Layout.minimumWidth: 0; objectName: modelData.key; idleText: bridge.translate(modelData.name); operation: modelData.key }
                            }
                        }
                    }
                    ColumnLayout { visible: popup.category === "Desempenho" && !popup.searching; Layout.fillWidth: true; spacing: 8
                        Label { text: bridge.translate("Arquivos temporários e cache"); color: bridge.palette.text; font.weight: Font.DemiBold }
                        Label { Layout.fillWidth: true; wrapMode: Text.Wrap; text: bridge.translate("Os downloads salvos na pasta de destino não são removidos."); color: bridge.palette.muted }
                        GridLayout { objectName: "settingsCacheActions"; Layout.fillWidth: true; columns: popup.actionColumns; uniformCellWidths: true; columnSpacing: 8; rowSpacing: 8
                            TaskButton { objectName: "cache_info"; Layout.fillWidth: true; Layout.minimumWidth: 0; idleText: bridge.translate("Atualizar tamanho do cache"); operation: "cache_info" }
                            TaskButton { objectName: "cache_clear"; Layout.fillWidth: true; Layout.minimumWidth: 0; idleText: bridge.translate("Limpar cache"); operation: "cache_clear" }
                        }
                    }
                    Item { Layout.preferredHeight: 20 }
                }
            }
        }
    }
}
