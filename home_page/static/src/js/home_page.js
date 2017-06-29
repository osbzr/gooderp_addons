odoo.define('home_page', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var Model = require('web.Model');
    var session = require('web.session');
    var framework = require('web.framework');

    var QWeb = core.qweb;
    var _t = core._t;

    var HomePage = Widget.extend({
        events: {
            'click button[oe_top_link]': 'on_click_top',
            'click .oe_quick_link': 'on_click_quick',
            'click .oe_main_link': 'on_click_main',
        },
        commafy: function (num) {
            if(parseFloat(num)!=0) {
                var commafy_num = 0;
                if (num.indexOf('.') < 0) {
                    commafy_num = parseInt(num);
                } else {
                    commafy_num = parseInt(num.split('.')[0]);
                }
                return (commafy_num + '').replace(/(?=(?!\b)(\d{3})+$)/g, ',') + "." + num.split('.')[1];
            }else{
                return '0.0';
            }
        },
        /**
         *把后端传进来的action的数据进行还原 并且
         * 替换掉tree为list 因为在js里面 tree表示为list
         * */
        get_action_vals: function (vals) {
            vals[1] = vals[1].replace('tree','list');
            var view_mode_list = vals[1].split(',')
            var views = this.constract_views(view_mode_list, vals);
            return {
                type: 'ir.actions.act_window',
                res_model: vals[2],
                view_mode:  vals[1],
                views: views,
                domain: vals[3],
                context: vals[4],
                name: vals[6],
                target: vals[7],
            };
        },
        /***
         *针对传入的
         */
        constract_views: function (view_mode_list, vals) {
            var views = []
            if(typeof vals[5]=='object'){
                for(var i=0;i < (vals[5]).length;i++){
                    views.push([vals[5][i], view_mode_list[i]])
                }
            }else{
                for(var i=0;i < view_mode_list.length;i++){
                    views.push([false, view_mode_list[i]])
                }
            }
            return views
        },
        /***
         *以下三个on_clik 是点击事件，因为取值定位有差别所以要用三个方法
         *
         */
        on_click_top: function (e) {
            var self = this;
            e.preventDefault();
            var $button = $(e.currentTarget);
            var button_id = $button[0].id;
            this.do_action(self.get_action_vals(self.result_top[button_id]),
                          {clear_breadcrumbs: true});
        },
        on_click_quick: function (e) {
            //因为报表存在分区， 分区显示 所以 和第一第二模块的 数据处理不太一样，大同小异！
            var self  =this;
            var $li = $(e.currentTarget);
            var a_id = $li.attr('oe_top_link_i');
            var link_a_id = $li.attr('oe_top_link_j');
            var index_vals = self.result_quick[a_id][1];
            this.do_action(self.get_action_vals(index_vals[link_a_id]),
                          {clear_breadcrumbs: true});
        },

        on_click_main: function (e) {
            var self  =this;
            var $a = $(e.currentTarget);
            var a_id = $a[0].id;
            var result_main = self.result_main;
            if (result_main[a_id][0] != result_main[a_id][1]) {
                this.do_action(self.get_action_vals(result_main[a_id]),
                          {clear_breadcrumbs: true});
            }
        },
        /***
         *获取QWeb中的html的信息
         */
        three_part_qweb_render: function () {
            var top_fist = $(QWeb.render('top_fist_1'));
            var top_second = $(QWeb.render('top_second_2'));
            var top_third = $(QWeb.render('top_third_3'));
            var help_content = $(QWeb.render('help_content'));
            return {
                'top_fist': top_fist,
                'top_second': top_second,
                'top_third': top_third,
                'help_content':help_content
            }
        },
        /***
         *根据返回的数据判定三块数据 那块需要显示 没有相应的数据就不要显示了
         * */
        three_part_is_show: function (result, most_frame) {
            var self = this;
            var have_content = true;
            this.result_top=[];
            this.result_main =[];
            this.result_quick=[];
            if (result['top'].length) {
                self.$el.find('.main').append(most_frame.top_fist);
                this.result_top = result['top']
            }
            if (result['main'].length) {
                self.$el.find('.main').append(most_frame.top_second);
                var center_main_table = $(QWeb.render('center_main_table'));
                self.$el.find('.main_div').append(center_main_table);
                this.result_main = result['main']
            }
            if (result['right'].length) {
                self.$el.find('.main').append(most_frame.top_third);
                this.result_quick = result['right']
            }
            if (!(result['right'].length || result['main'].length || result['right'].length)) {
                self.$el.find('.main').append(most_frame.help_content);
                have_content = false
            }
            return have_content
        },
        second_part: function () {
            var self = this;
            var result_top = self.result_top;
            var row_num = result_top.length / 4 > 1 ? 3 : parseInt(12 / result_top.length);
            for (var i = 0; i < result_top.length; i++) {
                var top_data = this.result_top[i][0].split('  ');
                if ((i + 1) / 4 > parseInt(result_top.length / 4)) {
                    row_num = parseInt(12 / (result_top.length % 4)) == 0 ? 4 : parseInt(12 / (result_top.length % 4))
                }
                if (top_data.length == 2) {
                    var left_html_str = $("<div class='col-xs-6 col-sm-" + row_num + " block-center text-center'>\
                          <button class='btn btn-primary button-circle oe_top_link_" + i +
                        "' oe_top_link='" + i + "' id='" + i + "' style='width: 160px;height: 160px'>\
                          <h4>" + top_data[0] + "</h4>\
                          <h3>\
                          " +  self.commafy(top_data[1]) + "</h3>\
                          </button><p class='m-t-sm'></p></div>");
                    self.$el.find('.top_div').append(left_html_str);
                }
            }
        },
        third_part: function () {
            var index_last = 0;
            var self = this;
            var result_quick = self.result_quick;
            for (var i = 0; i < result_quick.length; i++) {
                var left_big_html_str = "<div class='col-xs-12 col-md-3 right_small_div_" + i + "'><h3>" +
                    (result_quick[i][0].split(';'))[1] + "</h3><ul class='list-group right_small_ul_"+i+"'></ul></div>"
                self.$el.find('.right_div').append(left_big_html_str);
                for (var j = 0; j < result_quick[i][1].length; j++) {
                    var left_html_str = $("<li  class='list-group-item oe_p oe_quick_link' oe_top_link_i='" + i + "' " +
                        " oe_top_link_j='" + j+ "' id='" + index_last + "'>" +
                        "<a><p>" + result_quick[i][1][j][6] + "</p></a></li>");
                    self.$el.find('.right_small_ul_' + i).append(left_html_str);
                    index_last++;
                }
            }
        },
        first_part: function () {
            var self = this;
            var index = 0;
            var result_main = self.result_main;
            var row_num = result_main.length / 4 > 1 ? 3 : parseInt(12 / result_main.length);
            for (var j = 0; j < result_main.length; j++) {
                var center_html_str = "<div class='col-sm-" + row_num + " col-xs-6'><div class='feature-item text-center'>\
                <p class='btn  btn-primary btn-lg btn-block oe_main_link'  oe_main_link='" + index
                    + "' id='" + index + "'>" + result_main[index][0] + "</p>\
                <p></p><p></p></div><div>";
                self.$el.find('.feature-list').append(center_html_str);
                if (row_num*(j+1)%12==0){
                    self.$el.find('.feature-list').append("<div class='span12'><br/></div>");
                }
                index++;
            }
        },
        start: function () {
            var num = this.get('value');
            var self = this;
            self.$el.append("<div id='main' class='main'></div>")
            /*首页分为三块  样式进行显示 分别是 数据统计  业务总览 实时报表 */
            var most_frame = this.three_part_qweb_render();
            new Model("home.page").call("get_action_url").then(function (result) {
                var index = 0;
                /* 三块 可以选择性的不显示某个 模块 */
                if (self.three_part_is_show(result, most_frame)) {
                    /* 第一块的视图的构建 及跳转的逻辑 */
                    self.first_part();
                    /* 第二块的视图的构建 及跳转的逻辑 */
                    self.second_part();
                    /* 第三块的视图的构建 及跳转的逻辑 */
                    self.third_part()
                }
            });
        },
    });
    core.action_registry.add('home_page.homepage', HomePage);
})