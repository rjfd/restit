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
from ..exceptions import BadResponseFormatException, \
                         MalformedStructureException


class ResponseValidator(object):
    """Simple JSON schema validator
    This class implements a very simple validator for the JSON formatted
    messages received by request responses from a RestClient instance.
    The validator validates the JSON response against a "structure" string that
    specifies the structure that the JSON response must comply.
    The validation procedure raises a BadResponseFormatException in case of a
    validation failure.
    The structure syntax is given by the following grammar:
    Structure  ::=  Level
    Level      ::=  Path | Path '&' Level
    Path       ::=  Step | Step '>'+ Path
    Step       ::=  Key  | '?' Key | '*' | '(' Level ')'
    Key        ::=  <string> | Array+
    Array      ::=  '[' <int> ']' | '[' '*' ']' | '[' '+' ']'
    The symbols enclosed in ' ' are tokens of the language, and the + symbol
    denotes repetition of the preceding token at least once.
    Examples of usage:
    Example 1:
        Validator args:
            structure = "return > *"
            response = { 'return': { ... } }
        In the above example the structure will validate against any response
        that contains a key named "return" in the root of the response
        dictionary and its value is also a dictionary.
    Example 2:
        Validator args:
            structure = "[*]"
            response = [...]
        In the above example the structure will validate against any response
        that is an array of any size.
    Example 3:
        Validator args:
            structure = "return[*]"
            response = { 'return': [....] }
        In the above example the structure will validate against any response
        that contains a key named "return" in the root of the response
        dictionary and its value is an array.
    Example 4:
        Validator args:
            structure = "return[0] > token"
            response = { 'return': [ { 'token': .... } ] }
        In the above example the structure will validate against any response
        that contains a key named "return" in the root of the response
        dictionary and its value is an array, and the first element of the
        array is a dictionary that contains the key 'token'.
    Example 5:
        Validator args:
            structure = "return[0][*] > key1"
            response = { 'return': [ [ { 'key1': ... } ], ...] }
        In the above example the structure will validate against any response
        that contains a key named "return" in the root of the response
        dictionary where its value is an array, and the first value of this
        array is also an array where all it's values must be a dictionary
        containing a key named "key1".
    Example 6:
        Validator args:
            structure = "return > (key1[*] & key2 & ?key3 > subkey)"
            response = { 'return': { 'key1': [...], 'key2: .... } ] }
        In the above example the structure will validate against any response
        that contains a key named "return" in the root of the response
        dictionary and its value is a dictionary that must contain a key named
        "key1" that is an array, a key named "key2", and optionaly a key named
        "key3" that is a dictionary that contains a key named "subkey".
    Example 7:
        Validator args:
            structure = "return >> roles[*]"
            response = { 'return': { 'key1': { 'roles': [...] },
                                     'key2': { 'roles': [...] } } }
        In the above example the structure will validate against any response
        that contains a key named "return" in the root of the response
        dictionary, and its value is a dictionary that for any key present in
        the dictionary their value is also a dictionary that must contain a key
        named 'roles' that is an array.
        Please note that you can use any number of successive '>' to denote the
        level in the JSON tree that you want to match next step in the path.
    """

    @staticmethod
    def validate(structure, response):
        if structure is None:
            return

        if response is None:
            raise BadResponseFormatException("Empty response")

        ResponseValidator._validate_level(structure, response)

    @staticmethod
    def _validate_level(level, resp):
        if level == '':
            if resp != {}:
                raise BadResponseFormatException("'{}' is not an empty dict"
                                                 .format(resp))
            else:
                return

        paths = ResponseValidator._parse_level_paths(level)
        for path in paths:
            path_sep = path.find('>')
            if path_sep != -1:
                level_next = path[path_sep + 1:].strip()
            else:
                path_sep = len(path)
                level_next = None
            key = path[:path_sep].strip()

            if key == '*':
                if not isinstance(resp, dict):
                    raise BadResponseFormatException("'{}' is not a dict"
                                                     .format(resp))
            elif key == '':  # check all keys
                for k in resp.keys():
                    ResponseValidator._validate_key(k, level_next, resp)
            else:
                ResponseValidator._validate_key(key, level_next, resp)

    @staticmethod
    def _validate_array(array_seq, level_next, resp):
        if array_seq:
            if not isinstance(resp, list):
                raise BadResponseFormatException("'{}' is not an array"
                                                 .format(resp))
            if array_seq[0].isdigit():
                idx = int(array_seq[0])
                if len(resp) <= idx:
                    raise BadResponseFormatException(
                        "length of array '{}' is lower than the index {}"
                        .format(resp, idx))
                ResponseValidator._validate_array(array_seq[1:], level_next,
                                                  resp[idx])
            elif array_seq[0] == '*':
                for elem in resp:
                    ResponseValidator._validate_array(array_seq[1:],
                                                      level_next, elem)
            elif array_seq[0] == '+':
                if len(resp) < 1:
                    raise BadResponseFormatException(
                        "array should not be empty")
                for elem in resp:
                    ResponseValidator._validate_array(array_seq[1:],
                                                      level_next, elem)
            else:
                raise MalformedStructureException(
                    "only <int> | '*' | '+' are allowed as array index "
                    "arguments")
        else:
            if level_next:
                ResponseValidator._validate_level(level_next, resp)

    @staticmethod
    def _validate_key(key, level_next, resp):
        array_access = [a.strip() for a in key.split("[")]
        key = array_access[0]
        if key:
            if not isinstance(resp, dict):
                raise BadResponseFormatException("'{}' is not a dict"
                                                 .format(resp))
            optional = key[0] == '?'
            if optional:
                key = key[1:]
            if key not in resp:
                if optional:
                    return
                raise BadResponseFormatException("key '{}' is not in dict {}"
                                                 .format(key, resp))
            resp_next = resp[key]
        else:
            resp_next = resp
        if len(array_access) > 1:
            ResponseValidator._validate_array(
                [a[0:-1] for a in array_access[1:]], level_next, resp_next)
        else:
            if level_next:
                ResponseValidator._validate_level(level_next, resp_next)

    @staticmethod
    def _parse_level_paths(level):
        level = level.strip()
        if level[0] == '(':
            level = level[1:]
            if level[-1] == ')':
                level = level[:-1]
            else:
                raise MalformedStructureException(
                    "There is no matching end parenthesis in '{}'"
                    .format(level))

        paths = []
        depth = 0
        nested = 0
        for i, char in enumerate(level):
            if char == '&' and nested == 0:
                paths.append(level[depth:i].strip())
                depth = i + 1
            elif char == '(':
                nested += 1
            elif char == ')':
                nested -= 1
        paths.append(level[depth:].strip())
        return paths
