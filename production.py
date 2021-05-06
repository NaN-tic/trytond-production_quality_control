#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from datetime import datetime, timedelta

from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'
    quality_templates = fields.One2Many('product.template-quality.template', 'template', "Quality Templates")


class Production(metaclass=PoolMeta):
    __name__ = 'production'

    quality_templates = fields.Function(fields.One2Many(
            'product.template-quality.template', None, "Quality Templates"), 
        'get_quality_templates')

    quality_tests = fields.One2Many('quality.test', 'document', 'Quality Tests',
        context={
            'default_quality_templates': Eval('quality_templates'),
            },
        depends=['quality_templates'])
    time_since_quality_control = fields.DateTime('Time since quality control')

    def get_quality_templates(self, name):
        context = Transaction().context

        quality_templates = []
        if self.product:
            for quality_template in self.product.template.quality_templates:
                if quality_template.company.id == context.get('company'):
                    quality_templates.append(quality_template.id)
        return quality_templates

    @classmethod
    def compute_request(cls, product, warehouse, quantity, date, company):
        "Inherited from stock_supply_production"
        production = super(Production, cls).compute_request(product,
            warehouse, quantity, date, company)
        if product.template.quality_templates:
            production.quality_templates = product.template.quality_templates
        return production

    @classmethod
    def run(cls, productions):
        for production in productions:
            production.time_since_quality_control = datetime.now()
            production.save()
        super(Production, cls).run(productions)

    @classmethod
    def done(cls, productions):
        pool = Pool()
        QualityTest = pool.get('quality.test')

        for production in productions:
            document = 'production,%s' % str(production.id)
            tests_not_successful = QualityTest.search([
                ('state', 'not like', 'successful'),
                ('document', '=', 'production,%s' % str(production.id)),
            ])
            if len(tests_not_successful) != 0:
                raise UserError(gettext('production_quality_control.'
                        'msg_test_not_successful',
                        production=production.number))

    @classmethod
    def create_quality_tests(cls):
        pool = Pool()
        QualityTest = pool.get('quality.test')

        productions = cls.search([
            ('state','=','running')
        ])

        to_save = []
        for production in productions:
            for quality_template in production.quality_templates:
                if ((datetime.now() - production.time_since_quality_control
                        ).seconds/60 >= quality_template.interval):
                    #create quality_test
                    test = QualityTest()
                    test.document = production
                    test.templates = [quality_template.quality_template]
                    test.company = quality_template.company
                    to_save.append(test)

                    production.time_since_quality_control = datetime.now()
                    production.save()
        if to_save:
            QualityTest.save(to_save)
            QualityTest.apply_templates(to_save)


class ProductionTemplate(ModelSQL, ModelView):
    "Production Template"
    __name__ = 'product.template-quality.template'

    template = fields.Many2One('product.template', "Template")
    company = fields.Many2One('company.company', "Company", required=True)
    interval = fields.Integer("Interval", required=True,
        help="Interval in minutes")
    quality_template = fields.Many2One('quality.template', "Quality Template")

    @classmethod
    def default_company(cls):
        return Transaction().context.get('company')