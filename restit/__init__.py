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
from __future__ import absolute_import

import inspect
import itertools
import logging
import re
import requests
from requests import ConnectionError
try:
    from requests.packages.urllib3.exceptions import SSLError
except ImportError:
    from urllib3.exceptions import SSLError

from .exceptions import RequestException, BadResponseFormatException
from .validator import ResponseValidator


logger = logging.getLogger(__name__)


class _Request(object):
    def __init__(self, method, path, path_params, rest_client, resp_structure):
        self.method = method
        self.path = path
        self.path_params = path_params
        self.rest_client = rest_client
        self.resp_structure = resp_structure

    def _gen_path(self):
        new_path = self.path
        matches = re.finditer(r'\{(\w+?)\}', self.path)
        for match in matches:
            if match:
                param_key = match.group(1)
                if param_key in self.path_params:
                    new_path = new_path.replace(match.group(0),
                                                self.path_params[param_key])
                else:
                    raise RequestException('Invalid path. Param "{}" was not '
                                           'specified'.format(param_key), None)
        return new_path

    def __call__(self, req_data=None, method=None, params=None, data=None,
                 raw_content=False):
        method = method if method else self.method
        if not method:
            raise Exception('No HTTP request method specified')
        if req_data:
            if method == 'get':
                if params:
                    raise Exception('Ambiguous source of GET params')
                params = req_data
            else:
                if data:
                    raise Exception('Ambiguous source of {} data'
                                    .format(method.upper()))
                data = req_data
        resp = self.rest_client.do_request(method, self._gen_path(), params,
                                           data, raw_content)
        if raw_content and self.resp_structure:
            raise Exception("Cannot validate reponse in raw format")
        ResponseValidator.validate(self.resp_structure, resp)
        return resp


class RestClient(object):
    def __init__(self, host, port, client_name=None, ssl=False, auth=None):
        super(RestClient, self).__init__()
        self.client_name = client_name if client_name else ''
        self.base_url = 'http{}://{}:{}'.format('s' if ssl else '', host, port)
        logger.debug("REST service base URL: %s", self.base_url)
        self.headers = {'Accept': 'application/json'}
        self.auth = auth
        self.session = requests.Session()

    def _login(self, request=None):
        pass

    def _is_logged_in(self):
        pass

    def _reset_login(self):
        pass

    def is_service_online(self, request=None):
        pass

    @staticmethod
    def requires_login(func):
        def func_wrapper(self, *args, **kwargs):
            retries = 2
            while True:
                try:
                    if not self._is_logged_in():
                        self._login()
                    resp = func(self, *args, **kwargs)
                    return resp
                except RequestException as e:
                    if isinstance(e, BadResponseFormatException):
                        raise e
                    retries -= 1
                    if e.status_code not in [401, 403] or retries == 0:
                        raise e
                    self._reset_login()
        return func_wrapper

    def do_request(self, method, path, params=None, data=None,
                   raw_content=False):
        url = '{}{}'.format(self.base_url, path)
        logger.debug('%s REST API %s req: %s data: %s', self.client_name,
                     method.upper(), path, data)
        try:
            if method.lower() == 'get':
                resp = self.session.get(url, headers=self.headers,
                                        params=params, auth=self.auth)
            elif method.lower() == 'post':
                resp = self.session.post(url, headers=self.headers,
                                         params=params, data=data,
                                         auth=self.auth)
            elif method.lower() == 'put':
                resp = self.session.put(url, headers=self.headers,
                                        params=params, data=data,
                                        auth=self.auth)
            elif method.lower() == 'delete':
                resp = self.session.delete(url, headers=self.headers,
                                           params=params, data=data,
                                           auth=self.auth)
            else:
                raise RequestException('Method "{}" not supported'
                                       .format(method.upper()), None)
            if resp.ok:
                logger.debug("%s REST API %s res status: %s content: %s",
                             self.client_name, method.upper(),
                             resp.status_code, resp.text)
                if raw_content:
                    return resp.content
                try:
                    return resp.json() if resp.text else None
                except ValueError:
                    logger.error("%s REST API failed %s req while decoding "
                                 "JSON response : %s", self.client_name,
                                 method.upper(), resp.text)
                    raise RequestException("{} REST API failed request while "
                                           "decoding JSON response: {}"
                                           .format(self.client_name,
                                                   resp.text),
                                           resp.status_code, resp.text)
            else:
                logger.error("%s REST API failed %s req status: %s",
                             self.client_name, method.upper(),
                             resp.status_code)
                raise RequestException("{} REST API failed request with status"
                                       " code {}".format(self.client_name,
                                                         resp.status_code),
                                       resp.status_code, resp.content)
        except ConnectionError as ex:
            if ex.args:
                if isinstance(ex.args[0], SSLError):
                    errno = "n/a"
                    strerror = "SSL error. Probably trying to access a non " \
                               "SSL connection."
                    logger.error("%s REST API failed %s, SSL error.",
                                 self.client_name, method.upper())
                else:
                    match = re.match(r'.*: \[Errno (-?\d+)\] (.+)',
                                     ex.args[0].reason.args[0])
                    if match:
                        errno = match.group(1)
                        strerror = match.group(2)
                        logger.error("%s REST API failed %s, connection error:"
                                     " [errno: %s] %s", self.client_name,
                                     method.upper(), errno, strerror)
                    else:
                        errno = "n/a"
                        strerror = "n/a"
                        logger.error(
                            "%s REST API failed %s, connection error.",
                            self.client_name, method.upper())
            else:
                errno = "n/a"
                strerror = "n/a"
                logger.error("%s REST API failed %s, connection error.",
                             self.client_name, method.upper())

            if errno != "n/a":
                ex_msg = ("{} REST API cannot be reached: {} [errno {}]. "
                          "Please check your configuration and that the API "
                          "endpoint is accessible"
                          .format(self.client_name, strerror, errno))
            else:
                ex_msg = ("{} REST API cannot be reached. Please check "
                          "your configuration and that the API endpoint is "
                          "accessible".format(self.client_name))
            raise RequestException(ex_msg, conn_errno=errno,
                                   conn_strerror=strerror)

    @staticmethod
    def api(path, **api_kwargs):
        def call_decorator(func):
            def func_wrapper(self, *args, **kwargs):
                method = api_kwargs.get('method', None)
                resp_structure = api_kwargs.get('resp_structure', None)
                args_name = inspect.getargspec(func).args
                args_dict = dict(itertools.izip(args_name[1:], args))
                for key, val in kwargs:
                    args_dict[key] = val
                return func(self, *args, request=_Request(method, path,
                                                          args_dict, self,
                                                          resp_structure),
                            **kwargs)
            return func_wrapper
        return call_decorator

    @staticmethod
    def api_get(path, resp_structure=None):
        return RestClient.api(path, method='get',
                              resp_structure=resp_structure)

    @staticmethod
    def api_post(path, resp_structure=None):
        return RestClient.api(path, method='post',
                              resp_structure=resp_structure)

    @staticmethod
    def api_put(path, resp_structure=None):
        return RestClient.api(path, method='put',
                              resp_structure=resp_structure)

    @staticmethod
    def api_delete(path, resp_structure=None):
        return RestClient.api(path, method='delete',
                              resp_structure=resp_structure)
