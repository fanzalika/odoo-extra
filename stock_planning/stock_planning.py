# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: partner.py 1007 2005-07-25 13:18:09Z kayhman $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields,osv
import pooler
from tools import config
import time
import netsvc
import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime

class stock_planning_period(osv.osv):
    _name = "stock.planning.period"
    _columns = {
        'name': fields.char('Period Name', size=64),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'period_ids': fields.one2many('stock.period', 'planning_id', 'Periods'),
    }
    
    def create_period_weekly(self,cr, uid, ids, context={}):
        return self.create_period(cr, uid, ids, context, 7)
    
    def create_period_monthly(self,cr, uid, ids, context={}):
        return self.create_period(cr, uid, ids, context, 30)

    def create_period(self,cr, uid, ids, context={}, interval=1):
        for p in self.browse(cr, uid, ids, context):
            dt = p.date_start
            ds = mx.DateTime.strptime(p.date_start, '%Y-%m-%d')
            while ds.strftime('%Y-%m-%d')<p.date_stop:
                de = ds + RelativeDateTime(days=interval)
                self.pool.get('stock.period').create(cr, uid, {
                    'name': ds.strftime('%d/%m'),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'planning_id': p.id,
                })
                ds = ds + RelativeDateTime(days=interval)
        return True
stock_planning_period()


class stock_period(osv.osv):
    _name = "stock.period"

    _columns = {
        'name': fields.char('Period Name', size=64),
        'date_start': fields.date('Start Date', required=True),
        'date_stop': fields.date('End Date', required=True),
        'planning_id': fields.many2one('stock.planning.period', 'Period', required=True, select=True),
    }
    
stock_period()


class stock_planning_sale_prevision(osv.osv):
    _name = "stock.planning.sale.prevision"
    
    _columns = {
        'name' : fields.char('Name', size=64),
        'user_id': fields.many2one('res.users' , 'Salesman'),
        'period_id': fields.many2one('stock.period' , 'Period', required=True),
        'product_id': fields.many2one('product.product' , 'Product', required=True),
        'product_qty' : fields.float('Product Quantity', required=True),
        'product_uom' : fields.many2one('product.uom', 'Product UoM', required=True),
    }
    
    
    def product_id_change(self, cr, uid, ids, product, uom=False):
        if not product:
            return {'value': {'product_qty' : 0.0, 'product_uom': False},'domain': {'product_uom': []}}

        product_obj =  self.pool.get('product.product').browse(cr, uid, product)
        result = {}
        if not uom:
            result['product_uom'] = product_obj.uom_id.id
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],}
        return {'value': result}
    
stock_planning_sale_prevision()

