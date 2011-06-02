# -*- coding: utf-8 -*-
#
# Copyright © 2009-2011 Pietro Battiston
#   http://www.pietrobattiston.it
#
# Copyright (C) 2008 Brent Woodruff
#   http://www.fprimex.com
#
# Copyright (C) 2004 John Sutherland <garion@twcny.rr.com>
#   http://garion.tzo.com/python/
# 
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

__version__ = '0.6'

USER_AGENT = 'python-galleryremote v. %s' % (__version__)

CA_SYSTEM_DIR = '/etc/ssl/certs'

import urllib2
import cookielib

try:
    from M2Crypto import m2urllib2, SSL
    M2CRYPTO_AVAILABLE = True
except:
    M2CRYPTO_AVAILABLE = False

import StringIO
import time
import logging
from multipart import multipart

class GalleryException(Exception):
    """
    The base class for exceptions related to error messages from gallery.
    """

class ConnectionException(Exception):
    """
    The base class for exceptions related to connection to gallery.
    """

class NotSupportedException(Exception):
    """
    For operations that only one version of Gallery supports, if asked with the
    other version.
    """

class Gallery:
    """
    The Gallery class implements the Gallery Remote protocol as documented
    here:
    http://codex.gallery2.org/Gallery_Remote:Protocol

    The Gallery project is an open source web based photo album organizer
    written in php. Gallery's web site is:
    http://gallery.menalto.com/

    This class is a 3rd party product which is not maintained by the
    creators of the Gallery project.

    Example usage:
    from galleryremote import Gallery
    my_gallery = Gallery('http://www.yoursite.com/gallery2', 2)
    my_gallery.login('username','password')
    albums = my_gallery.fetch_albums()
    """

    def __init__(self, url, version=2):
        """
        Create a Gallery for remote access.
        url - base address of the gallery
        version - version of the gallery being connected to (default 2),
                  either 1 for Gallery1 or 2 for Gallery2
        
        gallery-uploader is able to cope with secured connections, thanks to
        M2Crypto. It won't catch any exception, though: handling i.e. unverified
        certificates is entirely left to higher level applications, which must
        hence be ready to catch M2Crypto exceptions.
        Moreover, gallery-uploader works fine (only emits a warning) also if
        M2Crypto is not available, and in that case connections will NOT be
        secure! If you want to avoid this risk, you can simply assert
        gallery.M2CRYPTO_AVAILABLE .
        """
        self.version = version # Gallery1 or Gallery2
        if version == 1:
            self.url = url + '/gallery_remote2.php'
        else:
            # default to G2
            self.url = url + '/main.php'
        
        # Until proven otherwise:
        self.secured = False
        
        if self.url.startswith( 'https://' ):
            if M2CRYPTO_AVAILABLE:
                self.secured = True
            else:
                print "WARNING: M2Crypto missing, gallery-uploader connections will not be secure!"
        
        self.cookiejar = cookielib.CookieJar()
        
        if self.secured:
            self.ssl_context = SSL.Context()
            self.ssl_context.load_verify_info( capath=CA_SYSTEM_DIR )
            self.ssl_context.set_verify( SSL.verify_peer |
                                         SSL.verify_fail_if_no_peer_cert |
                                         SSL.verify_client_once, 20 )
            self.opener = m2urllib2.build_opener( self.ssl_context, urllib2.HTTPCookieProcessor(self.cookiejar) )
        else:
            self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))

            
        self.logged_in = 0
        self.protocol_version = '2.5'
        self.auth_token = ''

    def _do_request(self, request, file_info=None):
        """
        Send a request, encoded as described in the Gallery Remote protocol.
        request - a dictionary of protocol parameters and values
        file_info - a tuple with the field name and the filename to be added
          in the body
        """
        boundary = '------python-galleryremote_boundary_%d' % int(time.time())

        headers = {'User-agent' : USER_AGENT,
                   'Content-type':'multipart/form-data; boundary=%s' % boundary,
                   'Accept': 'text/plain'}

        if self.auth_token and self.version >= 2:
            request['g2_authToken'] = self.auth_token
            logging.debug( "Submitting auth token %s" % self.auth_token )
        else:
            logging.debug( "Submitting no auth token" )
        
        enc_request = multipart(boundary, request, file_info)
        logging.debug( '\n\t\tREQUEST\n' )
        logging.debug( str(request) )
        logging.debug( '\n\t\tHEADERS (OUT)\n' )
        logging.debug( str(headers) )
        req = urllib2.Request(self.url, enc_request, headers)
        response = self.opener.open( req )
        
        info = response.info()
        logging.debug( "\n\t\tINFO (IN)\n" )
        logging.debug( str(info) )

        data = response.read()
        logging.debug( "\n\t\tDATA (IN)\n" )
        logging.debug( str(data) )
        response = self._parse_response( data )
        
        if 'auth_token' in response:
            self.auth_token = response['auth_token']
            logging.debug( "Got auth token %s" % self.auth_token )
        else:
            logging.debug( "No auth token found in %s" % response )

        if 'status' in response:
            # This _should be_ the right code to handle exceptions in Gallery 1,
            # but I didn't test; it was already there and assumed that 'status'
            # _was_ in response -- Pietro Battiston
            if response['status'] != '0':
                raise GalleryException, response['status_text']
        else:
            # ... but apparently, in Gallery 2 exceptions response _doesn't_
            # contain 'status' (FIXME: VERIFY!):
            if 'debug_exception' in response:
                raise GalleryException, response['debug_exception']

        return response
    
    def _parse_response(self, response):
        """
        Decode the response from a request, returning a request dict
        response - The response from a gallery request, encoded according
                   to the gallery remote protocol
        """
        myStr = StringIO.StringIO(response)
        
        header_found = False
        
        for line in myStr:
            if '#__GR2PROTO__' in line:
                header_found = True
                break
        
        if not header_found:
            # the 1st line should start with #__GR2PROTO__ !
            raise ConnectionException, "Bad response: \n" + response
            
        resDict = {}
        
        # This operates still on myStr (on the lines _following_ the header):
        for myS in myStr:
            strList = myS.split('=', 2)
                
            try:
                resDict[strList[0]] = strList[1]
                if resDict[strList[0]].endswith('\n'):
                    resDict[strList[0]] = resDict[strList[0]][:-1]                    
            except:
                resDict[strList[0]] = ''
        
        return resDict

    def _get(self, response, kwd):
        """
        """
        try:
            retval = response[kwd]
        except:
            retval = ''
        
        return retval
    
    def login(self, username, password):
        """
        Establish an authenticated session to the remote gallery.
        username - A valid gallery user's username
        password - That valid user's password
        """
        if self.version == 1:
            request = {
                'protocol_version' : self.protocol_version,
                'cmd' : 'login',
                'uname' : username,
                'password' : password
            }
        else:
            request = {
                'g2_controller' : 'remote:GalleryRemote',
                'g2_form[protocol_version]' : self.protocol_version,
                'g2_form[cmd]' : 'login',
                'g2_form[uname]' : username,
                'g2_form[password]' : password
            }
        response = self._do_request(request)
        
        # as long as it comes back here without an exception, we're ok.
        self.logged_in = True
    
    def fetch_albums(self):
        """
        Obtain a dict of albums contained in the gallery keyed by
        album name. In Gallery1, the name is alphanumeric. In Gallery2,
        the name is the unique identifying number for that album.
        """
        if self.version == 1:
            request = {
                'protocol_version' : self.protocol_version,
                'cmd' : 'fetch-albums'
            }
        else:
            request = {
                'g2_controller' : 'remote:GalleryRemote',
                'g2_form[protocol_version]' : self.protocol_version,
                'g2_form[cmd]' : 'fetch-albums'
            }
        response = self._do_request(request)
        
        # as long as it comes back here without an exception, we're ok.
        albums = {}
        
        for x in range(1, int(response['album_count']) + 1):
            album = {}
            album['name']                   = self._get(response,'album.name.' + str(x))
            album['title']                  = self._get(response,'album.title.' + str(x))
            album['summary']                = self._get(response,'album.summary.' + str(x))
            album['parent']                 = self._get(response,'album.parent.' + str(x))
            album['resize_size']            = self._get(response,'album.resize_size.' + str(x))
            album['perms.add']              = self._get(response,'album.perms.add.' + str(x))
            album['perms.write']            = self._get(response,'album.perms.write.' + str(x))
            album['perms.del_item']         = self._get(response,'album.perms.del_item.' + str(x))
            album['perms.del_alb']          = self._get(response,'album.perms.del_alb.' + str(x))
            album['perms.create_sub']       = self._get(response,'album.perms.create_sub.' + str(x))
            album['perms.info.extrafields'] = self._get(response,'album.info.extrafields' + str(x))
            album['ownerid']                = self._get(response,'album.ownerid' + str(x))
            
            albums[album['name']] = album
        
        return albums
    
    def fetch_albums_prune(self):
        """
        Obtain a dict of albums contained in the gallery keyed by
        album name. In Gallery1, the name is alphanumeric. In Gallery2,
        the name is the unique identifying number for that album.

        From the protocol docs:
        "The fetch_albums_prune command asks the server to return a list
        of all albums that the user can either write to, or that are
        visible to the user and contain a sub-album that is writable
        (including sub-albums several times removed)."
        """
        if self.version == 1:
            request = {
                'protocol_version' : self.protocol_version,
                'cmd' : 'fetch-albums-prune'
            }
        else:
            request = {
                'g2_controller' : 'remote:GalleryRemote',
                'g2_form[protocol_version]' : self.protocol_version,
                'g2_form[cmd]' : 'fetch-albums-prune'
            }
        response = self._do_request(request)
        
        # as long as it comes back here without an exception, we're ok.
        albums = {}
        
        for x in range(1, int(response['album_count']) + 1):
            album = {}
            album['name']                   = self._get(response,'album.name.' + str(x))
            album['title']                  = self._get(response,'album.title.' + str(x))
            album['summary']                = self._get(response,'album.summary.' + str(x))
            album['parent']                 = self._get(response,'album.parent.' + str(x))
            album['resize_size']            = self._get(response,'album.resize_size.' + str(x))
            album['perms.add']              = self._get(response,'album.perms.add.' + str(x))
            album['perms.write']            = self._get(response,'album.perms.write.' + str(x))
            album['perms.del_item']         = self._get(response,'album.perms.del_item.' + str(x))
            album['perms.del_alb']          = self._get(response,'album.perms.del_alb.' + str(x))
            album['perms.create_sub']       = self._get(response,'album.perms.create_sub.' + str(x))
            album['perms.info.extrafields'] = self._get(response,'album.info.extrafields' + str(x))
            album['ownerid']                = self._get(response,'album.ownerid' + str(x))
            
            albums[album['name']] = album
        
        return albums

    def add_item(self, album, filename, caption, description):
        """
        Add a photo to the specified album.
        album - album name / identifier
        filename - image to upload
        caption - string caption to add to the image
        description - string description to add to the image
        """
        if self.version == 1:
            request = {
                'protocol_version' : self.protocol_version,
                'cmd' : 'add-item',
                'set_albumName' : album,
                'userfile_name' : filename,
                'caption' : caption,
                'extrafield.Description' : description
            }
            response = self._do_request(request, ('userfile', filename) )
        else:
            request = {
                'g2_controller' : 'remote:GalleryRemote',
                'g2_form[protocol_version]' : self.protocol_version,
                'g2_form[cmd]' : 'add-item',
                'g2_form[set_albumName]' : album,
                'g2_form[userfile_name]' : filename,
                'g2_form[caption]' : caption,
                'g2_form[extrafield.Description]' : description
            }
            response = self._do_request(request, ('g2_userfile', filename) )
        
    
    def album_properties(self, album):
        """
        Obtain album property information for the specified album.
        album - the album name / identifier to obtain information for
        """
        if self.version == 1:
            request = {
                'protocol_version' : self.protocol_version,
                'cmd' : 'album-properties',
                'set_albumName' : album
            }
        else:
            request = {
                'g2_controller' : 'remote:GalleryRemote',
                'g2_form[protocol_version]' : self.protocol_version,
                'g2_form[cmd]' : 'album-properties',
                'g2_form[set_albumName]' : album
            }
        response = self._do_request(request)
        
        res_dict = {}
        
        if response.has_key('auto_resize'):
            res_dict['auto_resize'] = response['auto_resize']
        if response.has_key('add_to_beginning'):
            res_dict['add_to_beginning'] = response['add_to_beginning']
        
        return res_dict

    def image_properties(self, image):
         """
         Obtain image property information for the specified image.
         image - the identifier of the image for which we're interested in
         """
         if self.version == 1:
             raise NotSupportedException, "Operation not supported in Gallery version 1"
         else:
             request = {
                 'g2_controller' : 'remote:GalleryRemote',
                 'g2_form[protocol_version]' : self.protocol_version,
                 'g2_form[cmd]' : 'image-properties',
                 'g2_form[id]' : image
             }
         response = self._do_request(request)
         
         res_dict = {}
         
         for key in ['name', 'raw_height', 'raw_width', 'raw_filesize',\
         'resizedName', 'resized_width', 'resized_height', 'thumbName',\
         'thumb_width', 'thumb_height', 'caption', 'title', 'force', 'hidden']:
             if response.has_key('image.'+key):
                 res_dict[key] = response['image.'+key]
                 
         return res_dict
    
    def new_album(self, parent, name=None, title=None, description=None):
        """
        Add an album to the specified parent album.
        parent - album name / identifier to contain the new album
        name - unique string name of the new album
        title - string title of the album
        description - string description to add to the image
        """
        if self.version == 1:
            request = {
                'g2_controller' : 'remote:GalleryRemote',
                'protocol_version' : self.protocol_version,
                'cmd' : 'new-album',
                'set_albumName' : parent
            }
            if name != None:
                request['newAlbumName'] = name
            if title != None:
                request['newAlbumTitle'] = title
            if description != None:
                request['newAlbumDesc'] = description
        else:
            request = {
                'g2_controller' : 'remote:GalleryRemote',
                'g2_form[protocol_version]' : self.protocol_version,
                'g2_form[cmd]' : 'new-album',
                'g2_form[set_albumName]' : parent
            }
            if name != None:
                request['g2_form[newAlbumName]'] = name
            if title != None:
                request['g2_form[newAlbumTitle]'] = title
            if description != None:
                request['g2_form[newAlbumDesc]'] = description

        response = self._do_request(request)
        
        return response['album_name']
    
    def fetch_album_images(self, album):
        """
        Get the image information for all images in the specified album.
        album - specifies the album from which to obtain image information
        """
        if self.version == 1:
            request = {
                'protocol_version' : self.protocol_version,
                'cmd' : 'fetch-album-images',
                'set_albumName' : album,
                'albums_too' : 'no',
                'extrafields' : 'yes'
            }
        else:
            request = {
                'g2_controller' : 'remote:GalleryRemote',
                'g2_form[protocol_version]' : self.protocol_version,
                'g2_form[cmd]' : 'fetch-album-images',
                'g2_form[set_albumName]' : album,
                'g2_form[albums_too]' : 'no',
                'g2_form[extrafields]' : 'yes'
            }
        
        response = self._do_request(request)
        
        # as long as it comes back here without an exception, we're ok.
        images = []
        
        for x in range(1, int(response['image_count']) + 1):
            image = {}
            image['name']                = self._get(response, 'image.name.' + str(x))
            image['title']               = self._get(response, 'image.title.' + str(x))
            image['raw_width']           = self._get(response, 'image.raw_width.' + str(x))
            image['raw_height']          = self._get(response, 'image.raw_height.' + str(x))
            image['resizedName']         = self._get(response, 'image.resizedName.' + str(x))
            image['resized_width']       = self._get(response, 'image.resized_width.' + str(x))
            image['resized_height']      = self._get(response, 'image.resized_height.' + str(x))
            image['thumbName']           = self._get(response, 'image.thumbName.' + str(x))
            image['thumb_width']         = self._get(response, 'image.thumb_width.' + str(x))
            image['thumb_height']        = self._get(response, 'image.thumb_height.' + str(x))
            image['raw_filesize']        = self._get(response, 'image.raw_filesize.' + str(x))
            image['caption']             = self._get(response, 'image.caption.' + str(x))
            image['clicks']              = self._get(response, 'image.clicks.' + str(x))
            image['capturedate.year']    = self._get(response, 'image.capturedate.year' + str(x))
            image['capturedate.mon']     = self._get(response, 'image.capturedate.mon' + str(x))
            image['capturedate.mday']    = self._get(response, 'image.capturedate.mday' + str(x))
            image['capturedate.hours']   = self._get(response, 'image.capturedate.hours' + str(x))
            image['capturedate.minutes'] = self._get(response, 'image.capturedate.minutes' + str(x))
            image['capturedate.seconds'] = self._get(response, 'image.capturedate.seconds' + str(x))
            image['description']         = self._get(response, 'image.extrafield.Description.' + str(x))
            image['hidden']              = self._get(response, 'image.hidden.' + str(x))
            images.append(image)
        
        return images
    
    def fetch_image(self, image, thumb=True):
         """
         Get the image (this returns the real image data).
         If "thumb" is set, this will first do an "image-properties" request to
         get the name of the thumbnail, then get the thumbnail (if a thumbnail is
         not found, the image itself is returned).
         Alternatively, the name of the thumbnail can be passed directly as
         "image"; in this case, "thumb" must be False (since a thumbnail doesn't
         have a thumbnail!).
         
         FIXME: fetch_album_images already gets the name of each thumbnail, and
         it's very likely that it gets called before any call to fetch_image, so
         some caching of the information could spare many requests.
         """
         if self.version == 1:
             # I must search for the image url in Gallery1 - Pietro
             raise NotImplementedError, "Image retrieval curretnly not implemented for Gallery 1"
 
         if thumb:
             image_info = self.image_properties(image)
             if 'thumName' in image_info:
                 image = image_info[thumbname]
 
         image_url = self.url + '?g2_view=core.DownloadItem&g2_itemId=%s' % str(image)
 
         req = urllib2.Request(image_url)
         response = self.opener.open( req )
 
         return response.read()
