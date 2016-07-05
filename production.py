#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Template', 'Production']
__metaclass__ = PoolMeta


class Template:
    __name__ = 'product.template'
    quality_template = fields.Many2One('quality.template', 'Quality Template')


class Production:
    __name__ = 'production'

    quality_template = fields.Many2One('quality.template', 'Quality Template')
    quality_tests = fields.One2Many('quality.test', 'document', 'Quality Tests',
        context={
            'default_quality_template': Eval('quality_template'),
            },
        depends=['quality_template'])

    @fields.depends('product')
    def on_change_product(self):
        super(Production, self).on_change_product()
        if self.product and self.product.template.quality_template:
            self.quality_template = self.product.template.quality_template

    @classmethod
    def compute_request(cls, product, warehouse, quantity, date, company):
        "Inherited from stock_supply_production"
        production = super(Production, cls).compute_request(product,
            warehouse, quantity, date, company)
        if product.template.quality_template:
            production.quality_template = product.template.quality_template
        return production
