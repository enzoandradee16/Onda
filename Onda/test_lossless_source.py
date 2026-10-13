from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import requests
from lossless_source import rank_matches, choose_match, fetch_file

RECORD={'title':'Carefree','artists':['Kevin MacLeod'],'duration_ms':206466,'isrc':'USUAN1400037'}

def row(identity='123', **extra):
    return dict({'id':identity,'title':'Carefree','artistNames':['Kevin MacLeod'],
                 'duration':206466,'isrc':'USUAN1400037','playable':True},**extra)

class MatchingTests(unittest.TestCase):
    def test_wrong_artist_version_duration_and_unplayable_are_rejected(self):
        values=[row(artistNames=['Other Artist']),row(title='Carefree - Slowed'),
                row(duration=400000),row(playable=False),row(identity='../file'),{},None]
        self.assertEqual(rank_matches(RECORD,values),[])

    def test_exact_isrc_first_and_duplicates_removed(self):
        values=[row('1',isrc='OTHER'),row('2'),row('3')]
        ranked=rank_matches(RECORD,values)
        self.assertEqual([r['id'] for r in ranked],['2','1'])
        self.assertEqual(ranked[0]['source_url'],'https://tracks.monochrome.st/track/2')

    def test_ambiguous_requires_choice_except_when_automatic(self):
        ranked=rank_matches(RECORD,[row('1',isrc='ONE'),row('2',isrc='TWO')])
        choose=Mock(return_value=ranked[1])
        chosen=choose_match(RECORD,ranked,choose,{})
        self.assertEqual(chosen['id'],'2')
        self.assertEqual(choose.call_args.args[0]['_audio_provider'],'Monochrome')
        choose.reset_mock()
        chosen=choose_match(RECORD,ranked,choose,{'auto_match':True,'confirm_version':True})
        self.assertEqual(chosen['id'],'1')
        choose.assert_not_called()

    def test_missing_flac_explains_unavailability(self):
        with self.assertRaisesRegex(ValueError,'Nenhum FLAC compatível'):
            choose_match(RECORD,[],Mock(),{})

class Response:
    def __init__(self,status=200,data=b'fLaCtest',length=None):
        self.status_code=status
        self.data=data
        self.headers={'Content-Length':str(len(data) if length is None else length)}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def raise_for_status(self):
        if self.status_code>=400:raise requests.HTTPError(str(self.status_code))
    def iter_content(self,size):
        yield self.data[:2]
        yield self.data[2:]

class TransferTests(unittest.TestCase):
    def test_transfer_progress_and_file(self):
        session=Mock();session.get.return_value=Response()
        emit=Mock()
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/'track.flac'
            fetch_file(session,'https://tracks.monochrome.st/track/1',target,emit,'Song')
            self.assertEqual(target.read_bytes(),b'fLaCtest')
        self.assertFalse(session.get.call_args.kwargs['allow_redirects'])
        self.assertEqual(emit.call_args.args[0],'progress')
        self.assertEqual(emit.call_args.kwargs['status'],'finished')

    def test_access_denial_is_not_retried(self):
        session=Mock();session.get.return_value=Response(403)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError,'recusou'):
                fetch_file(session,'https://tracks.monochrome.st/track/1',Path(folder)/'a.flac',Mock(),'Song')
        self.assertEqual(session.get.call_count,1)

    def test_partial_or_non_flac_is_not_completed(self):
        for response in (Response(data=b'<html>denied</html>'),Response(length=999)):
            session=Mock();session.get.return_value=response;emit=Mock()
            with tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(ValueError):
                    fetch_file(session,'https://tracks.monochrome.st/track/1',Path(folder)/'a.flac',emit,'Song')
            self.assertFalse(any(c.kwargs.get('status')=='finished' for c in emit.call_args_list))

if __name__=='__main__':unittest.main()
