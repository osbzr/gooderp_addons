# -*- coding: utf-8 -*-
from hashlib import sha1
import requests
import json
import tempfile
import shutil
import os
from .crypt import WXBizMsgCrypt

from .models import WxRequest, WxResponse
from .models import WxMusic, WxArticle, WxImage, WxVoice, WxVideo, WxLink
from .models import WxTextResponse, WxImageResponse, WxVoiceResponse,\
    WxVideoResponse, WxMusicResponse, WxNewsResponse, APIError, WxEmptyResponse

__all__ = ['WxRequest', 'WxResponse', 'WxMusic', 'WxArticle', 'WxImage',
           'WxVoice', 'WxVideo', 'WxLink', 'WxTextResponse',
           'WxImageResponse', 'WxVoiceResponse', 'WxVideoResponse',
           'WxMusicResponse', 'WxNewsResponse', 'WxApplication',
           'WxEmptyResponse', 'WxApi', 'APIError']

class Singleton(object):

    def __new__(cls, *args, **kw):
        if not hasattr(cls, '_instance'):
            orig = super(Singleton, cls)
            cls._instance = orig.__new__(cls, *args, **kw)
        return cls._instance

class WxApplication(Singleton):

    UNSUPPORT_TXT = u'暂不支持此类型消息'
    WELCOME_TXT = u'您好！感谢您的关注！'
    APP_ID = None
    SECRET = None
    TOKEN = None
    ENCODING_AES_KEY = None

    def is_valid_params(self, params):
        timestamp = params.get('timestamp', '')
        nonce = params.get('nonce', '')
        signature = params.get('signature', '')
        echostr = params.get('echostr', '')
        sign_ele = [self.token, timestamp, nonce]
        sign_ele.sort()
        if(signature == sha1(''.join(sign_ele)).hexdigest()):
            return True, echostr
        else:
            return None

    def process(self, params, xml=None, app_id=None, secret=None, token=None):
        self.app_id = app_id if app_id else self.APP_ID
        self.secret = secret if secret else self.SECRET
        self.token = token if token else self.TOKEN
        assert self.token is not None
        ret = self.is_valid_params(params)
        if not ret:
            return 'invalid request'
        if not xml:
            # 微信开发者设置的调用测试
            return ret[1]

        # 解密消息
        encrypt_type = params.get('encrypt_type', '')
        if encrypt_type != '' and encrypt_type != 'raw':
            msg_signature = params.get('msg_signature', '')
            timestamp = params.get('timestamp', '')
            nonce = params.get('nonce', '')
            if encrypt_type == 'aes':
                cpt = WXBizMsgCrypt(self.token,
                                    self.aes_key, self.app_id)
                err, xml = cpt.DecryptMsg(xml, msg_signature, timestamp, nonce)
                if err:
                    return 'decrypt message error, code : %s' % err
            else:
                return 'unsupport encrypty type %s' % encrypt_type

        req = WxRequest(xml)
        self.wxreq = req
        func = self.handler_map().get(req.MsgType, None)
        if not func:
            return WxTextResponse(self.UNSUPPORT_TXT, req)
        self.pre_process()
        rsp = func(req)
        self.post_process(rsp)
        result = rsp.as_xml()
        # 加密消息
        if encrypt_type != '' and encrypt_type != 'raw':
            if encrypt_type == 'aes':
                err, result = cpt.EncryptMsg(result, nonce)
                if err:
                    return 'encrypt message error , code %s' % err
            else:
                return 'unsupport encrypty type %s' % encrypt_type
        return result

    def on_text(self, text):
        return WxTextResponse(self.UNSUPPORT_TXT, text)

    def on_link(self, link):
        return WxTextResponse(self.UNSUPPORT_TXT, link)

    def on_image(self, image):
        return WxTextResponse(self.UNSUPPORT_TXT, image)

    def on_voice(self, voice):
        return WxTextResponse(self.UNSUPPORT_TXT, voice)

    def on_video(self, video):
        return WxTextResponse(self.UNSUPPORT_TXT, video)

    def on_location(self, loc):
        return WxTextResponse(self.UNSUPPORT_TXT, loc)

    def event_map(self):
        if getattr(self, 'event_handlers', None):
            return self.event_handlers
        return {
            'subscribe': self.on_subscribe,
            'unsubscribe': self.on_unsubscribe,
            'SCAN': self.on_scan,
            'LOCATION': self.on_location_update,
            'CLICK': self.on_click,
            'VIEW': self.on_view,
            'click': self.on_click,
            'scancode_push': self.on_scancode_push,
            'scancode_waitmsg': self.on_scancode_waitmsg,
            'pic_sysphoto': self.on_pic_sysphoto,
            'pic_photo_or_album': self.on_pic_photo_or_album,
            'pic_weixin': self.on_pic_weixin,
            'location_select': self.on_location_select,
            'enter_agent': self.on_enter_agent, #进入某应用
            'view': self.on_view, #进入某页面？
        }

    def on_event(self, event):
        func = self.event_map().get(event.Event, None)
        return func(event)

    def on_subscribe(self, sub):
        return WxTextResponse(self.WELCOME_TXT, sub)

    def on_unsubscribe(self, unsub):
        return WxEmptyResponse()

    def on_click(self, click):
        return WxEmptyResponse()

    def on_scan(self, scan):
        return WxEmptyResponse()

    def on_location_update(self, location):
        return WxEmptyResponse()

    def on_view(self, view):
        return WxEmptyResponse()

    def on_scancode_push(self, event):
        return WxEmptyResponse()

    def on_scancode_waitmsg(self, event):
        return WxEmptyResponse()

    def on_pic_sysphoto(self, event):
        return WxEmptyResponse()

    def on_pic_photo_or_album(self, event):
        return WxEmptyResponse()

    def on_pic_weixin(self, event):
        return WxEmptyResponse()

    def on_location_select(self, event):
        return WxEmptyResponse()

    def on_enter_agent(self, event):
        return WxEmptyResponse()

    def on_view(self, event):
        return WxEmptyResponse()

    def handler_map(self):
        if getattr(self, 'handlers', None):
            return self.handlers
        return {
            'text': self.on_text,
            'link': self.on_link,
            'image': self.on_image,
            'voice': self.on_voice,
            'video': self.on_video,
            'location': self.on_location,
            'event': self.on_event,
        }

    def pre_process(self):
        pass

    def post_process(self, rsp):
        pass