class stock_planning(osv.osv):
    _name = "stock.planning"
    
    def _get_product_qty(self, cr, uid, ids, field_names, arg, context):
        res = {}
        if not context:
            context = {}
        mapping = {
            'incoming': "incoming_qty",
            'outgoing': "outgoing_qty",
        }
        for val in self.browse(cr, uid, ids):
            res[val.id] = {}
            context['from_date'] = val.period_id.date_start
            context['to_date'] = val.period_id.date_stop
            context['warehouse'] = val.warehouse_id.id or False
            product_obj =  self.pool.get('product.product').read(cr, uid,val.product_id.id,[], context)
            product_qty =product_obj[' , '.join(map(lambda x: mapping[x], field_names))]# 0.0
            res[val.id][field_names[0]] = product_qty
        return res
    
    def _get_planned_sale(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            cr.execute('select sum(product_qty) from stock_planning_sale_prevision where product_id = %d and period_id = %d',(val.product_id.id,val.period_id.id))
            product_qty = cr.fetchall()[0][0]
            res[val.id] = product_qty
        return res
    
    def _get_stock_start(self, cr, uid, ids, field_name, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            res[val.id] = 0.0
            context['from_date'] = val.period_id.date_start
            context['to_date'] = val.period_id.date_stop
            context['warehouse'] = val.warehouse_id.id or False
            current_date =  time.strftime('%Y-%m-%d')
            product_obj =  self.pool.get('product.product').browse(cr, uid,val.product_id.id,[], context)
            if current_date > val.period_id.date_stop:
                pass
            elif current_date > val.period_id.date_start and current_date < val.period_id.date_stop:
                res[val.id] = product_obj.qty_available
            else:
                res[val.id] = product_obj.qty_available + (val.to_procure - val.planned_outgoing)
        return res
    
    def _get_value_left(self, cr, uid, ids, field_names, arg, context):
        res = {}
        for val in self.browse(cr, uid, ids):
            res[val.id] = {}
            if field_names[0] == 'stock_incoming_left':
                ret = val.to_procure-val.incoming
            if  field_names[0] == 'outgoing_left':
                ret = val.planned_outgoing-val.outgoing
            res[val.id][field_names[0]] = ret
        return res
    
    _columns = {
        'name' : fields.char('Name', size=64),
        'period_id': fields.many2one('stock.period' , 'Period', required=True),
        'product_id': fields.many2one('product.product' , 'Product', required=True),
        'product_uom' : fields.many2one('product.uom', 'Product UoM', required=True),
        'planned_outgoing' : fields.float('Planned Outgoing', required=True),
        'planned_sale': fields.function(_get_planned_sale, method=True, string='Planned Sales'),
        'stock_start': fields.function(_get_stock_start, method=True, string='Stock Start'),
        'incoming': fields.function(_get_product_qty, method=True, type='float', string='Incomming', multi='incoming'),
        'outgoing': fields.function(_get_product_qty, method=True, type='float', string='Outgoing', multi='outgoing'),
        'stock_incoming_left': fields.function(_get_value_left, method=True, string='To Procure Left', multi="stock_incoming_left"),
        'outgoing_left': fields.function(_get_value_left, method=True, string='Outgoing Left', multi="outgoing_left"),
        'to_procure': fields.float(string='To Procure'),
        'warehouse_id' : fields.many2one('stock.warehouse','Warehouse'),
    }
    
    def procure_incomming_left(self, cr, uid, ids, context, *args):
        result = {}
        for obj in self.browse(cr, uid, ids):       
            if not obj.warehouse_id:
                raise osv.except_osv('Error', "select warehouse")
            location_id = obj.warehouse_id and obj.warehouse_id.lot_stock_id.id or False
            output_id = obj.warehouse_id and obj.warehouse_id.lot_output_id.id or False
            move_id = self.pool.get('stock.move').create(cr, uid, {
                            'name': obj.product_id.name[:64],
                            'product_id': obj.product_id.id,
                            'date_planned': obj.period_id.date_start,
                            'product_qty': obj.stock_incoming_left,
                            'product_uom': obj.product_uom.id,
                            'product_uos_qty': obj.stock_incoming_left,
                            'product_uos': obj.product_uom.id,
                            'location_id': location_id,
                            'location_dest_id': output_id,
                            'state': 'waiting',
                        })
            proc_id = self.pool.get('mrp.procurement').create(cr, uid, {
                            'name': 'Procure left From Planning',
                            'origin': 'Stock Planning',
                            'date_planned': obj.period_id.date_start,
                            'product_id': obj.product_id.id,
                            'product_qty': obj.stock_incoming_left,
                            'product_uom': obj.product_uom.id,
                            'product_uos_qty': obj.stock_incoming_left,
                            'product_uos': obj.product_uom.id,
                            'location_id': location_id,
                            'procure_method': obj.product_id.product_tmpl_id.procure_method,
                            'move_id': move_id,
                        })
            wf_service = netsvc.LocalService("workflow")
            wf_service.trg_validate(uid, 'mrp.procurement', proc_id, 'button_confirm', cr)
                    
        return True
    
    
    def product_id_change(self, cr, uid, ids, product, uom=False):
        if not product:
            return {'value': { 'product_uom': False},'domain': {'product_uom': []}}
        product_obj =  self.pool.get('product.product').browse(cr, uid, product)
        result = {}
        if not uom:
            result['product_uom'] = product_obj.uom_id.id
            domain = {'product_uom':
                        [('category_id', '=', product_obj.uom_id.category_id.id)],}
        return {'value': result}
stock_planning()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
