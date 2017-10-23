# -*- coding: utf-8 -*-
# © 2016 cole
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from docxtpl import DocxTemplate, InlineImage
import tempfile
import docx
import random
import os
import jinja2

"""
使用一个独立的文件来封装需要支持图片等功能，避免污染report_docx.py
"""

"""
需要安装python-docxtpl 0.4.6，使用InlineImage功能。
已安装旧版本，请使用pip install --upgrade docxtpl升级
"""

def calc_length(s):
    """
    把字符串，数字类型的参数转化为docx的长度对象，如：
    12 => Pt(12)
    '12' => Pt(12)
    '12pt' => Pt(12)  单位为point
    '12cm' => Cm(12)  单位为厘米
    '12mm' => Mm(12)   单位为毫米
    '12inchs' => Inchs(12)  单位为英寸
    '12emu' => Emu(12)
    '12twips' => Twips(12)
    """
    if not isinstance(s, str):
        # 默认为像素
        return docx.shared.Pt(s)

    if s.endswith('cm'):
        return docx.shared.Cm(float(s[:-2]))
    elif s.endswith('mm'):
        return docx.shared.Mm(float(s[:-2]))
    elif s.endswith('inchs'):
        return docx.shared.Inches(float(s[:-5]))
    elif s.endswith('pt') or s.endswith('px'):
        return docx.shared.Pt(float(s[:-2]))
    elif s.endswith('emu'):
        return docx.shared.Emu(float(s[:-3]))
    elif s.endswith('twips'):
        return docx.shared.Twips(float(s[:-5]))
    else:
        # 默认为像素
        return docx.shared.Pt(float(s))


def calc_alignment(s):
    """
    把字符串转换为对齐的常量
    """
    A = docx.enum.text.WD_ALIGN_PARAGRAPH
    if s=='center':
        return A.CENTER
    elif s=='left':
        return A.LEFT
    elif s=='right':
        return A.RIGHT
    else:
        return A.LEFT


@jinja2.contextfilter
def picture(ctx, data, width='40mm', height='40mm', align='center'):
    """
    把图片的二进制数据（使用了base64编码）转化为一个docx.Document对象

    data：图片的二进制数据（使用了base64编码）
    width：图片的宽度，可以为：'12cm','12mm','12pt' 等，参考前面的 calc_length()
    height：图片的长度，如果没有设置，根据长度自动缩放
    align：图片的位置，'left'，'center'，'right'
    """

    if not data:
        return None

    if width:
        width=calc_length(width)
    if height:
        height=calc_length(height)

    tempname = tempfile.mkdtemp()
    temppath = os.path.join(tempname, 'temp_%s_%s_%s_%s.%s' %
                 (os.getpid(), random.randint(1, 10000), ctx.get('id'), ctx.get('create_uid').id, 'png'))
    #data使用了base64编码，所以这里需要解码
    save_file(temppath, data.decode('base64'))
    return InlineImage(ctx['tpl'], temppath, width=width, height=height)

def save_file(folder_name, file):
    out_stream = open(folder_name, 'wb')
    try:
        out_stream.writelines(file)
    finally:
        out_stream.close()

def get_env():
    """
    创建一个jinja的enviroment，然后添加一个过滤器 
    """
    jinja_env = jinja2.Environment()
    jinja_env.filters['picture'] = picture
    return jinja_env

