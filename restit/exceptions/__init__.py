# -*- coding: utf-8 -*-
"""
 *   Copyright (c) 2017 SUSE LLC
 *
 *  openATTIC is free software; you can redistribute it and/or modify it
 *  under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; version 2.
 *
 *  This package is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
"""


class RequestException(Exception):
    def __init__(self, message, status_code=None, content=None,
                 conn_errno=None, conn_strerror=None):
        super(RequestException, self).__init__(message)
        self.status_code = status_code
        self.content = content
        self.conn_errno = conn_errno
        self.conn_strerror = conn_strerror


class BadResponseFormatException(RequestException):
    def __init__(self, message):
        super(BadResponseFormatException, self).__init__(
            "Bad response format" if message is None else message, None)


class MalformedStructureException(Exception):
    def __init__(self, message):
        super(MalformedStructureException, self).__init__(
            "Malformed validation structure" if message is None else message)
