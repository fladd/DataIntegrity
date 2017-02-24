# DataIntegrity

A tool for creating a _Data Integrity Fingerprint (DIF)_ of folders and single files, that is compatible with the BitTorrent info hash.

## Usage

**Create a fingerprint:**
```
>>> import data_integrity

>>> data_integrity.create_fingerprint("/path/to/my/data/", write_torrent=True)

>>> 'fb2e150f4424c27596a9403add5fee4fe4789be6'
```

If the optional argument `write_torrent` is `True`, a .torrent file will be written that can be used with any BitTorrent client to share the data.

**Verify the data:**
```
>>> import data_integrity

>>> data_integrity.verify_data("/path/to/my/data/", 'fb2e150f4424c27596a9403add5fee4fe4789be6')

>>> True
```

If a .torrent file is given as an optional third argument, each file in the data will be checked individually. In case the data cannot be verified, a list of corrupted files will be printed to the standard output.
