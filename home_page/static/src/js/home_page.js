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
        on_click_top: function (e) {
            var self = this;
            e.preventDefault();
            var $button = $(e.currentTarget);
            var button_id = $button[0].id;
            var view_mode = _.contains((self.result_top[button_id])[1].split(','), 'tree') ? 'list' : 'form';
            var views = _.contains((self.result_top[button_id])[1].split(','), 'tree') ? [[self.result_top[button_id][5],
                'list'], [false, 'form']] : [[self.result_top[button_id][5], 'form']];
            var action={
                type: 'ir.actions.act_window',
                res_model: (self.result_top[button_id])[2],
                view_mode: view_mode,
                views: views,
                domain: self.result_top[button_id][3],
                context: self.result_top[button_id][4],
                name: self.result_top[button_id][6],
                target: self.result_top[button_id][7],
            }
            this.do_action(action, {clear_breadcrumbs: true});
        },
        on_click_quick: function (e) {
            //因为报表存在分区， 分区显示 所以 和第一第二模块的 数据处理不太一样，大同小异！

            var self  =this;
            var $li = $(e.currentTarget);
            var a_id = $li.attr('oe_top_link_i');
            var link_a_id = $li.attr('oe_top_link_j');
            var index_vals = self.result_quick[a_id][1];
            var view_mode = _.contains(index_vals[link_a_id][1].split(','), 'tree') ? 'list' : 'form';
            var views = _.contains(index_vals[link_a_id][1].split(','), 'tree') ? [[index_vals[link_a_id][5],
                'list'], [false, 'form']] : [[index_vals[link_a_id][5], 'form']];
            self.do_action({
                type: 'ir.actions.act_window',
                res_model: index_vals[link_a_id][2],
                view_mode: view_mode,
                name: index_vals[link_a_id][6],
                views: views,
                domain: index_vals[link_a_id][3],
                context: index_vals[link_a_id][4],
                target: index_vals[link_a_id][7],
            }, {
                clear_breadcrumbs: true,
            });
        },

        on_click_main: function (e) {
            var self  =this;
            var $a = $(e.currentTarget);
            var a_id = $a[0].id;
            var result_main = self.result_main;
            if (result_main[a_id][0] != result_main[a_id][1]) {
                var view_mode = _.contains((result_main[a_id])[1].split(','), 'tree') ? 'list' : 'form';
                var views = _.contains((result_main[a_id])[1].split(','), 'tree') ? [[result_main[a_id][6],
                    'list'], [false, 'form']] : [[result_main[a_id][6], 'form']];
                self.do_action({
                    type: 'ir.actions.act_window',
                    res_model: (result_main[a_id])[2],
                    view_mode: view_mode,
                    name: result_main[a_id][7],
                    view_type: result_main[a_id][1],
                    views: views,
                    domain: result_main[a_id][3],
                    context: result_main[a_id][5],
                    target: result_main[a_id][8],
                }, {
                    clear_breadcrumbs: true,
                });
            }
        },


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
                    var left_html_str = $("<div class='col-xs-12 col-md-" + row_num + " block-center text-center'>\
                          <button class='btn btn-primary button-circle oe_top_link_" + i + "' oe_top_link='" + i + "' id='" + i + "' style='width: 160px;height: 160px'>\
                          <h4>" + top_data[0] + "</h4>\
                          <h3>" + top_data[1] + "</h3>\
                          </button><p class='m-t-sm'></p></div>");
                    self.$el.find('.top_div').append(left_html_str);
                }
            }
        },
        thrid_part: function () {
            var index_last = 0;
            var self = this;
            var result_quick = self.result_quick;
            for (var i = 0; i < result_quick.length; i++) {
                var left_big_html_str = "<div class='col-xs-12 col-md-3 right_small_div_" + i + "'><a><h3>" + (result_quick[i][0].split(';'))[1] + "</h3></a></div>"
                self.$el.find('.right_div').append(left_big_html_str);
                for (var j = 0; j < result_quick[i][1].length; j++) {
                    var left_html_str = $(" <a><li  class='text-muted oe_p oe_quick_link' oe_top_link_i='" + i + "'  oe_top_link_j='" + j+ "' id='" + index_last + "'>" +
                        "<p>" + result_quick[i][1][j][6] + "</p></li></a>");
                    self.$el.find('.right_small_div_' + i).append(left_html_str);
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
                <p  class='btn  btn-primary btn-lg btn-block oe_main_link'  oe_main_link='" + index + "' id='" + index + "'>" + result_main[index][0] + "</p>\
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
                    /* 第er块的视图的构建 及跳转的逻辑 */
                    self.second_part();
                    /* 第san块的视图的构建 及跳转的逻辑 */
                    self.thrid_part()
                }
            });
        },
    });
    core.action_registry.add('home_page.homepage', HomePage);
})