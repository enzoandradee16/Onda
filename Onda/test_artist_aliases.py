import unittest
from matching import score_candidate,select_candidate
from artist_aliases import artist_overlap
from record_identity import catalog_identity

RECORD=dict(title='Garota de Ipanema',artists=['Antônio Carlos Jobim'],album='Inédito',duration_ms=242760,track_number=5)
VIDEO=dict(id='8mcsaEqrbfU',title='Tom Jobim | Garota de Ipanema | Inédito',channel='Biscoito Fino',duration=243)

class ArtistAliasesTests(unittest.TestCase):
    def test_real_example_accepts_reviewed_alias_and_keeps_provenance(self):
        self.assertGreater(score_candidate(RECORD,VIDEO),.99)
        selected=select_candidate(RECORD,[VIDEO],prefer_best=True)
        self.assertEqual(selected['artist_alias']['matched_alias'],'Tom Jobim')
        self.assertIn('jobim.org',selected['artist_alias']['source_url'])
        self.assertEqual(RECORD['artists'],['Antônio Carlos Jobim'])
    def test_duration_and_recording_version_guards_still_apply(self):
        for changes in ({'duration':161},{'duration':288},{'title':VIDEO['title']+' Live'},{'title':VIDEO['title']+' Remix'},{'title':VIDEO['title']+' Cover'}):
            self.assertIsNone(score_candidate(RECORD,dict(VIDEO,**changes)))
    def test_surname_or_similar_artist_is_not_an_alias(self):
        for name in ('Jobim','Tom Jones','João Jobim'):
            self.assertLess(artist_overlap(RECORD['artists'][0],set(name.lower().split())),.65)
        self.assertIsNone(score_candidate(RECORD,dict(VIDEO,title='Tom Jones - Garota de Ipanema',channel='Tom Jones')))
    def test_catalog_alias_still_requires_album_track_duration(self):
        other=dict(RECORD,artists=['Tom Jobim'])
        self.assertEqual(catalog_identity(RECORD,other),'album-track')
        self.assertIsNone(catalog_identity(RECORD,dict(other,track_number=6)))
        self.assertIsNone(catalog_identity(RECORD,dict(other,duration_ms=161000)))

if __name__=='__main__':unittest.main()
