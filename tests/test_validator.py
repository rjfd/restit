# -*- coding: utf-8 -*-

from unittest import TestCase
from restit.exceptions import BadResponseFormatException, \
                              MalformedStructureException
from restit.validator import ResponseValidator


class TestResponseValidator(TestCase):
    def test_null_structure(self):
        ResponseValidator.validate(None, None)

    def test_invalid_response(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("", None)
        self.assertEqual(str(ctx.exception), "Empty response")

    def test_empty_response(self):
        ResponseValidator.validate("", {})

    def test_failed_empty_response(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("", {"hello": "world"})
        self.assertEqual(str(ctx.exception), "'{'hello': 'world'}' is not an "
                                             "empty dict")

    def test_dict_any_key(self):
        ResponseValidator.validate("*", {'key': 'value'})

    def test_dict_mandatory_key(self):
        ResponseValidator.validate("result", {'result': True, 'key': 'value'})

    def test_dict_mandatory_key_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("result", {'key': 'value'})
        self.assertEqual(str(ctx.exception),
                         "key 'result' is not in dict {'key': 'value'}")

    def test_dict_type(self):
        ResponseValidator.validate("result > *", {'result': {}})

    def test_dict_type_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("result > *", {'result': 'no_dict'})
        self.assertEqual(str(ctx.exception), "'no_dict' is not a dict")

    def test_dict_key_depth_1(self):
        ResponseValidator.validate("result > key",
                                   {'result': {'key': 'value'}})

    def test_dict_key_depth_1_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("result > key",
                                       {'result': {'wrong_key': 'value'}})
        self.assertEqual(str(ctx.exception),
                         "key 'key' is not in dict {'wrong_key': 'value'}")

    def test_dict_key_conjuction(self):
        ResponseValidator.validate("ret > (key1 & key2 & key3)",
                                   {'ret': {
                                       'key1': True,
                                       'key2': False,
                                       'key3': 4
                                   }})

    def test_dict_key_conjuction_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("ret > (key1 & key2 & key3)",
                                       {'ret': {
                                           'key1': True,
                                           'key2': False,
                                           'key4': 4
                                       }})
        self.assertTrue(str(ctx.exception).startswith(
            "key 'key3' is not in dict "))

    def test_dict_key_optional(self):
        ResponseValidator.validate("ret > (key1 & ?key2 & key3)",
                                   {'ret': {
                                       'key1': True,
                                       'key4': False,
                                       'key3': 4
                                   }})

    def test_dict_optional_complex(self):
        ResponseValidator.validate("ret > ?key1 > key2",
                                   {'ret': {
                                       'key3': True
                                   }})
        ResponseValidator.validate("ret > ?key1 > key2",
                                   {'ret': {
                                       'key1': {'key2': True}
                                   }})

    def test_dict_optional_complex_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("ret > ?key1 > key2",
                                       {'ret': {
                                           'key1': {'key3': False}
                                       }})
        self.assertEqual(str(ctx.exception),
                         "key 'key2' is not in dict {'key3': False}")

    def test_multiple_dicts(self):
        ResponseValidator.validate("ret > key1 > * & msg > *",
                                   {'ret': {'key1': {}},
                                    'msg': {}})

    def test_multiple_dicts_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("ret > key1 > * & msg > *",
                                       {'ret': {'key1': True},
                                        'msg': {}})
        self.assertEqual(str(ctx.exception),
                         "'True' is not a dict")

    def test_multiple_nested_dicts(self):
        ResponseValidator.validate("ret > (key1 > * & key2 > *)",
                                   {'ret': {
                                       'key1': {},
                                       'key2': {}
                                   }})

    def test_multiple_nested_dicts_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("ret > (key1 > * & key2 > *)",
                                       {'ret': {
                                           'key1': True,
                                           'key2': {}
                                       }})
        self.assertEqual(str(ctx.exception),
                         "'True' is not a dict")

    def test_dict_multiple_depth(self):
        ResponseValidator.validate("ret >> skey",
                                   {
                                       'ret': {
                                           'key1': {'skey': True},
                                           'key2': {'skey': False}
                                           }
                                   })

    def test_dict_multiple_depth_3(self):
        ResponseValidator.validate("ret >>> skey",
                                   {
                                       'ret': {
                                           'key1': {'key2': {'skey': True}},
                                       }
                                   })

    def test_dict_multiple_depth_fail_1(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("ret >> skey",
                                       {
                                           'ret': {
                                               'key1': {'skey': True},
                                               'key2': {'nkey': False}
                                           }
                                       })
        self.assertEqual(str(ctx.exception),
                         "key 'skey' is not in dict {'nkey': False}")

    def test_dict_multiple_depth_fail_2(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("ret >> skey",
                                       {
                                           'ret': {
                                               'key1': {'skey': True},
                                               'key2': {
                                                   'nkey': {'skey': False}
                                               }
                                           }
                                       })
        self.assertEqual(str(ctx.exception),
                         "key 'skey' is not in dict {'nkey': {'skey': False}}")

    def test_root_empty_array(self):
        ResponseValidator.validate("[*]", [])

    def test_array_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("[*]", {})
        self.assertEqual(str(ctx.exception), "'{}' is not an array")

    def test_root_at_least_one_element_array(self):
        ResponseValidator.validate("[+]", ['elem'])

    def test_root_at_least_one_element_array_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("[+]", [])
        self.assertEqual(str(ctx.exception), "array should not be empty")

    def test_dict_inside_array_1(self):
        ResponseValidator.validate("[+] > ret", [{'ret': 'True'}])

    def test_dict_inside_array_1_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("[+] > ret", ['hello'])
        self.assertEqual(str(ctx.exception), "'hello' is not a dict")

    def test_dict_inside_array_2(self):
        ResponseValidator.validate("[1] > ret", ['hello', {'ret': 'True'}])

    def test_dict_inside_array_2_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("[1] > ret", [{'ret': 'True'}, 'hello'])
        self.assertEqual(str(ctx.exception), "'hello' is not a dict")

    def test_array_inside_dict(self):
        ResponseValidator.validate("ret > [*]", {'ret': []})

    def test_array_inside_dict_2(self):
        ResponseValidator.validate("ret > [+] > hello", {
            'ret': [{'hello': True}]})

    def test_array_inside_dict_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("ret > [*]", {'ret': 'no_array'})
        self.assertEqual(str(ctx.exception), "'no_array' is not an array")

    def test_nested_array(self):
        ResponseValidator.validate("[+][*]", [['hello']])

    def test_nested_array_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("[+][*]", ['hello'])
        self.assertEqual(str(ctx.exception), "'hello' is not an array")

    def test_nested_array_2(self):
        ResponseValidator.validate("[0][1] > ret", [['hello', {'ret': True}]])

    def test_nested_array_2_fail(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("[+][1] > ret",
                                       [0, ['hello', {'ret': True}]])
        self.assertEqual(str(ctx.exception), "'0' is not an array")

    def test_array_index_out_of_bounds(self):
        with self.assertRaises(BadResponseFormatException) as ctx:
            ResponseValidator.validate("[1] > ret", ['hello'])
        self.assertEqual(str(ctx.exception),
                         "length of array '['hello']' is lower than the "
                         "index 1")

    def test_array_invalid_index(self):
        with self.assertRaises(MalformedStructureException) as ctx:
            ResponseValidator.validate("[inv] > ret", ['hello'])
        self.assertEqual(str(ctx.exception),
                         "only <int> | '*' | '+' are allowed as array index "
                         "arguments")

    def test_non_matching_parens(self):
        with self.assertRaises(MalformedStructureException) as ctx:
            ResponseValidator.validate("(ret > *", {'ret': None})
        self.assertEqual(str(ctx.exception),
                         "There is no matching end parenthesis in "
                         "'ret > *'")

    def test_complex_structure(self):
        ResponseValidator.validate(
            "([0] > ret >> (arr[1][0] > ?opt > (fst & snd[+]) & next > *))",
            [{
                'ret': {
                    'anything': {
                        'next': {},
                        'arr': [
                            [],
                            [
                                {
                                    'opt': {
                                        'fst': None,
                                        'snd': [True]
                                    }
                                }
                            ]
                        ]
                    }
                }
            }])
