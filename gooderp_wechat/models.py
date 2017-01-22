#encoding=utf-8

from xml.dom import minidom
import collections
import time


def kv2element(key, value, doc):
    ele = doc.createElement(key)
    if isinstance(value, str) or isinstance(value, unicode):
        data = doc.createCDATASection(value)
        ele.appendChild(data)
    else:
        text = doc.createTextNode(str(value))
        ele.appendChild(text)
    return ele


def fields2elements(tupleObj, enclose_tag=None, doc=None):
    if enclose_tag:
        xml = doc.createElement(enclose_tag)
        for key in tupleObj._fields:
            ele = kv2element(key, getattr(tupleObj, key), doc)
            xml.appendChild(ele)
        return xml
    else:
        return [kv2element(key, getattr(tupleObj, key), doc)
                for key in tupleObj._fields]

def element2dict(node):
    if node is None:
        return None

    child = node.firstChild
    if child is None:
        return None

    if child.nodeType == minidom.Node.CDATA_SECTION_NODE:
        return child.nodeValue
    elif child.nodeType == minidom.Node.TEXT_NODE:
        return child.data

    if node.childNodes:
        dic = {}
        child = node.firstChild
        while child is not None:
            if child.nodeType == minidom.Node.ELEMENT_NODE:
                dic[child.nodeName] = element2dict(child)
            child = child.nextSibling
        return dic
    else:
        return node.nodeValue

class WxRequest(object):

    def __init__(self, xml=None):
        if not xml:
            return
        doc = minidom.parseString(xml)
        self.__dict__ = element2dict(doc.firstChild)

class WxResponse(object):

    def __init__(self, request):
        self.CreateTime = long(time.time())
        self.ToUserName = request.FromUserName
        self.FromUserName = request.ToUserName
        self.Extra = {}

    def as_xml(self):
        doc = minidom.Document()
        xml = doc.createElement('xml')
        doc.appendChild(xml)
        xml.appendChild(kv2element('ToUserName', self.ToUserName, doc))
        xml.appendChild(kv2element('FromUserName', self.FromUserName, doc))
        xml.appendChild(kv2element('CreateTime', self.CreateTime, doc))
        xml.appendChild(kv2element('MsgType', self.MsgType, doc))
        contents = self.content_nodes(doc)
        if isinstance(contents, list) or isinstance(contents, tuple):
            for content in contents:
                xml.appendChild(content)
        else:
            xml.appendChild(contents)
        if self.Extra:
            for key, value in self.Extra.iteritems():
                xml.appendChild(kv2element(key, value, doc))
        return doc.toxml(encoding = 'utf-8')


WxMusic = collections.namedtuple('WxMusic',
                                 'Title Description MusicUrl HQMusicUrl')
WxArticle = collections.namedtuple('WxArticle',
                                   'Title Description PicUrl Url')
WxImage = collections.namedtuple('WxImage', 'MediaId')
WxVoice = collections.namedtuple('WxVoice', 'MediaId')
WxVideo = collections.namedtuple('WxVideo',
                                 'MediaId Title Description')
WxLink = collections.namedtuple('WxLink', 'Title Description Url')


class WxEmptyResponse(WxResponse):
    def __init__(self):
        pass

    def as_xml(self):
        return ''


class WxTextResponse(WxResponse):
    MsgType = 'text'

    def __init__(self, text, request):
        super(WxTextResponse, self).__init__(request)
        self.text = text

    def content_nodes(self, doc):
        return kv2element('Content', self.text, doc)


class WxCompoundResponse(WxResponse):
    MsgType = ''
    Tag = ''

    def __init__(self, data, request):
        super(WxCompoundResponse, self).__init__(request)
        self.data

    def content_nodes(self, doc):
        return self.fields2elements(self.data, self.Tag, doc)


class WxImageResponse(WxCompoundResponse):
    MsgType = 'image'
    Tag = 'Image'

class WxVoiceResponse(WxCompoundResponse):
    MsgType = 'voice'
    Tag = 'Voice'


class WxVideoResponse(WxCompoundResponse):
    MsgType = 'video'
    Tag = 'Video'


class WxMusicResponse(WxResponse):

    MsgType = 'music'
    Tag = 'Music'


class WxNewsResponse(WxResponse):

    MsgType = 'news'

    def __init__(self, articles, request):
        super(WxNewsResponse, self).__init__(request)
        if isinstance(articles, list):
            self.articles = articles
        else:
            self.articles = [articles]

    def content_nodes(self, doc):
        count = kv2element('ArticleCount', len(self.articles), doc)
        articles = doc.createElement('Articles')
        for article in self.articles:
            articles.appendChild(fields2elements(article, 'item', doc))
        return count, articles


class APIError(object):

    def __init__(self, code, msg):
        self.code = code
        self.message = msg
