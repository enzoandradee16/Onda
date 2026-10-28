"""Presentation-only state names; persisted queue identifiers stay unchanged."""
LABELS = {'Na fila':'Pendente', 'Pendente':'Pendente', 'pending':'Aguardando preparação',
          'Em andamento':'Baixando', 'Baixando':'Baixando', 'Falhou':'Falhou', 'Erro':'Falhou',
          'Cancelado':'Cancelado', 'Pausado':'Pausado', 'Concluído':'Concluído',
          'Aguardando escolha':'Aguardando confirmação', 'ready':'Pronta para reproduzir',
          'Pronta':'Pronta para reproduzir', 'preparing':'Preparando', 'Preparando':'Preparando',
          'error':'Falha na preparação'}


def label(state):
    return LABELS.get(state, state)


def can_act(state, action):
    state=label(state)
    return state in {'pause':{'Pendente','Baixando'},'resume':{'Pendente','Pausado','Cancelado'},
                     'retry':{'Falhou','Cancelado'},'cancel':{'Pendente','Baixando','Pausado'}}.get(action,set())
