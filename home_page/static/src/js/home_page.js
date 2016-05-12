openerp.home_page = function(instance, local) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    local.HomePage = instance.Widget.extend({
        start: function() {
            var num=this.get('value');
            var self=this
            self.$el.append("<div class='container-fluid'><div class='row'>\
                                    <div  class='top_div col-md-3'></div>\
                                    <div  class='main_div col-md-8'></div>\
                                    <div class='right_div col-md-1'></div>\
                                    </div></div>")
            new instance.web.Model("home.page").call("get_action_url").then(function(result){
                var index=0
                var center_main_table="<div class='center_class'><table border='1' cellpadding='3' class='oe_table_main'></table></div>"
                self.$el.find('.main_div').append(center_main_table);
                self.result_main=result['main']
                for(var i=0;i<2;i++){
                    var center_tr_html="<tr class='oe_tr_"+i+"'></tr>"
                    self.$el.find('.oe_table_main').append(center_tr_html);
                    for(var j=0;j<4;j++){
                        var result_one=self.result_main[index]
                        if (result_one===undefined){
                            result_one=[0,0,0,0,'web/binary/company_logo?db=hahh&company=1']
                        }else{
                            result_one[4]="/web/binary/image?model=home.page&id="+result_one[4]+"&field=image"
                        }
                        var center_html_str="<td ><img class='oe_img oe_main_link_"+index+"' id='"+index+"' height='150' \
                         width='150' src='"+result_one[4]+"' alt='暂无快捷菜单链接' />\
                        <br/><p>"+result_one[0]+"</p>\
                        </td>"
                        self.$el.find('.oe_tr_'+i+'').append(center_html_str);
                        if (result_one[0]!=result_one[1]){
                            self.$(".oe_main_link_"+index+"").click(function() {
                                 self.do_action({
                                    type: 'ir.actions.act_window',
                                    res_model: (self.result_main[this.id])[2],
                                    view_mode: 'list',
                                    name:self.result_main[this.id][7],
                                    view_type: self.result_main[this.id][1],
                                    views: [[self.result_main[this.id][6], 'list'],[false, 'form']],
                                    domain:self.result_main[this.id][3],
                                    context:self.result_main[this.id][5],
                                    target: 'current',
                                });
                            });
                        }
                        index++;
                    }
                }
                self.result_top=result['top']
                for(var i=0;i< 5;i++){
                    if (self.result_top[i]!==undefined){
                        var left_html_str = $("<p ><a class='oe_p oe_top_link_"+i+"' id='"+i+"'>"+self.result_top[i][0]+"</a></p> ");
                        self.$el.find('.top_div').append(left_html_str);
                        self.$(".oe_top_link_"+i+"").click(function() {
                             self.do_action({
                                type: 'ir.actions.act_window',
                                res_model: (self.result_top[this.id])[2],
                                view_mode: 'list',
                                /*view_type: self.result_top[this.id][1],*/
                                views: [[self.result_top[this.id][5], 'list'],[false, 'form']],
                                domain:self.result_top[this.id][3],
                                context:self.result_top[this.id][4],
                                name:self.result_top[this.id][6],
                                target: 'current',
                            });
                        });
                    }
                }
                self.result_quick=result['right']
                for(var i=0;i< 8;i++){
                    if (self.result_quick[i]!==undefined){
                        var left_html_str = $("<a><p class='oe_p oe_quick_link_"+i+"' id='"+i+"'>"+self.result_quick[i][0]+"</p></a>");
                        self.$el.find('.right_div').append(left_html_str);
                        self.$(".oe_quick_link_"+i+"").click(function() {
                             self.do_action({
                                type: 'ir.actions.act_window',
                                res_model: (self.result_quick[this.id])[2],
                                view_mode: 'list',
                                name:self.result_quick[this.id][6],
                                /*view_type: self.result_quick[this.id][1],*/
                                views: [[self.result_quick[this.id][5], 'list'],[false, 'form']],
                                domain:self.result_quick[this.id][3],
                                context:self.result_quick[this.id][4],
                                target: 'current',
                            });
                        });
                    }
                }

             });
        },
    });
    instance.web.client_actions.add('home_page.homepage', 'instance.home_page.HomePage');
    
}
