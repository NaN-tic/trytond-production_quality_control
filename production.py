#The COPYRIGHT file at the top level of this repository contains the full
#copyright notices and license terms.
from datetime import datetime

from trytond.model import fields, ModelSQL, ModelView
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction


class Template(metaclass=PoolMeta):
    __name__ = 'product.template'
    quality_templates = fields.One2Many('product.template-quality.template',
        'template', "Quality Templates")


# product.product setup must be executed so template's quality_templates field
# is created to product.product too
class Product(metaclass=PoolMeta):
    __name__ = 'product.product'


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
    time_since_quality_control = fields.DateTime('Time since quality control',
        readonly=True)

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
        to_save = []
        for production in productions:
            production.time_since_quality_control = datetime.now()
            to_save.append(production)
        cls.save(to_save)
        super(Production, cls).run(productions)

    @classmethod
    def create_quality_tests(cls, productions):
        pool = Pool()
        QualityTest = pool.get('quality.test')

        to_save = []
        for production in productions:
            for quality_template in production.quality_templates:
                total_time_since_quality_control = (datetime.now() -
                    production.time_since_quality_control).seconds/60
                if (total_time_since_quality_control >=
                        quality_template.interval):
                    for quality_contol in range(int(
                            total_time_since_quality_control/
                            quality_template.interval)):
                        test = QualityTest()
                        test.document = production
                        test.templates = [quality_template.quality_template]
                        test.company = quality_template.company
                        to_save.append(test)

                    production.time_since_quality_control = datetime.now()

        cls.save(productions)
        if to_save:
            QualityTest.save(to_save)
            QualityTest.apply_templates(to_save)

    @classmethod
    def create_quality_tests_worker(cls):
        productions = cls.search([
            ('state','=','running')
        ])

        for production in productions:
            with Transaction().set_context(queue_name='production'):
                cls.__queue__.create_quality_tests([production])


class ProductionTemplate(ModelSQL, ModelView):
    "Production Template"
    __name__ = 'product.template-quality.template'

    template = fields.Many2One('product.template', "Template",required=True,
        ondelete="CASCADE",
        context={
            'company': Eval('company'),
            },
        depends=['company'])
    company = fields.Many2One('company.company', "Company", required=True)
    interval = fields.Integer("Interval", required=True,
        help="Interval in minutes")
    quality_template = fields.Many2One('quality.template', "Quality Template",
        required=True)

    @classmethod
    def default_company(cls):
        return Transaction().context.get('company')
