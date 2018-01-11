odoo.define('web.stock_query', function(require) {
    var Client = require('web.WebClient');
    var Model = require('web.DataModel');
    var Core = require('web.core');
    
    Client.include({
        show_application: function() {
            this._super.apply(this, arguments);
            this.show_stock_query();
            this.$board = false;
        },

        show_stock_query: function() {
            var self = this,
                $query = $('<ul class="nav navbar-nav navbar-right nav-stock-query"><li><input type="text" placeholder="库存查询"/><a class="query"></a><a class="destroy"></a><div class="stock-query-search-list"/></li></ul>'),
                $input = $query.find('input'),
                $destroy = $query.find('.destroy');

            $input.on('focus', function(event) {
                $input.addClass('editable');
                if ($input.val() !== '' && self.$board) self.$board.fadeIn('fast');
            }).on('blur', function(event) {
                if ($input.val() === '') {
                    $input.removeClass('editable');
                }
                self.hide_query_board();
            }).on('input', function(event) {
                if ($input.val() === '') {
                    $destroy.fadeOut('fast');
                    self.hide_query_board();
                } else {
                    $destroy.fadeIn('fast');
                    self.show_query_board($input);
                }
            }).on('keydown', function(event) {
                switch (event.which) {
                    case $.ui.keyCode.ENTER:
                        self.select_query();
                        break;
                    case $.ui.keyCode.DOWN:
                        self.query_board_move('down');
                        event.preventDefault();
                        break;
                    case $.ui.keyCode.UP:
                        self.query_board_move('up');
                        event.preventDefault();
                        break;
                }
            });

            $query.on('mousedown', '.stock-query-search-list li:not(.search-list-more)', function(event) {
                self.select_query($(this));
            }).on('mousedown', '.search-list-more', function(event) {
                self.open_report_stock_balance();
            }).on('hover', '.stock-query-search-list li', function(event) {
                self.query_board_move($(this));
            }).on('click', '.destroy', function(event) {
                $input.val('');
                $input.focus();
                $destroy.fadeOut('fast');
            });

            $('.oe_systray').before($query);
        },

        show_query_board: function($input) {
            var self = this;
            new Model('goods').call('name_search', {name: $input.val()} ).then(function(results) {
                if (results.length <= 0) return self.hide_query_board();

                self.$board = $(Core.qweb.render('web_stock_query.search_list', {'values': _.map(results, function(result) {
                    return {id: result[0], name: result[1]};
                })}));

                self.$board.attr('top', $input.height() + 2 + 'px');
                $input.parent().find('.stock-query-search-list').html(self.$board);
            });
        },

        hide_query_board: function() {
            if (this.$board) this.$board.fadeOut('fast');
        },

        query_board_move: function(direction) {
            if (this.$board) {
                var current_move = this.$board.find('li.select'),
                    next_move = false;

                if (_.contains(['up', 'down'], direction)) {
                    next_move = direction === 'down'? current_move.next(): current_move.prev();
                    if (next_move && next_move.is('li')) {
                        var offset_y = next_move.offset().top - (direction === 'down'? this.$board.height(): 40);
                        this.$board.scrollTop(this.$board.scrollTop() + offset_y);
                    }
                } else if (direction.jquery) {
                    next_move = direction;
                }

                if (next_move && next_move.is('li')) {
                    next_move.addClass('select').siblings('.select').removeClass('select');
                }
            }
        },

        open_report_stock_balance: function() {
            this.action_manager.do_action({
                type: 'ir.actions.act_window',
                res_model: 'report.stock.balance',
                views: [[false, 'pivot'], [false, 'list']],
                limit:80000,
                target: 'current',
                name: '库存余额表',
            });
        },

        select_query: function($target) {
            var self = this;
            if (self.$board) {
                $target = $target || self.$board.find('li.select');
                if ($target.hasClass('search-list-more')) {
                    return self.open_report_stock_balance();
                }

                self.action_manager.do_action({
                    type: 'ir.actions.act_window',
                    res_model: 'report.stock.balance',
                    views: [[false, 'pivot'], [false, 'list']],
                    domain: [['goods_id', '=', $target.data('id')]],
                    target: 'new',
                    name: '搜索：' + $target.text().trim(),
                });
            }
        }
    });
});
