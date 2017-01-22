#encoding=utf-8
import simplejson
import requests
import time
import urllib
import urllib2
from .models import WxRequest, WxResponse
from .models import WxArticle, WxImage, WxVoice, WxVideo, WxLink
from .models import WxTextResponse, WxImageResponse, WxVoiceResponse,\
    WxVideoResponse, WxNewsResponse, APIError, WxEmptyResponse
from .official import WxApplication as BaseApplication, WxBaseApi
from .crypt import WXBizMsgCrypt



__all__ = ['WxRequest', 'WxResponse', 'WxArticle', 'WxImage',
           'WxVoice', 'WxVideo', 'WxLink', 'WxTextResponse',
           'WxImageResponse', 'WxVoiceResponse', 'WxVideoResponse',
           'WxNewsResponse', 'WxApplication',
           'WxApi', 'APIError']


class WxApplication(BaseApplication):

    UNSUPPORT_TXT = u'暂不支持此类型消息'
    WELCOME_TXT = u'你好！感谢您的关注！'
    SECRET_TOKEN = None
    CORP_ID = None
    ENCODING_AES_KEY = None

    def process(self, params, xml=None, token=None, corp_id=None,
                aes_key=None):
        self.token = token or self.SECRET_TOKEN
        self.corp_id = corp_id or self.CORP_ID
        self.aes_key = aes_key or self.ENCODING_AES_KEY
        assert self.token is not None
        assert self.corp_id is not None
        assert self.aes_key is not None
        timestamp = params.get('timestamp', '')
        nonce = params.get('nonce', '')
        msg_signature = params.get('msg_signature', '')
        echostr = params.get('echostr', '')
        cpt = WXBizMsgCrypt(self.token, self.aes_key, self.corp_id)
        #判断是否是首次接入
        if echostr != '':
            ret,echostr_plain = cpt.VerifyURL(msg_signature, timestamp, nonce, echostr)
            if ret == 0:
                return echostr_plain
            else:
                raise Exception(u'invalid request: %s' % ret)
        # 解密消息`
        err, decode_xml = cpt.DecryptMsg(xml, msg_signature, timestamp, nonce)
        if err:
            raise Exception(u'decrypt message error, code : %s' % err)
        self.req = WxRequest(decode_xml)
        if hasattr(self.req, 'AgentType'):
            if self.req.AgentType=='kf_internal':
                return self.kf_internal_return(self.req)
            return self.req.PackageId
        func = self.handler_map().get(self.req.MsgType, None)
        if not func:
            return WxEmptyResponse()
        self.pre_process()
        rsp = func(self.req)
        self.post_process(rsp)
        result = rsp.as_xml().encode('UTF-8')
        if not result:
            return ''
        err, result = cpt.EncryptMsg(result, nonce)
        if err:
            raise Exception(u'encrypt message error , code %s' % err)
        return result


    def kf_internal_return(self,req):
        message_dict=req.Item
        if message_dict.get('MsgType')=='event' and message_dict.get('Event')=='subscribe':
            result= req.PackageId
        elif message_dict.get('MsgType')=='text':
            result={'PackageId':req.PackageId,'content':message_dict.get('Content'),'to_user_id':message_dict.get('Receiver').get('Id'),'from_user_id':message_dict.get('FromUserName')}

        elif message_dict.get('MsgType')=='image' or message_dict.get('MsgType')=='voice' :
            result = {'PackageId': req.PackageId, 'content': message_dict.get('Content'),
                      'to_user_id': message_dict.get('Receiver').get('Id'),
                      'from_user_id': message_dict.get('FromUserName'),'MsgType':message_dict.get('MsgType'),'MediaId':message_dict.get('MediaId'),'media_url': message_dict.get('PicUrl')}
        return result

    #http请求微信验证后再跳转回来
    def oauth_authorize_redirect_url(self, db_name, redirect_uri, state_params):
        state = {'db': db_name, 'agentid': self.APP_ID or 0}
        state.update(state_params)
        string_state = '(' + simplejson.dumps(state)[1:-1] + ')'
        if redirect_uri and not redirect_uri.startswith('http'):
            redirect_uri = 'http://' + redirect_uri
        if not self.CORP_ID:
            raise Exception("当前WxApplication实例没有self.CORP_ID, ")
        url = WxApi.authorize_url(self.CORP_ID, redirect_uri, state=string_state)
        #url = "%s?appid=%s&redirect_uri=%s&response_type=code&scope=snsapi_base&state=(%s)#wechat_redirect" % (validation_endpoint, self.CORP_ID, redirect_uri, string_state)
        print '------ wechat_redirect url:', url
        return url

def format_list(data):
    if data and (isinstance(data, list) or isinstance(data, tuple)):
        return '|'.join(data)
    else:
        return data


