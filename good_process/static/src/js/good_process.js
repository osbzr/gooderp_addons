odoo.define('good.process', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var form_relational = require('web.form_relational');
var Model = require('web.Model');
var QWeb = core.qweb;
var _t = core._t;

var FieldGoodProcess = form_relational.FieldMany2ManyTags.extend({
    tag_template: "FieldGoodProcess",
    events: {
            'click .good_approve': 'good_approve',
            'click .good_refused': 'good_refused',
        },

    start: function() {
        this._super.apply(this, arguments);
    },

    render_tag: function(data) {
        console.log(data, this);
        var self = this;
        var user_ids =  _.filter(data,function (value)
                            { if(value.display_name==self.session.name){
                                return value.id}})
        if(self.view.datarecord.id!=undefined){
            this.$('.process').remove();
            this.$('.o_form_input_dropdown').remove();
            this.$el.prepend(QWeb.render(this.tag_template, {elements: data,
                button_invisible: user_ids.length,
                filed_display_name: self.string,
                readonly: this.get('effective_readonly')}));}
    },

    good_refused:function () {
        var self = this;
        new Model('mail.thread').call('good_process_refused',[self.view.datarecord.id, self.view.model]).then(function (result) {
           if(result && typeof(result)== 'object'){
               self.render_tag(result);
           }else{
               self.do_notify(_t("拒绝失败"), _t(result));
           }
        })
    },

    good_approve:function () {
       var self = this;
       new Model('mail.thread').call('good_process_approve',[self.view.datarecord.id, self.view.model]).then(function (result) {

           if(result && typeof(result)== 'object'){
               _.each(result,function (id) {
                   var remove_tags = self.$el.find('span[data-id="' + id + '"]');
                   var remove_button = self.$el.find('.good_approve_div');
                   $(remove_tags).addClass('o_hidden');
                   $(remove_button).addClass('o_hidden');
               });
           }else{
               self.do_notify(_t("审批失败"), _t(result));
           }
       })
    },
});
/**
 * Registry of form fields
 */
core.form_widget_registry.add('goodprocess', FieldGoodProcess);

});
