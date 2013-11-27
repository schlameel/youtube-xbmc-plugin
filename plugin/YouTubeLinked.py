'''
    YouTube plugin for XBMC
    Copyright (C) 2010-2012 Tobias Ussing And Henrik Mosgaard Jensen

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
    
    Parts received from https://gist.github.com/uogbuji/705383
'''


import sys
import re
import time

try:
    import simplejson as json
except ImportError:
    import json


class YouTubeLinked():

    def __init__(self):
        self.language = sys.modules["__main__"].language
        self.storage = sys.modules["__main__"].storage
        self.core = sys.modules["__main__"].core
        self.common = sys.modules["__main__"].common
        self.nonChannels = ['edu', 'education', 'subscription_center', 'feed', 'editor', 'watch', 'playlist']
        # Received from https://gist.github.com/uogbuji/705383
        self.GRUBER_URLINTEXT_PAT = re.compile(ur'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?\xab\xbb\u201c\u201d\u2018\u2019]))')

    #---------------------------------Entry Points------------------------------------#
    def getLinkedResources(self, item):
        desc = item("Plot")
        channels = []
        playlists = []
        videos = []
        
        if not desc or 'media:thumbnail' in desc:
            return False
        
        mgroups = self.GRUBER_URLINTEXT_PAT.findall(desc)
        urls = [mgroup[0] for mgroup in mgroups]
        for url in urls:
            #######################################################################################
            #
            # Currently only looks for resources under the domains "youtube.com" and "youtu.be"
            # May need to be updated for international
            #
            ####################################################################################### 
            if 'youtube.com/' in url.lower() or 'youtu.be/' in url.lower():
                if '#' in url:
                    url = url[:url.find('#')]
                if self.hasPlaylist(url):
                    playlists.append(self.findPlaylist(url))
                elif self.hasVideo(url):
                    videos.append(self.findVideo(url))
                elif self.hasChannel(url):
                    channels.append(self.findChannel(url))

        url = ''
        q = {}
        if channels:
            q['linked_channels'] = json.dumps(self.uniquify(channels))
        if playlists:
            q['linked_playlists'] = json.dumps(self.uniquify(playlists))
        if videos:
            q['linked_videos'] = json.dumps(self.uniquify(videos))
        
        return q
    
    def list(self, params):
        self.common.log("params: " + repr(params), 5)
        self.common.log("params: " + repr(params))
        get = params.get
        
        if get("linked") == 'videos':
            return self.listVideos(params)
        
        if get("linked") == 'channels':
            return self.listChannels(params)

        if get("linked") == 'playlists':
            return self.listPlaylists(params)
    
    #------------------------------Resource Extraction---------------------------------#
    def hasChannel(self, url):
        '''Returns True if the URL is a channel.
        Assumes the URL is not a playlist or a video
        '''
        base = 'youtube.com/'
        ### May need to allow for youtube.com/channel/<channel_id> then get the name
        user_string = 'youtube.com/user/'
        if user_string in url.lower():
            return True
        start = url.lower().find(base) + len(base)
        end = url.find('/', start)
        if end == -1:
            end = url.find('?', start)
        if end == -1:
            user = url[start:]
        else:
            user = url[start:end]
        
        return (user not in self.nonChannels)
    
    def findChannel(self, url):
        base = 'youtube.com/'
        user_string = 'youtube.com/user/'
        if user_string in url.lower():
            start = url.lower().find(user_string) + len(user_string)
            end = url.find('/', start)
            if end == -1:
                end = url.find('\\', start)
            if end == -1:
                end = url.find('?', start)
            if end == -1:
                return url[start:]
            else:
                return url[start:end]
    
        start = url.lower().find(base) + len(base)
        end = url.find('/', start)
        if end == -1:
            end = url.find('\\', start)
        if end == -1:
            end = url.find('?', start)
        if end == -1:
            channel = url[start:]
        else:
            channel = url[start:end]
        return channel
            
    def hasPlaylist(self, url):
        return ('?list=' in url or '&list=' in url)
        
    def findPlaylist(self, url):
        list_string = 'list='
        start = url.find(list_string) + len(list_string)
        end = url.find('&', start)
        if end == -1:
            end = url.find('\\', start)
        if end != -1:
            return url[start:end]
        else:
            return url[start:]
        
    def hasVideo(self, url, eliminate_playlist=False):
        '''Returns True if the URL is a playlist.
        Assumes the URL is not a playlist
        '''
        if eliminate_playlist:
            if self.hasPlaylist(url):
                return False
    
        return ('/watch?' in url or 'youtu.be' in url.lower())
    
    def findVideo(self, url):
        youtu_be = 'youtu.be/'
        
        if youtu_be in url:
            loc = url.lower().find(youtu_be) + len(youtu_be)
            return url[loc:]
        
        if '?v=' in url or '&v=' in url:
            start = url.find('?v=') + 3
            if start < 3:
                start = url.find('&v=') + 3
            end = url.find('&', start)
            if end == -1:
                end = url.find('\\', start)
            if end != -1:
                return url[start:end]
            else:
                return url[start:]
        
    #----------------------------------List Resources----------------------------------#
    def listChannels(self, params):
        self.common.log("params: " + repr(params), 5)
        get = params.get
        
        channels = json.loads(get('linked_channels'))
        #self.common.log("channels - " + repr(channels), 5)

        (result, status) = self.getBatchDetails(params, channels)
        thumbnail = result[0].get('thumbnail', "")
        if (thumbnail):
            self.storage.store(params, thumbnail, "thumbnail")

        return (result, status)

    def listPlaylists(self, params):
        self.common.log("params: " + repr(params), 5)
        get = params.get
        
        playlists = json.loads(get('linked_playlists')) #self.decodeIds(get('linked_playlists'))
        (result, status) = self.getBatchDetails(params, playlists)
        thumbnail = result[0].get('thumbnail', "")
        if (thumbnail):
            self.storage.store(params, thumbnail, "thumbnail")
        
        return (result, status)

    def listVideos(self, params):
        self.common.log("params: " + repr(params), 5)
        get = params.get
        
        videos = json.loads(get('linked_videos')) #self.decodeIds(get('linked_videos'))

        (result, status) = self.core.getBatchDetails(videos)
        thumbnail = result[0].get('thumbnail', "")
        if (thumbnail):
            self.storage.store(params, thumbnail, "thumbnail")
        
        return (result, status)

    def getChannelInfo(self, xml):
        entries = self.getEntries(xml)

        ytobjects = []
        for node in entries:
            channel ={}
            
            try:
                self.common.log(node, 5)
                channel['Title'] = self.unescape(self.common.parseDOM(node, "title")[0])
                thumbnails = self.common.parseDOM(node, "media:thumbnail", ret="url")
                if thumbnails:
                    channel['thumbnail'] = thumbnails[0]
                channel['channel'] = self.common.parseDOM(node, "yt:username")[0]
                channel['feed'] = 'uploads'
                ytobjects.append(channel)
            except:
                continue

        return ytobjects

    def getPlaylistInfo(self, xml):
        entries = self.getEntries(xml)

        ytobjects = []
        for node in entries:
            playlist ={}
            
            try:
                playlist['Title'] = self.unescape(self.common.parseDOM(node, "title")[0])
                thumbnails = self.common.parseDOM(node, "media:thumbnail", attrs={'yt:name':'hqdefault'}, ret="url")
                if thumbnails:
                    playlist['thumbnail'] = thumbnails[0]
                else:
                    playlist['thumbnail'] = self.common.parseDOM(node, "media:thumbnail", ret="url") 
                playlist['playlist'] = self.common.parseDOM(node, "yt:playlistId")[0] 
                playlist['author'] = self.unescape(self.common.parseDOM(node, "name")[0]) 
                playlist['feed'] = 'playlist'
                ytobjects.append(playlist)
            except:
                continue

        return ytobjects
    
    def getBatchDetails(self, params, items):
        self.common.log("params: " + repr(params), 5)
        self.common.log("items: " + repr(items), 5)
        
        get = params.get
        
        request_start = ""
        request_end = ""
        api = ""
        
        if get('linked') == 'playlists':
            request_start = "<feed xmlns='http://www.w3.org/2005/Atom'\n xmlns:media='http://search.yahoo.com/mrss/'\n xmlns:batch='http://schemas.google.com/gdata/batch'\n xmlns:yt='http://gdata.youtube.com/schemas/2007'>\n <batch:operation type='query'/> \n"
            request_end = "</feed>"
            api = 'playlists/snippets/'
        elif get('linked') == 'channels':
            request_start = "<feed xmlns='http://www.w3.org/2005/Atom'\n xmlns:media='http://search.yahoo.com/mrss/'\n xmlns:batch='http://schemas.google.com/gdata/batch'\n xmlns:yt='http://gdata.youtube.com/schemas/2007'>\n <batch:operation type='query'/> \n"
            request_end = "</feed>"
            api = 'users/'
        else:
            return ([], 500)
        
        data_request = ""

        ytobjects = []
        status = 500
        i = 1
        result = ''

        for item_id in items:
            if item_id:
                data_request += "<entry> \n <id>http://gdata.youtube.com/feeds/api/" + api + item_id + "</id>\n</entry> \n"
                if i == 50:
                    final_request = request_start + data_request + request_end
                    rstat = 403
                    while rstat == 403:
                        result = self.core._fetchPage({"link": "http://gdata.youtube.com/feeds/api/" + api + "batch", "api": "true", "request": final_request})
                        rstat = self.common.parseDOM(result["content"], "batch:status", ret="code")
                        if len(rstat) > 0:
                            if int(rstat[len(rstat) - 1]) == 403:
                                self.common.log("quota exceeded. Waiting 5 seconds. " + repr(rstat))
                                rstat = 403
                                time.sleep(5)

                    temp = ""
                    if get('linked') == 'playlists':
                        temp = self.getPlaylistInfo(result["content"], params)
                    else:
                        temp = self.getChannelInfo(result["content"], params)
                    ytobjects += temp
                    data_request = ""
                    i = 1
                i += 1

        if i > 1:
            final_request = request_start + data_request + request_end
            result = self.core._fetchPage({"link": "http://gdata.youtube.com/feeds/api/" + api + "batch", "api": "true", "request": final_request})

            if get('linked') == 'playlists':
                temp = self.getPlaylistInfo(result["content"])
            else:
                temp = self.getChannelInfo(result["content"])
            ytobjects += temp

        if len(ytobjects) > 0:
            status = 200

        return (ytobjects, status)
    
    #----------------------------------Utilities----------------------------------#
    def unescape(self, s):
        s = s.replace("&lt;", "<")
        s = s.replace("&gt;", ">")
        s = s.replace("&apos;", "'")
        s = s.replace("&quot;", '"')
        s = s.replace("&amp;", "&")
        return s

    def uniquify(self, seq):
        seen = set()
        return [x for x in seq if x not in seen and not seen.add(x)]
    
    def getEntries(self, xml):
        entries = self.common.parseDOM(xml, "entry")
        if not entries:
            entries = self.common.parseDOM(xml, "atom:entry")

        return entries

