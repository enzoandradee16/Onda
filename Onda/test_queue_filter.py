import unittest
from queue_filter import matches


class QueueFilterTests(unittest.TestCase):
    def test_search_is_accent_insensitive_and_includes_metadata(self):
        job = {
            'state': 'Na fila',
            'queue_info': {
                'artists': ['Antônio Carlos Jobim'],
                'album': 'Wave',
                'platform': 'Spotify',
            },
        }
        self.assertTrue(matches(job, 'Garota de Ipanema', 'antonio wave', 'Todos'))
        self.assertFalse(matches(job, 'Garota de Ipanema', 'antonio missing', 'Todos'))
        self.assertFalse(matches(job, 'Garota de Ipanema', '', 'Com falha'))
        self.assertTrue(matches(job, 'Garota de Ipanema', '', 'Pendentes'))
        self.assertTrue(
            matches({'state': 'Baixando'}, 'トーキョー', 'トーキョー', 'Em andamento')
        )
