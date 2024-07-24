odoo.define('sales_mini_dashboard.sale_dashboard', function (require) {
"use strict";

var core = require('web.core');
var ListController = require('web.ListController');
var ListModel = require('web.ListModel');
var ListRenderer = require('web.ListRenderer');
var ListView = require('web.ListView');
var SampleServer = require('web.SampleServer');
var view_registry = require('web.view_registry');
const session = require('web.session');
var QWeb = core.qweb;

let dashboardValues;
SampleServer.mockRegistry.add('sale.order/retrieve_dashboard', () => {
    return Object.assign({}, dashboardValues);
});

var SaleListDashboardModel = ListModel.extend({

    init: function () {
        this.dashboardValues = {};
        this._super.apply(this, arguments);
    },

    __get: function (localID) {
        var result = this._super.apply(this, arguments);
        if (_.isObject(result)) {
            result.dashboardValues = this.dashboardValues[localID];
        }
        return result;
    },

    __load: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },

    __reload: function () {
        return this._loadDashboard(this._super.apply(this, arguments));
    },

    _loadDashboard: function (super_def) {
        var self = this;
        var dashboard_def = this._rpc({
            model: 'sale.order',
            method: 'retrieve_dashboard',
            context: session.user_context,
        });
        return Promise.all([super_def, dashboard_def]).then(function(results) {
            var id = results[0];
            dashboardValues = results[1];
            self.dashboardValues[id] = dashboardValues;
            console.log("dashboardValues", dashboardValues);
            return id;
        });
    },
});

var SaleListDashboardRenderer = ListRenderer.extend({
    events:_.extend({}, ListRenderer.prototype.events, {
        'click .o_dashboard_action': '_onDashboardActionClicked',
        'click #view_product': '_OpenFormViewProduct',
        'click #view_customer': '_OpenFormViewCustomer',
    }),

     _OpenFormViewProduct: function(ev) {
            var product_id = $(ev.currentTarget).data('id');
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'product.product',
                res_id: product_id,
                views: [[false, 'form']],
                target: 'current',
            });
        },

     _OpenFormViewCustomer: function(ev) {
            var customer_id = $(ev.currentTarget).data('id');
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'res.partner',
                res_id: customer_id,
                views: [[false, 'form']],
                target: 'current',
            });
        },

    _renderView: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var values = self.state.dashboardValues;
            var sale_dashboard = QWeb.render('sales_mini_dashboard.SaleDashboard', {
                values: values,
            });
            self.$el.prepend(sale_dashboard);
        });
    },

    _onDashboardActionClicked: function (e) {
        e.preventDefault();
        var $action = $(e.currentTarget);
        this.trigger_up('dashboard_open_action', {
            action_name: "sale.action_orders",
            action_context: $action.attr('context'),
        });
    },
});

var SaleListDashboardController = ListController.extend({
    custom_events: _.extend({}, ListController.prototype.custom_events, {
        dashboard_open_action: '_onDashboardOpenAction',
    }),

    _onDashboardOpenAction: function (e) {
        return this.do_action(e.data.action_name,
            {additional_context: JSON.parse(e.data.action_context)});
    },
});



var SaleListDashboardView = ListView.extend({
    config: _.extend({}, ListView.prototype.config, {
        Model: SaleListDashboardModel,
        Renderer: SaleListDashboardRenderer,
        Controller: SaleListDashboardController,
    }),
});


view_registry.add('sale_list_dashboard', SaleListDashboardView);

return {
    SaleListDashboardView: SaleListDashboardView,
    SaleListDashboardRenderer: SaleListDashboardRenderer,
    SaleListDashboardController: SaleListDashboardController
};

});
