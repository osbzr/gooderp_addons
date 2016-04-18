openerp.num_to_china = function() {
    var instance = openerp;
    var QWeb = instance.web.qweb;
    var _t = instance.web._t;

    instance.web.form.num_to_china=instance.web.form.FieldFloat.extend({
          render_value: function() {
              var self=this
              if (!this.get("effective_readonly")) {
                  this.$el.find('input').val(this.get('value'));
              } else {
                  var num=this.get('value');
                  new instance.web.Model("res.currency").call("rmb_upper",[parseFloat(num)]).then(function(result){
                    self.$el.text(result);
                  });
              }
          },
      });
    instance.web.form.widgets.add('num_to_china', 'instance.web.form.num_to_china');
}
