#  Copyright 2008-2015 Nokia Networks
#  Copyright 2016-     Robot Framework Foundation
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from inspect import isclass
from itertools import chain
import json
import re
try:
    from enum import Enum
except ImportError:  # Standard in Py 3.4+ but can be separately installed
    class Enum(object):
        pass

try:
    from typing_extensions import TypedDict

    class _TypedDictDummy(TypedDict):
        pass
    TypedDictType = type(_TypedDictDummy)
except ImportError:
    TypedDictType = None

from robot.model import Tags
from robot.utils import (IRONPYTHON, getshortdoc, get_timestamp,
                         Sortable, setter, unicode, unic)

from .htmlutils import HtmlToText, DocFormatter
from .writer import LibdocWriter
from .output import LibdocOutput


class LibraryDoc(object):

    def __init__(self, name='', doc='', version='', type='LIBRARY',
                 scope='TEST', doc_format='ROBOT',
                 source=None, lineno=-1):
        self.name = name
        self._doc = doc
        self.version = version
        self.type = type
        self.scope = scope
        self.doc_format = doc_format
        self.source = source
        self.lineno = lineno
        self._data_types = dict()
        self.inits = []
        self.keywords = []

    @property
    def data_types(self):
        return sorted([type_doc for type_doc in self._data_types.values()],
                      key=lambda type_doc: type_doc.name)

    @data_types.setter
    def data_types(self, data_types):
        list_of_type_docs = [self._get_type_doc(_type) for _type in data_types]
        self._data_types = dict([(t.name, t) for t in list_of_type_docs])

    @property
    def doc(self):
        if self.doc_format == 'ROBOT' and '%TOC%' in self._doc:
            return self._add_toc(self._doc)
        return self._doc

    def _add_toc(self, doc):
        toc = self._create_toc(doc)
        return '\n'.join(line if line.strip() != '%TOC%' else toc
                         for line in doc.splitlines())

    def _create_toc(self, doc):
        entries = re.findall(r'^\s*=\s+(.+?)\s+=\s*$', doc, flags=re.MULTILINE)
        if self.inits:
            entries.append('Importing')
        if self.keywords:
            entries.append('Keywords')
        if self._data_types:
            entries.append('Data types')
        return '\n'.join('- `%s`' % entry for entry in entries)

    @setter
    def doc_format(self, format):
        return format or 'ROBOT'

    @setter
    def inits(self, inits):
        return self._sort_keywords(inits)

    @setter
    def keywords(self, kws):
        return self._sort_keywords(kws)

    def _sort_keywords(self, kws):
        for keyword in kws:
            self._add_types_from_keyword(keyword)
            keyword.parent = self
            keyword.generate_shortdoc()
        return sorted(kws)

    def _add_types_from_keyword(self, keyword):
        for arg in keyword.args:
            if arg.type:
                for type_repr, _type in zip(arg.type_as_repr_list, arg.type):
                    if (type_repr not in self._data_types
                            and isinstance(_type, type)
                            and type(_type) is not type):
                        self._data_types[type_repr] = self._get_type_doc(_type)

    def _get_type_doc(self, arg_type):
        if isinstance(arg_type, (EnumDoc, TypedDictDoc)):
            return arg_type
        elif self._is_TypedDictType(arg_type):
            return TypedDictDoc(arg_type)
        elif self._is_EnumType(arg_type):
            return EnumDoc(arg_type)

    def _is_TypedDictType(self, arg_type):
        return (TypedDictType
                and isinstance(arg_type, TypedDictType)
                ) or (
                isinstance(arg_type, dict)
                and arg_type.get('super', None) == 'TypedDict')

    def _is_EnumType(self, arg_type):
        return (isclass(arg_type)
                and issubclass(arg_type, Enum)
                ) or (
                isinstance(arg_type, dict)
                and arg_type.get('super', None) == 'Enum')

    @property
    def all_tags(self):
        return Tags(chain.from_iterable(kw.tags for kw in self.keywords))

    def save(self, output=None, format='HTML'):
        with LibdocOutput(output, format) as outfile:
            LibdocWriter(format).write(self, outfile)

    def convert_docs_to_html(self):
        formatter = DocFormatter(self.keywords, self.data_types, self.doc, self.doc_format)
        self._doc = formatter.html(self.doc, intro=True)
        self.doc_format = 'HTML'
        for init in self.inits:
            init.doc = formatter.html(init.doc)
        for keyword in self.keywords:
            keyword.doc = formatter.html(keyword.doc)
        for type_doc in self._data_types.values():
            type_doc.doc = formatter.html(type_doc.doc)

    def to_dictionary(self):
        return {
            'name': self.name,
            'doc': self.doc,
            'version': self.version,
            'generated': get_timestamp(daysep='-', millissep=None),
            'type': self.type,
            'scope': self.scope,
            'doc_format': self.doc_format,
            'source': self.source,
            'lineno': self.lineno,
            'all_tags': list(self.all_tags),
            'inits': [init.to_dictionary() for init in self.inits],
            'keywords': [kw.to_dictionary() for kw in self.keywords],
            'data_types': [dt.to_dictionary() for dt in self.data_types]
        }

    def to_json(self, indent=None):
        data = self.to_dictionary()
        if IRONPYTHON:
            # Workaround for https://github.com/IronLanguages/ironpython2/issues/643
            data = self._unicode_to_utf8(data)
        return json.dumps(data, indent=indent)

    def _unicode_to_utf8(self, data):
        if isinstance(data, dict):
            return {self._unicode_to_utf8(key): self._unicode_to_utf8(value)
                    for key, value in data.items()}
        if isinstance(data, (list, tuple)):
            return [self._unicode_to_utf8(item) for item in data]
        if isinstance(data, unicode):
            return data.encode('UTF-8')
        return data


