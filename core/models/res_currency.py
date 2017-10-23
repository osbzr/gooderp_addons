# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResCurrency(models.Model):
    _inherit = 'res.currency'

    company_id = fields.Many2one(
        'res.company',
        string=u'公司',
        change_default=True,
        default=lambda self: self.env['res.company']._company_default_get())

    @api.model
    def rmb_upper(self, value):
        """
        人民币大写
        来自：http://topic.csdn.net/u/20091129/20/b778a93d-9f8f-4829-9297-d05b08a23f80.html
        传入浮点类型的值返回 unicode 字符串
        :param 传入阿拉伯数字
        :return 返回值是对应阿拉伯数字的绝对值的中文数字
        """
        rmbmap = [u"零", u"壹", u"贰", u"叁", u"肆", u"伍", u"陆", u"柒", u"捌", u"玖"]
        unit = [u"分", u"角", u"元", u"拾", u"佰", u"仟", u"万", u"拾", u"佰", u"仟", u"亿",
                u"拾", u"佰", u"仟", u"万", u"拾", u"佰", u"仟", u"兆"]
        # 冲红负数处理
        xflag = 0
        if value < 0:
            xflag = value
            value = abs(value)
        # 先把value 数字进行格式化保留两位小数，转成字符串然后去除小数点
        nums = map(int, list(str('%0.2f' % value).replace('.', '')))
        words = []
        zflag = 0  # 标记连续0次数，以删除万字，或适时插入零字
        start = len(nums) - 3
        for i in range(start, -3, -1):  # 使i对应实际位数，负数为角分
            # 大部分情况对应数字不等于零 或者是刚开始循环
            if 0 != nums[start - i] or len(words) == 0:
                if zflag:
                    words.append(rmbmap[0])
                    zflag = 0
                words.append(rmbmap[nums[start - i]])   # 数字对应的中文字符
                words.append(unit[i + 2])               # 列表此位置的单位
            # 控制‘万/元’ 万和元比较特殊，如2拾万和2拾1万 无论有没有这个1 万字是必须的
            elif 0 == i or (0 == i % 4 and zflag < 3):
                # 上面那种情况定义了 2拾1万 的显示 这个是特殊对待的 2拾万（一类）的显示
                words.append(unit[i + 2])
                # 元（控制条件为 0 == i ）和万(控制条为(0 == i % 4 and zflag < 3))的情况的处理是一样的
                zflag = 0
            else:
                zflag += 1
        if words[-1] != unit[0]:  # 结尾非‘分’补整字 最小单位 如果最后一个字符不是最小单位(分)则要加一个整字
            words.append(u"整")
        if xflag < 0:             # 如果为负数则要在数字前面加上‘负’字
            words.insert(0, u"负")
        return ''.join(words)
