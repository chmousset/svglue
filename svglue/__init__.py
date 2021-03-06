#!/usr/bin/env python
# -*- coding: utf-8 -*-

from uuid import uuid4

from lxml import etree


SVG_NS = 'http://www.w3.org/2000/svg'
RECT_TAG = '{http://www.w3.org/2000/svg}rect'
TSPAN_TAG = '{http://www.w3.org/2000/svg}tspan'
IMAGE_TAG = '{http://www.w3.org/2000/svg}image'
USE_TAG = '{http://www.w3.org/2000/svg}use'
GRP_TAG = '{http://www.w3.org/2000/svg}g'
TXT_TAG = '{http://www.w3.org/2000/svg}text'
HREF_ATTR = '{http://www.w3.org/1999/xlink}href'

def fix_ids(etree):
    etree.set('id', str(uuid4()))
    for i in etree:
        fix_ids(i)

class TemplateParseError(Exception):
    pass


class Template(object):
    @classmethod
    def load(cls, src=None, file=None):
        if not (src == None) ^ (file == None):
            raise RuntimeError('Must specify exactly one of src or '
                               'file argument')

        if src:
            return cls(etree.fromstring(src))

        return cls(etree.parse(file))

    def __init__(self, doc):
        self._doc = doc
        self._rect_subs = {}
        self._tspan_subs = {}
        self._grp_subs = {}
        self._defs = None

        for elem in self._doc.xpath('//*'):
            tid = elem.get('template-id', None)
            if not tid:
                continue

            # FIXME: use own namespace?
            del elem.attrib['template-id']

            if elem.tag == RECT_TAG:
                self._rect_subs[tid] = elem
            elif elem.tag == TSPAN_TAG:
                self._tspan_subs[tid] = elem
            elif elem.tag == GRP_TAG:
                self._grp_subs[tid] = elem
            elif elem.tag == TXT_TAG:
                self._tspan_subs[tid] = elem[0]
            else:
                raise TemplateParseError(
                    'Can only replace <rect> and <tspan> elements, found %s '
                    'instead' % (elem.tag,)
                )

        defs = self._doc.xpath('/svg:svg/svg:defs', namespaces={'svg': SVG_NS})

        if defs:
            self._defs = defs[0]
        else:
            self._defs = self._doc.getroot().insert(
                0, etree.Element('{%s}defs' % SVG_NS)
            )

    def set_text(self, tid, text):
        self._tspan_subs[tid].text = text

    def set_image(self, tid, src=None, file=None, mimetype=None):
        if not (src == None) ^ (file == None):
            raise RuntimeError('Must specify exactly one of src or '
                               'file argument')

        if not mimetype and (not file or hasattr(file, 'read')):
            raise RuntimeError('Must specify mimetype when not linking ',
                               'an image')

        elem = self._rect_subs[tid]
        elem.tag = IMAGE_TAG

        ALLOWED_ATTRS = ('x', 'y', 'width', 'height', 'style')
        for attr in elem.attrib.keys():
            if not attr in ALLOWED_ATTRS:
                del elem.attrib[attr]

        elem.set('preserveAspectRatio', 'none')

        # embed?
        if not mimetype:
            elem.set(HREF_ATTR, file)
        else:
            if not src:
                if not hasattr(file, 'read'):
                    file = open(file, 'r')
                src = file.read()
            elem.set(HREF_ATTR, 'data:%s;base64,%s' % (
                mimetype, src.encode('base64')
            ))

    def set_svg(self, tid, src=None, file=None, dx=0, dy=0, scalex=1):
        if not (src == None) ^ (file == None):
            raise RuntimeError('Must specify exactly one of src or '
                               'file argument')

        if src:
            isrt = etree.fromstring(str(src))
        else:
            isrt = etree.parse(file)

        root = self._doc.getroot()

        # get the position x & Y of the square
        elem = self._rect_subs[tid]
        x = str( float(elem.get('x')) * scalex)
        y = float(elem.get('y'))

        # Fix for inkscape-generated pins templates
        height = float(isrt.getroot().get('height'))
        y = str(y - height)

        # remove the square
        elem.getparent().remove(elem)

        layer1 = self._doc.getroot().find(GRP_TAG)

        pin = isrt.find(GRP_TAG) # get the first layer
        fix_ids(pin) # change the ids to avoid any conflict
        pin.set('transform', 'scale (%s, 1) translate(%s, %s)' % (scalex, x,y))
        layer1.append(pin)

    def remove_group(self, tid):
        self._grp_subs[tid].getparent().remove(self._grp_subs[tid])

    def remove_rect(self, tid):
        self._rect_subs[tid].getparent().remove(self._rect_subs[tid])

    def __str__(self):
        return etree.tostring(self._doc)


load = Template.load