class KeywordDoc(Sortable):

    def __init__(self, name='', args=(), doc='', shortdoc='', tags=(), source=None,
                 lineno=-1, parent=None):
        self.name = name
        self.args = args
        self.doc = doc
        self._shortdoc = shortdoc
        self.tags = Tags(tags)
        self.source = source
        self.lineno = lineno
        self.parent = parent

    @property
    def shortdoc(self):
        if self._shortdoc:
            return self._shortdoc
        return self._get_shortdoc()

    def _get_shortdoc(self):
        doc = self.doc
        if self.parent and self.parent.doc_format == 'HTML':
            doc = HtmlToText().get_shortdoc_from_html(doc)
        return ' '.join(getshortdoc(doc).splitlines())

    @shortdoc.setter
    def shortdoc(self, shortdoc):
        self._shortdoc = shortdoc

    @property
    def deprecated(self):
        return self.doc.startswith('*DEPRECATED') and '*' in self.doc[1:]

    @property
    def _sort_key(self):
        return self.name.lower()

    def generate_shortdoc(self):
        if not self._shortdoc:
            self.shortdoc = self._get_shortdoc()

    def to_dictionary(self):
        return {
            'name': self.name,
            'args': [self._arg_to_dict(arg) for arg in self.args],
            'doc': self.doc,
            'shortdoc': self.shortdoc,
            'tags': list(self.tags),
            'source': self.source,
            'lineno': self.lineno
        }

    def _arg_to_dict(self, arg):
        return {
            'name': arg.name,
            'type': arg.type_as_repr_list,
            'default': arg.default_repr,
            'kind': arg.kind,
            'required': arg.required,
            'repr': unicode(arg)
        }


class TypedDictDoc:

    def __init__(self, type_info=None, name='', super='', doc='', items=None,
                 required_keys=None, optional_keys=None):
        self.name = name
        self.super = super
        self.doc = doc
        self.items = items or dict()
        self.required_keys = required_keys or list()
        self.optional_keys = optional_keys or list()
        if isinstance(type_info, dict):
            self.name = type_info['name']
            self.super = type_info['super']
            self.doc = type_info['doc']
            self.items = type_info['items']
            self.required_keys = type_info['required_keys']
            self.optional_keys = type_info['optional_keys']
        elif TypedDictType and isinstance(type_info, TypedDictType):
            self.name = type_info.__name__
            self.super = 'TypedDict'
            self.doc = type_info.__doc__ if type_info.__doc__ else ''
            for key, value in type_info.__annotations__.items():
                self.items[key] = value.__name__ if isclass(value) else unic(value)
            self.required_keys = list(type_info.__required_keys__)
            self.optional_keys = list(type_info.__optional_keys__)

    def to_dictionary(self):
        return {
            'name': self.name,
            'super': self.super,
            'doc': self.doc,
            'items': self.items,
            'required_keys': self.required_keys,
            'optional_keys': self.optional_keys
        }


class EnumDoc:

    def __init__(self,
                 type_info=None,
                 name='',
                 super='',
                 doc='',
                 members=None):
        self.name = name
        self.super = super
        self.doc = doc
        self.members = members or list()
        if isinstance(type_info, dict):
            self.name = type_info['name']
            self.super = type_info['super']
            self.doc = type_info['doc']
            self.members = type_info['members']
        elif isclass(type_info) and issubclass(type_info, Enum):
            self.name = type_info.__name__
            self.super = 'Enum'
            self.doc = type_info.__doc__ or ''
            self.members = [{'name': name, 'value': unicode(member.value)}
                            for name, member in type_info.__members__.items()]

    def to_dictionary(self):
        return {
            'name': self.name,
            'super': self.super,
            'doc': self.doc,
            'members': self.members
        }
