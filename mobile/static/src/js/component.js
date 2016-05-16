$(function() {
    var charInput = Vue.extend({
        props: ['model'],
        template: '<input class="weui_input" v-model="model.value" type="text" :placeholder="model.placeholder" />',
    });

    var dateInput = Vue.extend({
        props: ['model'],
        template: '<input class="weui_input" style="width: 80%" v-model="model.value" type="date" />',
    });

    var datetimeInput = Vue.extend({
        props: ['model'],
        template: '<input class="weui_input" style="width: 80%" v-model="model.value" type="datetime-local" />',
    });

    var textInput = Vue.extend({
        props: ['model'],
        template: '<textarea class="weui_textarea" v-model="model.value" :placeholder="model.placeholder" rows="3"></textarea>' +
                  '<div class="weui_textarea_counter"><span>0</span>/200</div>',
    });

    var numberInput = Vue.extend({
        props: ['model'],
        template: '<input class="weui_input" v-model="model.value" type="number" :placeholder="model.placeholder" />',
    });

    var selectionInput = Vue.extend({
        props: ['model'],
        computed: {
            selection: function() {
                if (this.model.selection) {
                    try {
                        var selection = this.model.selection.replace(new RegExp('\\(', 'g'), '[').replace(new RegExp('\\)', 'g'), ']');
                        return eval(selection);
                    } catch(exception) {
                        alert('selection值解析错误，请联系管理员');
                    }
                }

                return [];
            },
        },
        template: '#selectionInput'
    });


    var many2oneInput = Vue.extend({
        props: ['model'],
        template: '#many2oneInput',
        data: function() {
            return {
                word: '',
                search_word: '',
                search_cache: false,
                records: [],
            };
        },
        methods: {
            input_change: function() {
                var self = this;

                self.search_word = self.word;
                if (self.search_word) {
                    $.when($.get('/mobile/many2one/search', {
                        word: self.search_word,
                        model: self.model.model,
                        domain: self.model.domain,
                    })).then(function(results) {
                        self.records = JSON.parse(results);
                    });
                }
            },

            blur_input: function() {
                if (!this.model.value) {
                    this.word = '';
                    this.search_word = '';
                }
            },

            delete_input: function() {
                this.model.value = false;
            },

            enter_input: function() {
                if (this.records) {
                    this.model.value = this.records[0].id;
                    this.word = this.records[0].value;
                    this.search_word = '';
                }
            },
            choose_record: function(record) {
                this.model.value = record.id;
                this.word = record.value;
                this.search_word = '';
            },
        },
    });

    Vue.component('char-input', charInput);
    Vue.component('date-input', dateInput);
    Vue.component('datetime-input', datetimeInput);
    Vue.component('number-input', numberInput);
    Vue.component('text-input', textInput);
    Vue.component('selection-input', selectionInput);
    Vue.component('many2one-input', many2oneInput);
});
