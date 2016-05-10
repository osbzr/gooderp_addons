(function () {
    'use strict';

    var _t = openerp._t;

    openerp.Tour.register({
        id: 'test_export_view',
        name: _t("测试导出页面显示的内容!"),
        path: '/web',
        mode: 'test',
        // TODO : identify menu by data-menu attr or text node ?
        steps: [
            // Go to the first statement reconciliation
            {
                title:     "进入主菜单",
                element:   '.oe_menu_toggler:contains("配置"):visible',
            },
            {
                title:     "用户菜单",
                element:   '.oe_menu_leaf:contains("用户"):visible',
            },
           {
                title:     "选中要显示的数据",
                element:   'tr[data-id="1"] .oe_list_record_selector input[type="checkbox"]',
                popover:   { fixed: true },
            }, 
             {
                title:     "显示导出按钮",
                element:   'button[class="oe_dropdown_toggle oe_dropdown_arrow"]:contains("导出当前列表"):visible',
                popover:   { fixed: true },
            },
            {
                title:     "导出当前列表",
                element:   'li[class="oe_sidebar_export_view_xls"]:first-child',
                popover:   { fixed: true },
                autoComplete: function (tour) {}
            },
            {
                title:     "结束了",
            }
        ]
    });

}());