class WxBaseApi(object):

    API_PREFIX = 'https://api.weixin.qq.com/cgi-bin/'

    def __init__(self, appid, appsecret, api_entry=None):
        self.appid = appid
        self.appsecret = appsecret
        self._access_token = None
        self.api_entry = api_entry or self.API_PREFIX

    @property
    def access_token(self):
        if not self._access_token:
            token, err = self.get_access_token()
            if not err:
                self._access_token = token['access_token']
                return self._access_token
            else:
                return None
        return self._access_token

    def set_access_token(self, token):
        self._access_token = token

    def _process_response(self, rsp):
        if rsp.status_code != 200:
            return None, APIError(rsp.status_code, 'http error')
        try:
            content = rsp.json()
        except:
            return None, APIError(99999, 'invalid rsp')
        if 'errcode' in content and content['errcode'] != 0:
            return None, APIError(content['errcode'], content['errmsg'])
        return content, None

    def _get(self, path, params=None):
        if not params:
            params = {}
        params['access_token'] = self.access_token
        rsp = requests.get(self.api_entry + path, params=params,
                           verify=False)
        return self._process_response(rsp)

    def _post(self, path, data, ctype='json'):
        headers = {'Content-type': 'application/json'}
        path = self.api_entry + path
        if '?' in path:
            path += '&access_token=' + self.access_token
        else:
            path += '?access_token=' + self.access_token
        if ctype == 'json':
            data = json.dumps(data, ensure_ascii=False).encode('utf-8')
        rsp = requests.post(path, data=data, headers=headers, verify=False)
        return self._process_response(rsp)

    def upload_media(self, mtype, file_path=None, file_content=None,
                     url='media/upload', suffies=None):
        path = self.api_entry + url + '?access_token=' \
            + self.access_token + '&type=' + mtype
        suffies = suffies or {'image': '.jpg', 'voice': '.mp3',
                              'video': 'mp4', 'thumb': 'jpg'}
        suffix = None
        if mtype in suffies:
            suffix = suffies[mtype]
        if file_path:
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            shutil.copy(file_path, tmp_path)
            os.close(fd)
        elif file_content:
            fd, tmp_path = tempfile.mkstemp(suffix=suffix)
            f = os.fdopen(fd, 'wb')
            f.write(file_content)
            f.close()
        media = open(tmp_path, 'rb')
        rsp = requests.post(path, files={'media': media},
                            verify=False)
        media.close()
        os.remove(tmp_path)
        return self._process_response(rsp)

    def download_media(self,  media_id, to_path, url='media/get'):
        rsp = requests.get(self.api_entry + url,
                           params={'media_id': media_id,
                                   'access_token': self.access_token},
                           verify=False)
        if rsp.status_code == 200:
            save_file = open(to_path, 'wb')
            save_file.write(rsp.content)
            save_file.close()
            return {'errcode': 0}, None
        else:
            return None, APIError(rsp.status_code, 'http error')

    def _get_media_id(self, obj, resource, content_type):
        if not obj.get(resource + '_id'):
            rsp, err = None, None
            if obj.get(resource + '_content'):
                rsp, err = self.upload_media(
                    content_type,
                    file_content=obj.get(resource + '_content'))
                if err:
                    return None
            elif obj.get(resource + '_url'):
                rs = requests.get(obj.get(resource + '_url'))
                rsp, err = self.upload_media(
                    content_type,
                    file_content=rs.content)
                if err:
                    return None
            else:
                return None
            return rsp['media_id']
        return obj.get(resource + '_id')


