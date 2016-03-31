"use strict";
(function(){
    var instance = openerp;
    var QWeb = instance.web.qweb, _t = instance.web._t;

    instance.web_readonly_bypass = {
        /**
         * ignore readonly: place options['readonly_fields'] into the data
         * if nothing is specified into the context
         *
         * create mode: remove read-only keys having a 'false' value
         *
         * @param {Object} data field values to possibly be updated
         * @param {Object} options Dictionary that can contain the following keys:
         *   - readonly_fields: Values from readonly fields to merge into the data object
         * @param boolean mode: True case of create, false case of write
         * @param {Object} context->readonly_by_pass
         */
        ignore_readonly: function(data, options, mode, context){
            var readonly_by_pass_fields = this.retrieve_readonly_by_pass_fields(
                options, context);
            if(mode){
                $.each( readonly_by_pass_fields, function( key, value ) {
                    if(value==false){
                        delete(readonly_by_pass_fields[key]);
                    }
                });
            }
            data = $.extend(data,readonly_by_pass_fields);
        },

        /**
         * retrieve_readonly_by_pass_fields: retrieve readonly fields to save
         * according context.
         *
         * @param {Object} options Dictionary that can contain the following keys:
         *   - readonly_fields: all values from readonly fields
         * @param {Object} context->readonly_by_pass: Can be true if all
         *   all readonly fields should be saved or an array of field name to
         *   save ie: ['readonly_field_1', 'readonly_field_2']
         * @returns {Object}: readonly key/value fields to save according context
         */
        retrieve_readonly_by_pass_fields: function(options, context){
            var readonly_by_pass_fields = {};
            if (options && 'readonly_fields' in options &&
               options['readonly_fields'] && context &&
               'readonly_by_pass' in context && context['readonly_by_pass']){
                if (_.isArray(context['readonly_by_pass'])){
                    $.each( options.readonly_fields, function( key, value ) {
                        if(_.contains(context['readonly_by_pass'], key)){
                            readonly_by_pass_fields[key] = value;
                        }
                    });
                }else{
                    readonly_by_pass_fields = options.readonly_fields;
                }
            }
            return readonly_by_pass_fields;
        },
    };

    var readonly_bypass = instance.web_readonly_bypass;

    instance.web.BufferedDataSet.include({

        init : function() {
            this._super.apply(this, arguments);
        },
        /**
         * Creates Overriding
         *
         * @param {Object} data field values to set on the new record
         * @param {Object} options Dictionary that can contain the following keys:
         *   - readonly_fields: Values from readonly fields that were updated by
         *     on_changes. Only used by the BufferedDataSet to make the o2m work correctly.
         * @returns super {$.Deferred}
         */
        create : function(data, options) {
            var self = this;
            var context = instance.web.pyeval.eval('contexts',
                                                   self.context.__eval_context);
            readonly_bypass.ignore_readonly(data, options, true, context);
            return self._super(data,options);
        },
        /**
         * Creates Overriding
         *
         * @param {Object} data field values to set on the new record
         * @param {Object} options Dictionary that can contain the following keys:
         *   - readonly_fields: Values from readonly fields that were updated by
         *     on_changes. Only used by the BufferedDataSet to make the o2m work correctly.
         * @returns super {$.Deferred}
         */
        write : function(id, data, options) {
            var self = this;
            var context = instance.web.pyeval.eval('contexts',
                                                   self.context.__eval_context);
            readonly_bypass.ignore_readonly(data, options, false, context);
            return self._super(id,data,options);
        },

    });

    instance.web.DataSet.include({
        /*
        BufferedDataSet: case of 'add an item' into a form view
        */
        init : function() {
            this._super.apply(this, arguments);
        },
        /**
         * Creates Overriding
         *
         * @param {Object} data field values to set on the new record
         * @param {Object} options Dictionary that can contain the following keys:
         *   - readonly_fields: Values from readonly fields that were updated by
         *     on_changes. Only used by the BufferedDataSet to make the o2m work correctly.
         * @returns super {$.Deferred}
         */
        create : function(data, options) {
            var self = this;
            readonly_bypass.ignore_readonly(data, options, true, self.context);
            return self._super(data,options);
        },
        /**
         * Creates Overriding
         *
         * @param {Object} data field values to set on the new record
         * @param {Object} options Dictionary that can contain the following keys:
         *   - readonly_fields: Values from readonly fields that were updated by
         *     on_changes. Only used by the BufferedDataSet to make the o2m work correctly.
         * @returns super {$.Deferred}
         */
        write : function(id, data, options) {
            var self = this;
            readonly_bypass.ignore_readonly(data, options, false, self.context);
            return self._super(id,data,options);
        },

    });

    instance.web.ProxyDataSet.include({
        /*
        ProxyDataSet: case of 'pop-up'
        */
        init : function() {
            this._super.apply(this, arguments);
        },
        /**
         * Creates Overriding
         *
         * @param {Object} data field values to set on the new record
         * @param {Object} options Dictionary that can contain the following keys:
         *   - readonly_fields: Values from readonly fields that were updated by
         *     on_changes. Only used by the BufferedDataSet to make the o2m work correctly.
         * @returns super {$.Deferred}
         */
        create : function(data, options) {
            var self = this;
            var context = instance.web.pyeval.eval('contexts',
                    self.context.__eval_context);
            readonly_bypass.ignore_readonly(data, options, true, context);
            return self._super(data,options);
        },
        /**
         * Creates Overriding
         *
         * @param {Object} data field values to set on the new record
         * @param {Object} options Dictionary that can contain the following keys:
         *   - readonly_fields: Values from readonly fields that were updated by
         *     on_changes. Only used by the BufferedDataSet to make the o2m work correctly.
         * @returns super {$.Deferred}
         */
        write : function(id, data, options) {
            var self = this;
            var context = instance.web.pyeval.eval('contexts',
                    self.context.__eval_context);
            readonly_bypass.ignore_readonly(data, options, false, context);
            return self._super(id,data,options);
        },

    });

})();
