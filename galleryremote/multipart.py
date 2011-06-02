# This file is part of GUP.
#
# It is free software; you can redistribute it and/or modify it under the
# terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any
# later version.
#
# It is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along
# with it; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
#
# Copyright (C) 2007 Julio Biason

import mimetypes

def multipart(boundary, arguments, file_info):
    """
    Generates the body of a multipart data.
    """
    parts = []
    for key, value in arguments.iteritems():
        parts.append('--%s' % boundary)
        parts.append('Content-disposition: form-data; name="%s"' % key)
        parts.append('')
        parts.append(value)

    if file_info is not None:
        content_type = mimetypes.guess_type(file_info[1])[0] or \
                'application/octet-stream'

        parts.append('--%s' % (boundary))
        parts.append('Content-disposition: form-data; ' + \
                'name="%s"; filename="%s"' %
                (file_info[0], file_info[1]))
        parts.append('Content-Type: %s' % content_type)
        parts.append('Content-Transfer-Encoding: base64')
        parts.append('')

        image = open(file_info[1], "rb")
        contents = image.read()
        image.close()

        parts.append(contents)

    parts.append('--%s--' % boundary)

    return '\r\n'.join(parts)
