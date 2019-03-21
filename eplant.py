# -*- coding: utf-8 -*-

'''
eplant - easy lxml.etree planting.

Example:

    plant = ElementPlant(
        default_namespace = 'http://default/',
        nsmap = {
            'foo': 'http://foo/',
            'bar': 'http://bar/',
        }
    )

    default, foo, bar = plant.namespaces('', 'foo', 'bar')

    doc = default.root(
        foo.title({bar.x: 'a'}, 'title text'),
        bar('small-body', 'body text'),
    )

'''

from lxml.builder import ElementMaker


class QName(str):

    def __new__(cls, maker, name):
        self = str.__new__(cls, maker._namespace+name)
        self._maker = maker
        self._name = name
        return self

    def __call__(self, *args, **kwargs):
        return self._maker(self._name, *args, **kwargs)


class Namespace(ElementMaker):

    def __getattr__(self, name):
        return QName(self, name)


class ElementPlant(object):

    def __init__(self, default_namespace=None, nsmap=None, **options):
        self.nsmap = dict(nsmap or {})
        if default_namespace:
            self.nsmap[None] = default_namespace
        self.options = options

    def namespace(self, name):
        if name:
            namespace = self.nsmap[name]
        else:
            # Default namespace or unqualified
            namespace = self.nsmap.get(None, '')
        return Namespace(namespace=namespace, nsmap=self.nsmap, **self.options)

    def namespaces(self, *names):
        return tuple(self.namespace(name) for name in names)


# vim: set sts=4 sw=4 et ai:
