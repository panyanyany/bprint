# -*- coding:utf-8 -*-
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division
import inspect
import sys
import types
import urwid

from . import constants as C
from . import settings as S
from .utils import pyv, _unicode
from .terminal_size import get_terminal_size
from .lib import search_up_tree as sut
# from kitchen.text import display

if pyv == 3:
    xrange = range


def typeval(v, context=None, type_editors=None):
    if type_editors is None:
        type_editors = {
            C._ST_BYTES_ | C._ST_LITERAL_ | C._ST_UNICODE_: st_string_handler,
            C._ST_UNDEFINED_: st_undefined_handler,
        }

    try:
        if S.united_str_coding_representation:
            st = string_type(v)
            ret = u''
            for stype, handler in type_editors.items():
                if stype & st:
                    ret = handler(v, st, context)
        else:
            ret = u'<YOU MUST SET S.united_str_coding_representation TO True>'

    except Exception as e:
        raise
        if S.priority_strategy == C._PS_CORRECTNESS_FIRST:
            print_exc_plus()
            raise e
        # S.priority_strategy == C._PS_CONTENT_FIRST:
        hx = v.decode("latin-1").encode("hex")
        ret = ustr("<CAN NOT PARSE OBJECT(hex:" + hx + "):" + str(e) + ">")

    return ret

def ustr(s):
    '''convert string into unicode'''
    res = u''

    if not isinstance(s, (_unicode, str)):
        s = str(s)

    if isinstance(s, _unicode):
        res += s
    elif isinstance(s, str):
        # in python 2/3, it's utf8
        # so decode to unicode
        res += s.decode(S.encoding)

    return res

def long_string_wrapper(ls, how):
    if how == C._LS_WRAP_BY_80_COLUMN:
        pass
    pass

def tail_symbol(position):
    """calculate the tail of block
    newline character does not include here because
    when your calculate the length of whole line you only need to be
    care about printable characters
    """
    if (position & C._AS_LIST_ELEMENT_ or
            position & C._AS_DICT_ELEMENT_ or
            position & C._AS_CLASS_ELEMENT_ or
            position & C._AS_TUPLE_ELEMENT_):
        tail = u','
    else:
        tail = u''
    return tail

def string_type(s):
    if pyv == 2:
        # in py2, string literal is both instance of str and bytes
        # a literal string is str (i.e: coding encoded, eg: utf8)
        # a u-prefixed string is unicode
        if isinstance(s, _unicode):
            return C._ST_UNICODE_
        elif isinstance(s, str):  # same as isinstance(v, bytes)
            return C._ST_LITERAL_ | C._ST_BYTES_
    else:
        # in py3, 
        # a literal string is str (i.e: unicode encoded)
        # a u-prefixed string is str
        # a utf8 string is bytes
        if isinstance(s, bytes):
            return C._ST_BYTES_
        elif isinstance(s, str):
            return C._ST_LITERAL_ | C._ST_UNICODE_

    return C._ST_UNDEFINED_


def st_undefined_handler(obj, st, context=None):
    return ustr(obj)


def st_string_handler(s, st, context):
    if st & C._ST_BYTES_:
        s = s.decode(S.encoding)

    s = ustr(s)

    s = s.replace(u'\n', u'\\n')
    s = s.replace(u'\r', u'\\r')
    s = s.replace(u'\t', u'\\t')

    left_margin = 0
    if context is not None:
        left_filling = u''.join([
            context.leading,
            context.key_expr,
            context.sep_expr,
        ])
        left_margin = calc_width(left_filling)

    left_margin += 1

    str_encloser = enclose_string(s, st)
    left_margin += calc_width(str_encloser.string_type_mark)

    # t = urwid.Text(str_encloser.body)
    width = 0
    if S.text_wrap_method == C._TEXT_WRAP_BY_TERMINAL:
        width = get_terminal_size()[0] - left_margin
    elif S.text_wrap_method == C._TEXT_WRAP_BY_WIDTH:
        width = S.text_wrap_width - left_margin
    else:
        width = 0

    if width > 0:
        # seg_list = t.render((width,)).text
        seg_list = wrap_string(str_encloser.body, width)
        indent_char_width = calc_width(S.leading)
        for i in xrange(1, len(seg_list)):
            seg_list[i] = ''.join([
                left_margin//indent_char_width*S.leading,
                left_margin%2*u' ',
                seg_list[i],
            ])
        s = "\n".join(seg_list)

    str_encloser.body = s
            
    return ustr(str_encloser)

def enclose_string(s, st):
    from .models import StringEncloser
    str_encloser = StringEncloser(s)

    if st & C._ST_UNICODE_:
        if S.str_display_not_prefix_u:
            pass
        else:
            str_encloser.set_string_type_mark(u'u')
    elif st & C._ST_BYTES_:
        # in py3, printed string will enclose with b''
        if S.str_display_not_prefix_b:
            pass
        else:
            str_encloser.set_string_type_mark(u'b')

    return str_encloser

def calc_width(s):
    return urwid.str_util.calc_width(s, 0, len(s))
    # return display.textual_width(s)

def wrap_string(s, width):
    # return display.wrap(s, width=width)
    t = urwid.Text(s)
    seg_list = t.render((width,)).text
    seg_list = [seg.rstrip() for seg in seg_list]
    if pyv == 3:
        # seg is the type of <class 'bytes'> in py3
        # seg is the type of <type 'str'> in py2
        seg_list = [seg.decode('utf8') for seg in seg_list]
    return seg_list

def cut_string(s, length):
    t = urwid.Text(s)
    seg_list = t.render((length,)).text
    a_str = seg_list[0].rstrip().decode('utf8')
    if pyv == 2:
        # to unicode
        a_str = a_str.decode('utf8')
    return a_str

def is_extendable(obj):
    '判断obj是否可以展开'
    return isinstance(obj, dict) or hasattr(obj, '__dict__') or isinstance(obj, (tuple, list, types.FrameType))

def too_long(leadCnt, position, obj):
    indent_str = leadCnt*S.leading

    choas = u''
    # assumpts its the value of list
    if position & C._AS_VALUE_:
        choas += '['
    choas += '\''

    terminal_x = get_terminal_size()[0]
    body = typeval(obj)
    whole_line_x = len(indent_str) + len(body)

    return terminal_x - whole_line_x <= 0

def object_attr_default_filter(obj, name, val):
    '过滤不需要的对象属性'

    for propLeading in S.prop_leading_filters:
        if name.startswith(propLeading):
            return True

    for prop in S.prop_filters:
        # filter is a string
        if isinstance(prop, str) or isinstance(prop, _unicode):
            if name == prop:
                return True
        # filter is a type
        # if type(prop) == types.TypeType:
        if isinstance(prop, type):
            if type(val) == prop:
                return True
        # filter is callable
        elif hasattr(prop, '__call__'):
            if prop(name, val):
                return True

    return False

def dict_key_filter(obj, name, val):
    return False

def _b(s):
    if S.write_to_buffer_when_execute:
        S.buffer_handler.write(s)
        S.buffer_handler.flush()
    return s

def inline_msg(o):
    if isinstance(o, (int, float, tuple, list, dict, bytes, str, _unicode)):
        'base types'
        _msg = typeval(o)
        msg = cut_string(_msg, 30)
        more = _msg[len(msg):]
        if len(more) > 0:
            msg += u'...(len=%d)' % calc_width(_msg)
    else:
        'class definitions or class instances'
        msg = repr(o)

    return msg
