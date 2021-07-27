# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import production
from . import ir

def register():
    Pool.register(
        ir.Cron,
        production.Template,
        production.Production,
        production.ProductionTemplate,
        module='production_quality_control', type_='model')