class WxApi(WxBaseApi):

    def get_access_token(self, url=None, **kwargs):
        params = {'grant_type': 'client_credential', 'appid': self.appid,
                  'secret': self.appsecret}
        if kwargs:
            params.update(kwargs)
        rsp = requests.get(url or self.api_entry + 'token', params=params,
                           verify=False)
        return self._process_response(rsp)

    def user_info(self, user_id, lang='zh_CN'):
        return self._get('user/info', {'openid': user_id, 'lang': lang})

    def followers(self, next_id=''):
        return self._get('user/get', {'next_openid': next_id})

    def send_message(self, to_user, msg_type, content):
        func = {'text': self.send_text,
                'image': self.send_image,
                'voice': self.send_voice,
                'video': self.send_video,
                'music': self.send_music,
                'news': self.send_news}.get(msg_type, None)
        if func:
            return func(to_user, content)
        return None, None

    def send_text(self, to_user, content):
        return self._post('message/custom/send',
                          {'touser': to_user, 'msgtype': 'text',
                           'text': {'content': content}})

    def send_image(self, to_user, media_id=None, media_url=None):
        if media_id and media_id.startswith('http'):
            media_url = media_id
            media_id = None
        mid = self._get_media_id(
            {'media_id': media_id, 'media_url': media_url},
            'media', 'image')
        return self._post('message/custom/send',
                          {'touser': to_user, 'msgtype': 'image',
                           'image': {'media_id': mid}})

    def send_voice(self, to_user, media_id=None, media_url=None):
        if media_id and media_id.startswith('http'):
            media_url = media_id
            media_id = None
        mid = self._get_media_id(
            {'media_id': media_id, 'media_url': media_url},
            'media', 'voice')
        return self._post('message/custom/send',
                          {'touser': to_user, 'msgtype': 'voice',
                           'voice': {'media_id': mid}})

    def send_music(self, to_user, music):
        music['thumb_media_id'] = self._get_media_id(music,
                                                     'thumb_media',
                                                     'image')
        if not music.get('thumb_media_id'):
            return None, APIError(41006, 'missing media_id')
        return self._post('message/custom/send',
                          {'touser': to_user, 'msgtype': 'music',
                           'music': music})

    def send_video(self, to_user, video):
        video['media_id'] = self._get_media_id(video, 'media', 'video')
        video['thumb_media_id'] = self._get_media_id(video,
                                                     'thumb_media', 'image')
        if 'media_id' not in video or 'thumb_media_id' not in video:
            return None, APIError(41006, 'missing media_id')
        return self._post('message/custom/send',
                          {'touser': to_user, 'msgtype': 'video',
                           'video': video})

    def send_news(self, to_user, news):
        if isinstance(news, dict):
            news = [news]
        return self._post('message/custom/send',
                          {'touser': to_user, 'msgtype': 'news',
                           'news': {'articles': news}})

    def create_group(self, name):
        return self._post('groups/create',
                          {'group': {'name': name}})

    def groups(self):
        return self._get('groups/get')

    def update_group(self, group_id, name):
        return self._post('groups/update',
                          {'group': {'id': group_id, 'name': name}})

    def group_of_user(self, user_id):
        return self._get('groups/getid', {'openid': user_id})

    def move_user_to_group(self, user_id, group_id):
        return self._post('groups/members/update',
                          {'openid': user_id, 'to_groupid': group_id})

    def create_menu(self, menus):
        return self._post('menu/create', menus, ctype='text')

    def get_menu(self):
        return self._get('menu/get')

    def delete_menu(self):
        return self._get('menu/delete')

    def customservice_records(self, starttime, endtime, openid=None,
                              pagesize=100, pageindex=1):
        return self._get('customservice/getrecord',
                         {'starttime': starttime,
                          'endtime': endtime,
                          'openid': openid,
                          'pagesize': pagesize,
                          'pageindex': pageindex})
