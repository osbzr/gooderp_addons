$(function() {
    var charInput = Vue.extend({
        props: ['model', 'placeholder'],
        template: '<input class="weui_input" v-model="model" type="text" :placeholder="placeholder" />',
    });

    var dateInput = Vue.extend({
        props: ['model'],
        template: '<input class="weui_input" v-model="model" type="date" />',
    });

    var datetimeInput = Vue.extend({
        props: ['model'],
        template: '<input class="weui_input" v-model="model" type="datetime-local" />',
    });

    var textInput = Vue.extend({
        props: ['model', 'placeholder'],
        template: '<textarea class="weui_textarea" v-model="model" :placeholder="placeholder" rows="3"></textarea>' +
                  '<div class="weui_textarea_counter"><span>0</span>/200</div>',
    });

    var numberInput = Vue.extend({
        props: ['model', 'placeholder'],
        template: '<input class="weui_input" v-model="model" type="number" :placeholder="placeholder" />',
    });

    var many2oneInput = Vue.extend({
        props: ['model', 'placeholder'],
        template: '<input class="weui_input" type="number" :placeholder="placeholder" @input="input_change" />',
        methods: {
            input_change: function() {
                console.log(this);
                this.model = '123';
            }
        },
    });

    Vue.component('char-input', numberInput);
    Vue.component('date-input', dateInput);
    Vue.component('datetime-input', datetimeInput);
    Vue.component('number-input', numberInput);
    Vue.component('text-input', textInput);
    Vue.component('many2one-input', many2oneInput);
});
