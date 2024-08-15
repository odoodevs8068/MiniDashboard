from odoo import api, models, fields, _
from odoo.tools import format_amount


class SaleOrderInherit(models.Model):
    _inherit = 'sale.order'

    @api.model
    def retrieve_dashboard(self):
        """ This function returns the values to populate the custom dashboard in
            the Sales order views.
        """
        top_products_by_value = self.get_top_products_by_value_dt()
        top_customers_by_value, top_countries_by_value, top_regions_by_value = self.get_top_customers_by_value_dt()
        result = {
            'top_products_by_value': top_products_by_value,
            'top_customers_by_value': top_customers_by_value,
            'top_countries_by_value': top_countries_by_value,
            'top_regions_by_value': top_regions_by_value,
        }
        self.get_sales_count(result)
        return result

    @api.model
    def get_top_customers_by_value_dt(self):
        def get_sale_orders():
            domain = [('state', 'in', ['sale', 'done'])]
            return self.env['sale.order'].search(domain, order='amount_total desc')

        def aggregate_sales_by_customer(sale_orders):
            customer_sales = {}
            for order in sale_orders:
                customer = order.partner_id
                customer_sales[customer] = customer_sales.get(customer, 0) + order.amount_total
            return sorted(customer_sales.items(), key=lambda x: x[1], reverse=True)[:5]

        def get_top_customers(sorted_customers):
            return [
                {
                    'customer_name': cust.name,
                    'total_value': value,
                    'customer_id': cust.id,
                    'country_id': cust.country_id.id,
                    'country_name': cust.country_id.name,
                } for cust, value in sorted_customers
            ]

        def aggregate_sales_by_country(customers):
            country_sales = {}
            for customer in customers:
                country_name = customer['country_name']
                region_group = self.env['res.country.group'].search([('country_ids.name', '=', country_name)], limit=1)
                region_name = region_group.name if region_group else "Unknown"
                if country_name in country_sales:
                    country_sales[country_name]['total_value'] += customer['total_value']
                else:
                    country_sales[country_name] = {'total_value': customer['total_value'], 'region': region_name}
            return [
                {'country': country, 'total_value': value['total_value'], 'region': value['region']}
                for country, value in country_sales.items()
            ]

        def aggregate_sales_by_region(countries):
            region_sales = {}
            for country in countries:
                region_name = country['region']
                region_sales[region_name] = region_sales.get(region_name, 0) + country['total_value']
            return [{'region_name': region, 'total_value': value} for region, value in region_sales.items()]

        sale_orders = get_sale_orders()
        sorted_customers = aggregate_sales_by_customer(sale_orders)
        top_customers_by_value = get_top_customers(sorted_customers)
        top_countries_by_value = aggregate_sales_by_country(top_customers_by_value)
        top_regions_by_value = aggregate_sales_by_region(top_countries_by_value)

        return top_customers_by_value, top_countries_by_value, top_regions_by_value

    @api.model
    def get_top_products_by_value_dt(self):
        domain = [('state', 'in', ['sale', 'done'])]
        sale_orders = self.env['sale.order'].search(domain, order='amount_total desc')
        sale_order_ids = sale_orders.ids

        if sale_order_ids:
            query = """
                        SELECT 
                            sol.product_id,
                            pt.name AS product_name,
                            SUM(sol.product_uom_qty) AS total_quantity,
                            SUM(sol.price_total) AS total_value
                        FROM 
                            sale_order_line AS sol
                        JOIN 
                            product_product AS pp ON sol.product_id = pp.id
                        JOIN 
                            product_template AS pt ON pp.product_tmpl_id = pt.id
                        WHERE 
                            sol.order_id IN %s
                        GROUP BY 
                            sol.product_id, pt.name
                        ORDER BY 
                            total_value DESC
                        LIMIT 5;
                    """
            self.env.cr.execute(query, (tuple(sale_order_ids),))
            result = self.env.cr.fetchall()
            top_products_by_value = [
                {
                    'product_name': record[1],
                    'total_value': record[3],
                    'product_id': record[0]
                }
                for record in result
            ]

            return top_products_by_value

    @api.model
    def get_sales_count(self, result):
        sale_order = self.env['sale.order']
        user = self.env.user
        result['total_orders'] = sale_order.search_count([])
        result['sale_orders'] = sale_order.search_count([('state', 'in', ['sale', 'done'])])
        result['to_invoice'] = sale_order.search_count([('invoice_status', '=', 'to invoice')])
        result['invoiced'] = sale_order.search_count([('invoice_status', '=', 'invoiced')])
        result['my_sale_orders'] = sale_order.search_count(
            [('user_id', '=', user.id), ('state', 'in', ['sale', 'done'])])
        result['my_to_invoice'] = sale_order.search_count(
            [('user_id', '=', user.id), ('invoice_status', '=', 'to invoice')])
        result['my_invoiced'] = sale_order.search_count(
            [('user_id', '=', user.id), ('invoice_status', '=', 'invoiced')])

        order_sum = """select sum(amount_total) from sale_order where state 
               in ('sale', 'done')"""
        self._cr.execute(order_sum)
        sale_amount = self.env.cr.fetchone()
        result['total_sale_amount'] = format_amount(self.env, sale_amount[0] or 0, self.env.company.currency_id)

        invoice_amount_sum = """select sum(amount_total) from sale_order where invoice_status 
                       = 'invoiced'"""
        self._cr.execute(invoice_amount_sum)
        invoice_amount = self.env.cr.fetchone()
        result['total_invoice_amount'] = format_amount(self.env, invoice_amount[0] or 0, self.env.company.currency_id)

        partial_invoice_amount_sum = """
                            SELECT SUM(am.amount_residual)
                            FROM account_move AS am
                            JOIN sale_order AS so ON so.name = am.invoice_origin
                            WHERE am.state = 'posted' AND am.payment_state = 'partial' AND am.move_type = 'out_invoice'
                        """
        self._cr.execute(partial_invoice_amount_sum)
        partial_amount = self.env.cr.fetchone()

        invoice_amount_total = invoice_amount[0] if invoice_amount[0] is not None else 0.0
        partial_amount_total = partial_amount[0] if partial_amount[0] is not None else 0.0
        total_paid_amount = invoice_amount_total - partial_amount_total

        result['total_paid_amount'] = format_amount(self.env, total_paid_amount or 0, self.env.company.currency_id)
        result['bl_amount'] = format_amount(self.env, partial_amount[0] or 0, self.env.company.currency_id)
        return result