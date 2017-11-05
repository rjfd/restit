# -*- coding: utf-8 -*-

from unittest import TestCase
from restit.exceptions import RequestException
from restit import RestClient

import httpretty
from requests import ConnectionError


class TestRestClient(TestCase):
    class DummyClient(RestClient):
        def __init__(self):
            super(TestRestClient.DummyClient, self).__init__(
                'www.dummy.com', 8080
            )

        @RestClient.api_get('/class', resp_structure="[*] > (name & package)")
        def list_classes(self, request=None):
            return request({
                'format': 'json'
            })

        # pylint: disable=W0613
        @RestClient.api_get('/class/{cls_pkg}/{cls_name}',
                            resp_structure="name & package")
        def get_class(self, cls_pkg, cls_name, request=None):
            return request()

        @RestClient.api_post('/class', resp_structure="success")
        def add_class(self, class_pkg, class_name, request=None):
            return request({
                'name': class_name,
                'package': class_pkg
            })

        @RestClient.api_put('/class/{cls_pkg}/{cls_name}',
                            resp_structure="success")
        def deprecate_class(self, cls_pkg, cls_name, deprecated, request=None):
            return request({
                'deprecated': deprecated
            })

        @RestClient.api_delete('/class/{cls_pkg}/{cls_name}',
                               resp_structure="success")
        def remove_class(self, request=None, **kwargs):
            return request(params={'format': 'json'})

        @RestClient.api('/class')
        def generic_call(self, request=None, req_data=None, method=None,
                         params=None, data=None, raw_content=False):
            return request(req_data=req_data, params=params, method=method,
                           data=data, raw_content=raw_content)

        @RestClient.api('/class', resp_structure="*")
        def generic_api_call(self, request=None, req_data=None, method=None,
                             params=None, data=None, raw_content=False):
            return request(req_data=req_data, params=params, method=method,
                           data=data, raw_content=raw_content)

    def setUp(self):
        self.client = TestRestClient.DummyClient()

    @httpretty.activate
    def test_get(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.dummy.com:8080/class",
                               body='[{"name": "List", "package": "java.util"}'
                                    ', {"name": "Queue", "package": '
                                    '"java.util"}]',
                               content_type="application/json")

        result = self.client.list_classes()
        self.assertEqual(result, [
            {'name': 'List', 'package': 'java.util'},
            {'name': 'Queue', 'package': 'java.util'}
        ])
        self.assertEqual(httpretty.last_request().querystring,
                         {'format': ['json']})

    @httpretty.activate
    def test_get_param(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.dummy.com:8080/class/java.io/File",
                               body='{"name": "File", "package": "java.io"}',
                               content_type="application/json")

        result = self.client.get_class('java.io', 'File')
        self.assertEqual(result, {'name': 'File', 'package': 'java.io'})

    @httpretty.activate
    def test_post(self):
        httpretty.register_uri(httpretty.POST,
                               "http://www.dummy.com:8080/class",
                               body='{"success": true}',
                               content_type="application/json")

        result = self.client.add_class('java.io', 'File')
        self.assertEqual(result, {'success': True})
        self.assertEqual(httpretty.last_request().parsed_body,
                         {'name': ['File'],
                          'package': ['java.io']})

    @httpretty.activate
    def test_put(self):
        httpretty.register_uri(httpretty.PUT,
                               "http://www.dummy.com:8080/class/java.io/File",
                               body='{"success": false}',
                               content_type="application/json")

        result = self.client.deprecate_class(cls_name='File', deprecated=True,
                                             cls_pkg='java.io')
        self.assertEqual(result, {'success': False})
        self.assertEqual(httpretty.last_request().parsed_body,
                         {'deprecated': ['True']})

    @httpretty.activate
    def test_delete(self):
        httpretty.register_uri(httpretty.DELETE,
                               "http://www.dummy.com:8080/class/java.io/File",
                               body='{"success": true}',
                               content_type="application/json")

        result = self.client.remove_class(cls_name='File', cls_pkg='java.io')
        self.assertEqual(result, {'success': True})
        self.assertEqual(httpretty.last_request().querystring,
                         {'format': ['json']})

    def test_param_not_found(self):
        with self.assertRaises(RequestException) as ctx:
            self.client.remove_class(cls_package='java.io', cls_name='File')
        self.assertEqual(str(ctx.exception),
                         'Invalid path. Param "cls_pkg" was not specified')

    def test_no_http_method(self):
        with self.assertRaises(Exception) as ctx:
            self.client.generic_call()
        self.assertEqual(str(ctx.exception),
                         'No HTTP request method specified')

    def test_ambiguous_get_params(self):
        with self.assertRaises(Exception) as ctx:
            self.client.generic_call(method='get', req_data={'param': 0},
                                     params={'param': 1})
        self.assertEqual(str(ctx.exception),
                         'Ambiguous source of GET params')

    def test_ambiguous_upload_params(self):
        with self.assertRaises(Exception) as ctx:
            self.client.generic_call(method='post', req_data={'param': 0},
                                     data={'param': 1})
        self.assertEqual(str(ctx.exception),
                         'Ambiguous source of POST data')

    def test_incompatible_validation(self):
        with self.assertRaises(Exception) as ctx:
            self.client.generic_api_call(method='get', raw_content=True)
        self.assertEqual(str(ctx.exception),
                         'Cannot validate reponse in raw format')

    def test_http_method_not_supported(self):
        with self.assertRaises(RequestException) as ctx:
            self.client.generic_call(method='head')
        self.assertEqual(str(ctx.exception),
                         'Method "HEAD" not supported')

    @httpretty.activate
    def test_response_not_ok(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.dummy.com:8080/class",
                               body='{"success": false}',
                               content_type="application/json",
                               status=404)
        with self.assertRaises(RequestException) as ctx:
            self.client.generic_call(method='get')
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.content, '{"success": false}')

    @httpretty.activate
    def test_raw_content(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.dummy.com:8080/class",
                               body='<html><body>Hello Class</body></html>')
        result = self.client.generic_call(method='get', raw_content=True)
        self.assertEqual(result, '<html><body>Hello Class</body></html>')

    @httpretty.activate
    def test_invalid_json(self):
        httpretty.register_uri(httpretty.GET,
                               "http://www.dummy.com:8080/class",
                               body='<html><body>Hello Class</body></html>')
        with self.assertRaises(RequestException) as ctx:
            self.client.generic_api_call(method='get')
        self.assertEqual(ctx.exception.status_code, 200)
        self.assertEqual(ctx.exception.content,
                         '<html><body>Hello Class</body></html>')

    @httpretty.activate
    def test_connection_refused(self):
        with self.assertRaises(RequestException) as ctx:
            self.client.generic_api_call(method='get')
        self.assertEqual(ctx.exception.status_code, None)
        self.assertEqual(ctx.exception.content, None)
        self.assertEqual(ctx.exception.conn_errno, '111')
        self.assertEqual(ctx.exception.conn_strerror, "Connection refused")

    @httpretty.activate
    def test_connection_error(self):
        def throw_error():
            raise ConnectionError()

        httpretty.register_uri(httpretty.GET,
                               "http://www.dummy.com:8080/class",
                               body=throw_error)
        self.client.generic_api_call(method='get')
