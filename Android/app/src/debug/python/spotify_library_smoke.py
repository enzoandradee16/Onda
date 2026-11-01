"""Account fixture for isolated integration tests; never touches real credentials."""

_saved = None
PLAYLIST = 'A' * 22
TRACK = 'B' * 22


def install():
    global _saved
    import mobile_backend as backend
    from spotify_account import SpotifyAccount

    _saved = backend._spotify_account, backend._spotify_account_root

    class Account:
        connected = True
        playlists = SpotifyAccount.playlists

        def playlist(self, *args, **kwargs):
            result = SpotifyAccount.playlist(self, *args, **kwargs)
            for row in result['tracks']:
                row['_details_checked'] = True
            return result

        def get(self, path, params=None):
            if path == 'me/playlists':
                return dict(
                    items=[
                        dict(
                            id=PLAYLIST,
                            name='Fixture playlist',
                            owner=dict(display_name='Fixture owner'),
                            items=dict(total=1),
                            images=[],
                        )
                    ],
                    next=None,
                )
            if path == 'playlists/' + PLAYLIST:
                return dict(name='Fixture playlist', images=[])
            if path == 'playlists/' + PLAYLIST + '/items':
                return dict(
                    items=[
                        dict(
                            item=dict(
                                id=TRACK,
                                type='track',
                                name='Fixture track',
                                artists=[dict(name='Fixture artist')],
                                album=dict(
                                    name='Fixture album',
                                    images=[],
                                    release_date='2020-01-01',
                                ),
                                duration_ms=180000,
                            )
                        )
                    ],
                    total=1,
                    next=None,
                )
            raise AssertionError(path)

    backend._spotify_account = Account()
    backend._spotify_account_root = backend._root
    return True


def restore():
    import mobile_backend as backend

    if _saved is not None:
        backend._spotify_account, backend._spotify_account_root = _saved
