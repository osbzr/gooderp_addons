#!/usr/bin/env python
# -*- coding: utf-8 -*-
#########################################################################
# Author: jonyqin
# Created Time: Thu 11 Sep 2014 01:53:58 PM CST
# File Name: ierror.py
# Description:定义错误码含义
#########################################################################
# 0	请求成功
WXBizMsgCrypt_OK = 0
# -40001	签名验证错误
WXBizMsgCrypt_ValidateSignature_Error = -40001
# -40002	xml解析失败
WXBizMsgCrypt_ParseXml_Error = -40002
# -40003	sha加密生成签名失败
WXBizMsgCrypt_ComputeSignature_Error = -40003
# -40004	AESKey 非法
WXBizMsgCrypt_IllegalAesKey = -40004
# 40005	corpid 校验错误
WXBizMsgCrypt_ValidateCorpid_Error = -40005
# -40006	AES 加密失败
WXBizMsgCrypt_EncryptAES_Error = -40006
# -40007	AES 解密失败
WXBizMsgCrypt_DecryptAES_Error = -40007
# -40008	解密后得到的buffer非法
WXBizMsgCrypt_IllegalBuffer = -40008
# -40009	base64加密失败
WXBizMsgCrypt_EncodeBase64_Error = -40009
# -40010	base64解密失败
WXBizMsgCrypt_DecodeBase64_Error = -40010
# -40011	生成xml失败
WXBizMsgCrypt_GenReturnXml_Error = -40011
# 60008 部门已经存在错误
DepartmentExisted_Error = 60008
# 600102 成员 userid 已经存在
UseridExisted_Error = 60102
# 60108 成员weixinid 已经存在
WeixinidExisted_Error = 60108
# 60104 成员手机号已经存在
MobileEXisted_Error = 60104
# 60106 成员 email 已经存在
EmailExisted_Error = 60106
