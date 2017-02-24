import sys, os, time, hashlib, StringIO, bencode
from urllib2 import urlparse


class Torrent:
    """A class representing a Torrent."""

    def __init__(self, path, filename=None, announce="", announcelist=None,
                 comment=None, httpseeds=None):
        """Create a Torrent.

        Parameters
        ----------
        path : str
            the full path to the torrent content
        filename : str, optional
            the name of the resulting Torrent
        announce : str, optional
            the URL of the tracker
        announcelist : list, optional
            a list of lists with announce URLs
        comment : str, optional
            the text comment for the the torrent

        """

        self.path = os.path.abspath(path)
        self.filename = filename
        self.announce = announce
        self.announcelist = announcelist
        self.comment = comment
        self.httpseeds = httpseeds
        self.piece_length = 262144
        self.tdict = None
        self.info_hash = None

        self.tdict = {
            'announce': self.announce,
            'creation date': int(time.time()),
            'info': {
                'piece length': self.piece_length
                }
            }

        if self.comment is not None:
            self.tdict.update({'comment': self.comment})

        if self.httpseeds is not None:
            if not isinstance(self.httpseeds, list):
                raise TypeError('httpseeds must be a list')
            else:
                self.tdict.update({'httpseeds': self.httpseeds})
        if self.announcelist is not None:
            if not isinstance(self.announcelist, list):
                raise TypeError('announcelist must be a list of lists')
            if False in [isinstance(l, list) for l in self.announcelist]:
                raise TypeError('announcelist must be a list of lists')
            if False in [bool(urlparse.urlparse(f[0]).scheme) for f in self.announcelist]:
                raise ValueError('No schema present for url')
            else:
                self.tdict.update({'announce-list': self.announcelist})

        info_pieces = ''
        data = ''
        if path.endswith('/'):
            path = path[:-1]
        real_path = os.path.abspath(path)
        md5sum = hashlib.md5()

        if not os.path.isdir(path):
            length = 0
            with open(real_path, "rb") as fn:
                while True:
                    filedata = fn.read(self.piece_length)
                    if len(filedata) == 0:
                        break
                    length += len(filedata)
                    data += filedata
                    if len(data) >= self.piece_length:
                        info_pieces += hashlib.sha1(data[:self.piece_length]).digest()
                        data = data[self.piece_length:]
                    md5sum.update(filedata)
            self.tdict['info'].update(
                {
                    'length': length,
                    'md5sum': md5sum.hexdigest() # FIXME md5sum of what?
                }
            )

        else:
            to_get = []
            file_list = []
            for root, subdirs, files in os.walk(real_path):
                for f in files:
                    sub_path = os.path.relpath(os.path.join(root, f), start=real_path).split('/')
                    sub_path = [str(p) for p in sub_path]
                    to_get.append(sub_path)
            d = {hashlib.md5('/'.join(x)).hexdigest() : x for x in to_get}
            keys = sorted(d.keys())
            for key in keys:
                path_list = d[key]
                length = 0
                file_path = ('/').join(path_list)
                file_dict = {
                    'path': path_list,
                    'length': len(open(os.path.join(path, file_path), "rb").read())
                }
                with open(os.path.join(path, file_path), "rb") as fn:
                    while True:
                        filedata = fn.read(self.piece_length)
                        if len(filedata) == 0:
                            break
                        length += len(filedata)
                        data += filedata
                        if len(data) >= self.piece_length:
                            info_pieces += hashlib.sha1(data[:self.piece_length]).digest()
                            data = data[self.piece_length:]
                file_dict['md5sum'] = key
                file_list.append(file_dict)

            self.tdict['info'].update(
                {
                    'files': file_list,
                }
            )

        if len(data) > 0:
                info_pieces += hashlib.sha1(data).digest()

        self.tdict['info'].update(
            {
                'pieces': info_pieces,
                'name': str(os.path.basename(real_path))
            }
        )

        self.info_hash = hashlib.sha1(bencode.bencode(self.tdict['info'])).hexdigest()

    def write(self):
        """Write the torrent file."""

        if self.filename is None:
            filename = "{0}.torrent".format(self.tdict["info"]["name"])
        else:
            filename = self.filename
        with open(filename, 'wb') as f:
            f.write(bencode.bencode(self.tdict))


def create_fingerprint(data, write_torrent=False):
    """Create a Data Integrity Fingerprint (DIF).

    Parameters
    ----------
    data : str
        the full path to the data
    write_torrent : bool, optional
        whether to write a .torrent file (default=False)

    Returns
    -------
    data_integrity_fingerprint : str
        the Data Integrity Fingerprint (DIF)

    """

    torrent = Torrent(data)
    if write_torrent:
        torrent.write()
    return torrent.info_hash


def verify_data(data, data_integrity_fingerprint, torrent_file=None):
    """Verify data integrity.

    Parameters
    ----------
    data : str
        the full path to the data
    data_integrity_fingerprint : str
        the Data Integrity Fingerprint (DIF)
    torrent_file : str, optional
        the fullpath to the .torrent file

    """

    if torrent_file is None:
        return create_fingerprint(data) == data_integrity_fingerprint

    else:

        class TorrentFileVerifier:

            def __init__(self, torrent_file):
                self.file = torrent_file
                self.info = bencode.bdecode(open(self.file, 'rb').read())["info"]
                self._current_file = ""
                self._corrupted_files = []

            def _pieces_generator(self):
                """Yield pieces from download file(s)."""
                piece_length = self.info['piece length']
                if 'files' in self.info:  # Yield pieces from a multi-file torrent
                    piece = ""
                    for file_info in self.info['files']:
                        self._current_file = os.sep.join([self.info['name']] + file_info['path'])
                        sfile = open(self._current_file.decode('UTF-8'), "rb")
                        while True:
                            piece += sfile.read(piece_length-len(piece))
                            if len(piece) != piece_length:
                                sfile.close()
                                break
                            yield piece
                            piece = ""
                    if piece != "":
                        yield piece
                else:  # Yield pieces from a single file torrent
                    self._current_file = self.info['name']
                    sfile = open(self._current_file.decode('UTF-8'), "rb")
                    while True:
                        piece = sfile.read(piece_length)
                        if not piece:
                            sfile.close()
                            return
                        yield piece

            def _corruption_failure(self):
                """Display error message."""

                if self._current_file not in self._corrupted_files:
                    print("{0} seems to be corrupted!".format(self._current_file))
                    self._corrupted_files.append(self._current_file)

            def verify(self):
                pieces = StringIO.StringIO(self.info['pieces'])
                #  iterate through pieces
                for piece in self._pieces_generator():
                    #  compare piece hash with expected hash
                    piece_hash = hashlib.sha1(piece).digest()
                    if piece_hash != pieces.read(20):
                        self._corruption_failure()
                # Ensure we've read all pieces 
                if pieces.read():
                    self._corruption_failure()

        tfv = TorrentFileVerifier(torrent_file)
        tfv.verify()
        return create_fingerprint(data) == data_integrity_fingerprint


