from odoo import models, fields, api


class LaptopAllocation(models.Model):
    _name = 'laptop.allocation'
    _description = 'Laptop Allocation'

    employee_id = fields.Many2one('hr.employee', string="Employee", required=True)
    product_id = fields.Many2one('product.product', string="Laptop", required=True)
    date_allocated = fields.Datetime(string="Date Allocated", default=fields.Datetime.now)
    date_returned = fields.Datetime(string="Date Returned")
    state = fields.Selection([
        ('allocated', 'Allocated'),
        ('returned', 'Returned'),
    ], default='allocated')
    source_location_id = fields.Many2one('stock.location', string="Source Location", required=True,
                                         domain=[('usage', '=', 'internal')])
    destination_location_id = fields.Many2one('stock.location', string="Destination Location", required=True,
                                              domain=[('usage', '=', 'internal')])
    stock_move_id = fields.Many2one('stock.move', string="Stock Move", readonly=True)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if res.product_id and res.source_location_id and res.destination_location_id:
            move = res.env['stock.move'].create({
                'name': f"Laptop Move - {res.product_id.name}",
                'product_id': res.product_id.id,
                'product_uom': res.product_id.uom_id.id,
                'product_uom_qty': 1.0,
                'location_id': res.source_location_id.id,
                'location_dest_id': res.destination_location_id.id,
            })
            move._action_confirm()
            move._action_assign()
            move.quantity_done = 1.0
            move._action_done()

            res.stock_move_id = move.id
        return res

    def action_return_laptop(self):
        for record in self:
            if record.state != 'returned':
                record.write({
                    'state': 'returned',
                    'date_returned': fields.Datetime.now()
                })

                return_move = self.env['stock.move'].create({
                    'name': f"Laptop Return - {record.product_id.name}",
                    'product_id': record.product_id.id,
                    'product_uom': record.product_id.uom_id.id,
                    'product_uom_qty': 1.0,
                    'location_id': record.destination_location_id.id,
                    'location_dest_id': record.source_location_id.id,
                })
                return_move._action_confirm()
                return_move._action_assign()
                return_move.quantity_done = 1.0
                return_move._action_done()

    def open_stock_move(self):
        self.ensure_one()
        return {
            'name': 'Stock Move',
            'view_mode': 'form',
            'res_model': 'stock.move',
            'type': 'ir.actions.act_window',
            'res_id': self.stock_move_id.id,
        }

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    laptop_allocation_ids = fields.One2many('laptop.allocation', 'employee_id', string='Laptop Allocations')


