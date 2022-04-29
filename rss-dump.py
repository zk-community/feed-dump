#!/usr/bin/env python
# coding: utf-8
# License: MIT
# Author: Chris Ward <chris@zeroknowledge.fm>

__app_name__ = "rss-dump"
__version__ = "0.1"

# Archive the zeroknowledge.fm rss feed

from datetime import date
import os
import re
import json
import requests
import sys
from dateutil import parser as dtparse
import feedparser # // pip install feedparser

import hashlib
import logging
log_format = ' > %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_format)
log = logging.getLogger()

#feed_json['entries'][0].keys()
# 'title', 'title_detail', 'links', 'link', 'id', 'guidislink', 
# 'published', 'published_parsed', 'authors', 'author', 'author_detail', 
# 'itunes_episodetype', 'subtitle', 'subtitle_detail', 'itunes_duration', 
# 'itunes_explicit', 'image', 'podcast_transcript', 'summary', 'summary_detail', 
# 'tags', 'content', 'fireside_playerurl', 'fireside_playerembedcode', 'podcast_person'
        
class FeedParser:
    def __init__(self, rss_url, quiet=True):
        log_lvl = logging.INFO if quiet else logging.DEBUG
        log.setLevel(log_lvl)
        log.debug(f'Setting log level: {log_lvl}')
        
        self.rss_url = rss_url

        # override whatever tempfile.gettempdir() offers .... FIXME cleanup
        #import tempfile
        #tmp_dir = tempfile.gettempdir() # prints the current temporary directory
        tmp_dir = './' 
        self.outpath = os.path.join(tmp_dir, 'out')
        self.outpath_mp3 = os.path.join(self.outpath, 'mp3')
        log.info(f'Saving to {outpath_mp3}')

        # check if a folder exists where to store the backup
        if not os.path.exists(self.outpath):  # FIXME: redudant? since below we makedirs again?
            os.makedirs(self.outpath)
        if not os.path.exists(self.outpath_mp3):
            os.makedirs(self.outpath_mp3)

    def _autoname(self, name, prefix=None, ext=None, x_http=True):
    # Make names readable, for humans and machines
        _name = name.strip()
        _name = re.sub('https?://', '', _name) if x_http else _name
        _name = re.sub(r'[^a-zA-Z0-9_ ./]', '', _name)
        _name = re.sub(r'[./]', '_', _name)
        _name = re.sub(r'Episode', 'Ep', _name)
        _name = re.sub(r'[-\s_]+', '_', _name)
        _name = _name.title()
        _name = f"{prefix}_{_name}" if prefix else _name
        _name = f"{_name}.{ext}" if ext else _name
        return _name
        
    def _dump_file(self, data, filepath):
    # dump some data to a file on disk
        filepath = os.path.join(self.outpath, filepath)
        with open(filepath, 'w') as f:
            try:
                json.dump(data, f)
                print(f'JSON dumped: {filepath}')
            except Exception as error:
                with open(filepath, 'w') as f:
                    f.write(data.text)
                    print(f'File saved: {filepath}')
        
    def download(self, url, save_as='', overwrite=False): 
    # Download a url and save the result to disk
        save_as = save_as or self._autoname(url)
        save_as = os.path.join(self.outpath, save_as)
        path_exists = os.path.exists(save_as)
        
        log.debug (f'Downloading {url} > {save_as}')    
        if path_exists and not overwrite:
            log.debug (f" ... skpping, cached: {save_as}")
        else:
            resp = requests.get(url)
            with open(save_as, "wb") as f: # opening a file handler to create new file 
                f.write(resp.content) # writing content to file
            log.info ( self.hash_file(save_as) ) 
        return self.hash_file(save_as)

    def hash_file(self, filename):
    # Get a sha256 hash of the file for later reference
        if os.path.isfile(filename) is False:
            raise Exception("File not found for hash operation") 
        # make a hash object
        h_sha256 = hashlib.sha256()
        # open file for reading in binary mode
        with open(filename,'rb') as file:
            # read file in chunks and update hash
            chunk = 0
            while chunk != b'':
                chunk = file.read(1024) 
                h_sha256.update(chunk)
        # return the hex digest
        return h_sha256.hexdigest()
        
    def save(self):
        # Backup the main rss feed / json feed dump
        today = date.today().isoformat().replace('-', '')
        
    # Make the archive; save the xml and json converted plus all entries mp3
    # FIXME: save other media
        self.rss_xml = requests.get(self.rss_url)       
        self.rss_json = feedparser.parse(self.rss_url)     

        k = 0
        entries = self.rss_json['entries']
        hashes = []
        for i in entries:
            pub_dt = dtparse.parse(i['published']).strftime('%Y%m%d')
            urls = [l['href'] for l in i['links'] if l['rel'] == 'enclosure']
            url = urls[0] if len(urls) > 0 else None
            out_mp3 = self._autoname(i['title'], f"mp3/{pub_dt}", 'mp3')
            hash_sha256 = self.download(url, out_mp3) # cache, only download if newly available
            hashes.append(hash_sha256)
            k += 1
        self.rss_json['HASHES'] = hashes
        # force these to backup new everytime
        self._dump_file(self.rss_xml, self._autoname(self.rss_url, today, ext='xml'))
        # add hashes to json. FIXME: Add also to xml for consistency... ^^^^^^^^^^^^^^^^^^^^^
        self._dump_file(self.rss_json, self._autoname(self.rss_url, today, ext='json'))
        self._dump_file(hashes, self._autoname('hashes', ext='json'))
        
        print (f'{k} entries.')
        last_title = entries[0]['title']
        print (f'Last entry: {last_title}')

if __name__ == "__main__":
    # Backup the entire zeroknowledge podcast feed
    furl = 'https://feeds.fireside.fm/zeroknowledge/rss'
    furl = sys.argv[1] if len(sys.argv) > 1 else furl
    feed = FeedParser(furl, quiet=False)
    feed.save()
