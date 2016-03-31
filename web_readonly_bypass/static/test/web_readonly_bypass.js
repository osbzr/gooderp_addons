openerp.testing.section( 'web_readonly_bypass', {},
function(test){
        test('ignore_readonly', function(instance){
            var data = {};
            var mode_create = true;
            var options = {};
            var context = {};
            instance.web_readonly_bypass.ignore_readonly(data, options,
                mode_create, context);
            deepEqual(data,
                {},
                "Empty context and options mode create"
            );

            mode_create = false;
            data = {};
            instance.web_readonly_bypass.ignore_readonly(data, options,
                mode_create, context);
            deepEqual(data,
                {},
                "Empty context and options mode write"
            );

            mode_create = false;
            data = {};
            context = {'readonly_by_pass': true};
            options = {'readonly_fields': {'field_1': 'va1-1',
                                           'field_2': false,
                                           'field_3': 'val-3'}};
            instance.web_readonly_bypass.ignore_readonly(data, options,
                mode_create, context);
            deepEqual(data,
                {'field_1': 'va1-1', 'field_2': false, 'field_3': 'val-3'},
                "all fields mode write"
            );

            mode_create = true;
            data = {};
            context = {'readonly_by_pass': true};
            options = {'readonly_fields': {'field_1': 'va1-1',
                                           'field_2': false,
                                           'field_3': 'val-3'}};
            instance.web_readonly_bypass.ignore_readonly(data, options,
                mode_create, context);
            deepEqual(data,
                {'field_1': 'va1-1', 'field_3': 'val-3'},
                "all fields mode create (false value are escaped)"
            );

            mode_create = true;
            data = {};
            context = {};
            options = {'readonly_fields': {'field_1': 'va1-1',
                                           'field_2': false,
                                           'field_3': 'val-3'}};
            instance.web_readonly_bypass.ignore_readonly(data, options,
                mode_create, context);
            deepEqual(data,
                {},
                "without context, default, we won't save readonly fields"
            );
        });

        test('retrieve_readonly_by_pass_fields', function(instance){
            var context = {'readonly_by_pass': true}
            var options = {'readonly_fields': {'field_1': 'va1-1',
                                               'field_2': 'val-2',
                                               'field_3': 'val-3'}};
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {'field_1': 'va1-1', 'field_2': 'val-2', 'field_3': 'val-3'},
                "All fields should be accepted!"
            );

            context = {'readonly_by_pass': ['field_1', 'field_3']};
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {'field_1': 'va1-1','field_3': 'val-3'},
                "two field s1"
            );

            context = {'readonly_by_pass': ['field_1',]};
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {'field_1': 'va1-1'},
                "Only field 1"
            );

            context = {'readonly_by_pass': []};
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {},
                "Empty context field"
            );

            context = null;
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {},
                "Null context"
            );

            context = false;
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {},
                "false context"
            );

            context = {'readonly_by_pass': true}
            options = {'readonly_fields': {'field_1': 'va1-1'}};
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {'field_1': 'va1-1'},
                "Only one option"
            );


            options = {'readonly_fields': {}};
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {},
                "Empty readonly_fields option"
            );

            options = {};
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {},
                "Empty option"
            );

            options = null;
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {},
                "null option"
            );

            options = false;
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {},
                "false option"
            );

            context = false;
            deepEqual(
                instance.web_readonly_bypass.retrieve_readonly_by_pass_fields(
                    options, context),
                {},
                "false option and false context"
            );
        });
});
