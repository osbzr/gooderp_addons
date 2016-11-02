# -*- coding: utf-8 -*-
# © 2016 cole
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from docxtpl import DocxTemplate

import docx

import jinja2

"""
使用一个独立的类来封装需要支持图片等功能，避免污染report_docx.py
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
def picture(ctx,path,width=None, height=None,align=None):
    #转化为file-like对象
    if isinstance(path, bytes):
        import io
        path = io.BytesIO(path)
    else:
        #路径可以直接使用，不需要在这里转化为file
        pass



    tpl = ctx['tpl']
    doc = tpl.new_subdoc()

    if width:
        width=calc_length(width)
    if height:
        height=calc_length(height)
    
    # 如果不需要对齐，简便的方法
    # doc.add_picture(path,width=width,height=height)
    # 如果需要对齐 
    p = doc.add_paragraph()
    p.alignment = calc_alignment(align)
    p.add_run().add_picture(path,width=width,height=height)
    return doc


def get_env():
    """
    创建一个jinja的enviroment，然后添加了一个过滤器 
    """
    jinja_env = jinja2.Environment()
    jinja_env.filters['picture'] = picture
    return jinja_env

def test():
    
    tpl = DocxTemplate("tpls/test_tpl.docx")
 
    obj={'logo':'tpls/python_logo.png'}
    # 需要添加模版对象
    ctx={'obj':obj,'tpl':tpl}
    jinja_env = get_env()
    tpl.render(ctx,jinja_env)

    tpl.save('tpls/test.docx')

def main():
    test()


if __name__ == '__main__':
    main()
