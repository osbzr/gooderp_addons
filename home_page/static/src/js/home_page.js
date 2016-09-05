openerp.home_page = function(instance, local) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    local.HomePage = instance.Widget.extend({
        start: function() {
            var num=this.get('value');
            var self=this
            self.$el.append("<div id='main' class='main'>\
                             </div>\
                    </div>")
            var top_top_fist_1 ="<div class='class='section m-t-lg m-b-lg top_div'>\
                                    <div class='container'>\
                                            <div class='row'>\
                                                <div class='col-sm-6 col-sm-offset-3 feature-bg text-center'>\
                                                <p class='bg-primary'>\
                                                    <h1 class='feature-title' style='color:rgb(109,188,245)'>数据统计</h1> </p>\
                                                </div>\
                                            </div>\
                                            <div class='row text-center top_div'>\
                                            </div>\
                                    </div>\
                               </div>"
             var top_top_second_1 ="<div class='main_div'><div class='row'>\
                                <div class='col-sm-6 col-sm-offset-3 feature-bg text-center'>\
                                    <h1 class='feature-title' style='color:rgb(109,188,245)'>业务总览</h1> \
                                 </div>\
                             </div></div>"
            var top_top_last_1 ="<div class='container' style='margin-bottom: 20px;'>\
                                 <div class='row'>\
                                     <div class='col-sm-6 col-sm-offset-3 feature-bg text-center '>\
                                        <h1 class='feature-title' style='color:rgb(109,188,245)'>实时报表</h1> \
                                    </div>\
                                     <div class='col-xs-12 col-sm-12 news right_div'>\
                                     </div>\
                                  </div>"
            new instance.web.Model("home.page").call("get_action_url").then(function(result){
                var index=0;
                self.result_top=result['top']
                if(self.result_top){
                     self.$el.find('.main').append(top_top_fist_1);
                }
                self.result_main=result['main']
                if(self.result_main) {
                    self.$el.find('.main').append(top_top_second_1);
                    var center_main_table = "<div class='section section-feature'><div class='container'><div class='row feature-list'></div></div></div>"
                    self.$el.find('.main_div').append(center_main_table);
                    self.result_main = result['main']
                }
                for(var j=0;j<self.result_main.length;j++){
                    var result_one=self.result_main[index]
                    var center_html_str="<div class='col-sm-3 col-xs-6'><div class='feature-item text-center'>\
                        <p  class='btn btn-primary btn-lg oe_main_link_"+index+"' id='"+index+"'>"+result_one[0]+"</p>\
                        </div><div>"

                    self.$el.find('.feature-list').append(center_html_str);
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

                self.result_top.length/4 > 1?row_num=3 :row_num=parseInt(12/self.result_top.length);
                for(var i=0;i< self.result_top.length;i++){
                    var top_date = self.result_top[i][0].split('  ');
                    if ((i+1)/4>parseInt(self.result_top.length/4)) {
                        row_num = parseInt(12 / (self.result_top.length % 4)) == 0 ? 4 : parseInt(12 / (self.result_top.length % 4))
                    }
                    if (top_date.length==2){
                        var left_html_str = $("<div class='col-xs-12 col-md-"+row_num+"'>\
                              <button class='btn btn-primary-outline btn-pill oe_top_link_"+i+"' id='"+i+"' style='width: 160px;height: 160px;'>\
                              <h4>"+top_date[0]+"</h4>\
                              <h3   >"+top_date[1]+"</h3>\
                              </button><p class='m-t-sm'></p></div>");
                        self.$el.find('.top_div').append(left_html_str);
                        self.$(".oe_top_link_"+i+"").click(function() {
                             self.do_action({
                                type: 'ir.actions.act_window',
                                res_model: (self.result_top[this.id])[2],
                                view_mode: 'list',
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
                var index_last=0;
                if(self.result_quick){
                     self.$el.find('.main').append(top_top_last_1);
                }
                for(var i=0;i< self.result_quick.length;i++){
                    var left_big_html_str = "<div class='col-xs-12 col-md-3 right_small_div_"+i+"'><a>\
                                <h3>" + (self.result_quick[i][0].split(';'))[1] + "</h3></a></div>"
                    self.$el.find('.right_div').append(left_big_html_str);
                    for(var j=0;j<self.result_quick[i][1].length;j++) {
                        var left_html_str = $(" <a><li  class='text-muted oe_p oe_quick_link_" + index_last+ "' data-id='"+i+"_"+j+"_" + index_last + "' id='"+index_last+"' >"+
                            "<p>" + self.result_quick[i][1][j][6] + "</p></li></a>");
                        self.$el.find('.right_small_div_'+i).append(left_html_str);
                        self.$('.oe_quick_link_' +index_last + "").click(function () {
                            index_list = ($(this).attr("data-id")).split('_')
                            index_vals = self.result_quick[parseInt(index_list[0])][1]
                            self.do_action({
                                type: 'ir.actions.act_window',
                                res_model: index_vals[parseInt(index_list[1])][2],
                                view_mode: 'list',
                                name: index_vals[parseInt(index_list[1])][6],
                                views: [[index_vals[parseInt(index_list[1])][5], 'list'], [false, 'form']],
                                domain: index_vals[parseInt(index_list[1])][3],
                                context: index_vals[parseInt(index_list[1])][4],
                                target: 'current',
                            });
                        });
                        index_last ++;
                    }
                }
             });
        },
    });
    instance.web.client_actions.add('home_page.homepage', 'instance.home_page.HomePage');
    
}