def simplify_send_parmas(params):
    keys = params.keys()
    for key in keys:
        if not params[key]:
            del params[key]
    return params


class WxApi(WxBaseApi):

    API_PREFIX = 'https://qyapi.weixin.qq.com/'

    def __init__(self, appid, appsecret, api_entry=None):
        super(WxApi, self).__init__(appid, appsecret, api_entry)
        self.expires_in = time.time()

    @property
    def access_token(self):
        if self._access_token and time.time() >= self.expires_in:
            self._access_token = None

        if not self._access_token:
            token, err = self.get_access_token()
            if not err:
                self._access_token = token['access_token']
                self.expires_in = time.time() + token['expires_in']
                return self._access_token
            else:
                return None
        return self._access_token

    def get_access_token(self, url=None, **kwargs):
        params = {'corpid': self.appid, 'corpsecret': self.appsecret}
        params.update(kwargs)
        rsp = requests.get(url or self.api_entry + 'cgi-bin/gettoken',
                           params=params,
                           verify=False)
        return self._process_response(rsp)

    def departments(self):
        return self._get('cgi-bin/department/list')

    def add_department(self, name, parentid='1', order=None):
        return self._post('cgi-bin/department/create',
                          params={'name': name, 'parentid': parentid,
                                  'order': order})

    def update_department(self, depid, name=None, parentid=None, order=None):
        return self._post('cgi-bin/department/update',
                          params={'id': depid, 'name': name,
                                  'parentid': parentid, 'order': order})

    def delete_department(self, depid):
        return self._get('cgi-bin/department/delete', params={'id': depid})

    def tags(self):
        return self._get('cgi-bin/tag/list')

    def add_tag(self, tagname):
        return self._post('cgi-bin/tag/create', {'tagname': tagname})

    def update_tag(self, tagid, tagname):
        return self._post('cgi-bin/tag/update',
                          {'tagid': tagid, 'tagname': tagname})

    def delete_tag(self, tagid):
        return self._get('cgi-bin/tag/delete', params={'tagid': tagid})

    def tag_users(self, tagid):
        return self._get('cgi-bin/tag/get', params={'tagid': tagid})

    def add_tag_user(self, tagid, userlist):
        return self._post('cgi-bin/tag/addtagusers',
                          {'tagid': tagid, 'userlist': userlist})

    def remove_tag_user(self, tagid, userlist):
        return self._post('cgi-bin/tag/deltagusers',
                          {'tagid': tagid, 'userlist': userlist})

    def department_users(self, department_id, fetch_child=0, status=0):
        return self._get('cgi-bin/user/simplelist',
                         params={'department_id': department_id,
                                 'fetch_child': fetch_child,
                                 'status': status})

    def add_user(self, userid, name, department=None, position=None,
                 mobile=None, gender=None, tel=None, email=None,
                 weixinid=None, extattr=None):
        params = {
            "userid": userid,
            "name": name,
            "department": department,
            "position": position,
            "mobile": mobile,
            "gender": gender,
            "tel": tel,
            "email": email,
            "weixinid": weixinid,
            "extattr": extattr,
            }
        return self._post('cgi-bin/user/create', params)

    def update_user(self, userid, name, department=None, position=None,
                    mobile=None, gender=None, tel=None, email=None,
                    weixinid=None, extattr=None):
        params = {
            "userid": userid,
            "name": name,
            "department": department,
            "position": position,
            "mobile": mobile,
            "gender": gender,
            "tel": tel,
            "email": email,
            "weixinid": weixinid,
            "extattr": extattr,
            }
        return self._post('cgi-bin/user/update', params)

    def delete_user(self, userid):
        return self._get('cgi-bin/user/delete',
                         params={'userid': userid})

    def get_kf_list(self):
        return self._get('cgi-bin/kf/list')

    def upload_media(self, mtype, file_path=None, file_content=None):
        return super(WxApi, self).upload_media(
            mtype, file_path=file_path, file_content=file_content,
            url='cgi-bin/media/upload',
            suffies={'image': '.jpg', 'voice': '.mp3',
                              'video': '.mp4', 'file': ''})

    def download_media(self, media_id, to_path):
        return super(WxApi, self).download_media(
            media_id, to_path, 'cgi-bin/media/get')

    def send_message(self, msg_type, content, agentid, safe="0", touser=None,
                     toparty=None, totag=None, **kwargs):
        func = {'text': self.send_text,
                'image': self.send_image,
                'voice': self.send_voice,
                'video': self.send_video,
                'file': self.send_file,
                'news': self.send_news,
                'mpnews': self.send_mpnews}.get(msg_type, None)
        if func:
            return func(content, agentid, safe=safe, touser=touser,
                        toparty=toparty, totag=totag, **kwargs)
        else:
            return None, None

    def send_text(self, content, agentid, safe="0", touser=None,
                  toparty=None, totag=None):
        return self._post(
            'cgi-bin/message/send',
            simplify_send_parmas({'touser': format_list(touser),
                                  'toparty': format_list(toparty),
                                  'totag': format_list(totag),
                                  'msgtype': 'text',
                                  'agentid': agentid,
                                  'safe': safe,
                                  'text': {'content': content}
                                  }))

    def send_kf_text(self,sender_receiver_message):
        return self._post(
            'cgi-bin/kf/send',
            simplify_send_parmas(sender_receiver_message))


    def send_simple_media(self, mtype, media_id, agentid, safe="0",
                          touser=None, toparty=None, totag=None,
                          media_url=None):
        if media_id and media_id.startswith('http'):
            media_url = media_id
            media_id = None
        mid = self._get_media_id(
            {'media_id': media_id, 'media_url': media_url},
            'media', mtype)
        return self._post(
            'cgi-bin/message/send',
            simplify_send_parmas({'touser': format_list(touser),
                                  'toparty': format_list(toparty),
                                  'totag': format_list(totag),
                                  'msgtype': mtype,
                                  'agentid': agentid,
                                  'safe': safe,
                                  mtype: {'media_id': media_id}
                                  }))

    def send_image(self, media_id, agentid, safe="0", touser=None,
                   toparty=None, totag=None, media_url=None):
        return self.send_simple_media('image', media_id, agentid, safe,
                                      touser, toparty, totag, media_url)

    def send_voice(self, media_id, agentid, safe="0", touser=None,
                   toparty=None, totag=None, media_url=None):
        return self.send_simple_media('voice', media_id, agentid, safe,
                                      touser, toparty, totag, media_url)

    def send_file(self, media_id, agentid, safe="0", touser=None,
                  toparty=None, totag=None, media_url=None):
        return self.send_simple_media('file', media_id, agentid, safe,
                                      touser, toparty, totag, media_url)

    def send_video(self, video, agentid, safe="0", touser=None,
                   toparty=None, totag=None, media_url=None):
        video['media_id'] = self._get_media_id(video, 'media', 'video')
        if 'media_url' in video:
            del video['media_url']
        return self._post(
            'cgi-bin/message/send',
            simplify_send_parmas({'touser': format_list(touser),
                                  'toparty': format_list(toparty),
                                  'totag': format_list(totag),
                                  'msgtype': 'video',
                                  'agentid': agentid,
                                  'safe': safe,
                                  'video': video}))

    def send_news(self, news, agentid, safe="0", touser=None,
                  toparty=None, totag=None, media_url=None):
        if isinstance(news, dict):
            news = [news]
        return self._post(
            'cgi-bin/message/send',
            simplify_send_parmas({'touser': format_list(touser),
                                  'toparty': format_list(toparty),
                                  'totag': format_list(totag),
                                  'msgtype': 'news',
                                  'agentid': agentid,
                                  'safe': safe,
                                  'news': {'articles': news}}))

    def send_mpnews(self, mpnews, agentid, safe="0", touser=None,
                    toparty=None, totag=None, media_url=None):
        if isinstance(mpnews, dict):
            news = [mpnews]
        return self._post(
            'cgi-bin/message/send',
            simplify_send_parmas({'touser': format_list(touser),
                                  'toparty': format_list(toparty),
                                  'totag': format_list(totag),
                                  'msgtype': 'mpnews',
                                  'agentid': agentid,
                                  'safe': safe,
                                  'mpnews': {'articles': news}}))

    def create_menu(self, menus, agentid):
        return self._post('cgi-bin/menu/create?agentid=%s' % agentid,
                          repr(menus), ctype='text')

    def get_menu(self, agentid):
        return self._get('cgi-bin/menu/get', {'agentid': agentid})

    def delete_menu(self, agentid):
        return self._get('cgi-bin/menu/delete', {'agentid': agentid})

    # OAuth2
    @classmethod
    def authorize_url(self, appid, redirect_uri, response_type='code',
                      scope='snsapi_base', state=None):
        # 变态的微信实现，参数的顺序也有讲究。。艹！这个实现太恶心，太恶心！
        rd_uri = urllib.urlencode({'redirect_uri': redirect_uri})
        url = 'https://open.weixin.qq.com/connect/oauth2/authorize?'
        url += 'appid=%s&' % appid
        url += rd_uri
        url += '&response_type=' + response_type
        url += '&scope=' + scope
        if state:
            url += '&state=' + state
        return url + '#wechat_redirect'

    def get_user_info(self, agentid, code):
        return self._get('cgi-bin/user/getuserinfo',
                         {'agentid': agentid, 'code': code})
