# -*- encoding: utf-8 -*-
#################################################################################
#                                                                               #
#    base_json_field for OpenERP                                          #
#    Copyright (C) 2011 Akretion Sébastien BEAU <sebastien.beau@akretion.com>   #
#                                                                               #
#    This program is free software: you can redistribute it and/or modify       #
#    it under the terms of the GNU Affero General Public License as             #
#    published by the Free Software Foundation, either version 3 of the         #
#    License, or (at your option) any later version.                            #
#                                                                               #
#    This program is distributed in the hope that it will be useful,            #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#    GNU Affero General Public License for more details.                        #
#                                                                               #
#    You should have received a copy of the GNU Affero General Public License   #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.      #
#                                                                               #
#################################################################################

from osv import fields, osv
import netsvc
import json

class json_osv(osv.osv):
    
    #TODO : json in product.template and json in product.product

    def _get_js_fields(self, fields):
        self_fields = self._columns.keys()
        js_store_fields = {}
        js_fields = []
        for field in fields:
            if 'x_js_' in field and field in self_fields:
                store_field = field.split('_x_')[0].replace('x_js_', '')
                if js_store_fields.get(store_field, False):
                    js_store_fields[store_field] += [field]
                else:
                    js_store_fields[store_field] = [field]
                js_fields += [field]
        return js_store_fields, js_fields

    def convert_m2o_to_json(self, cr, uid, vals, fields, context=None):
        object_rel_list = {}
        res={}
        for field in fields:
            if self._columns[field]._type == 'many2one':
                if object_rel_list.get(self._columns[field]._obj):
                    object_rel_list[self._columns[field]._obj] += [vals[field]]
                else:
                    object_rel_list[self._columns[field]._obj] = [vals[field]]
                    res[self._columns[field]._obj] = {}
        for object_rel in object_rel_list:
            obj = self.pool.get(object_rel)
            object_read = obj.read(cr, uid, object_rel_list[object_rel], [obj._rec_name], context)
            for o in object_read:
                res[object_rel][o['id']] = o[obj._rec_name]
        for field in fields:
            if self._columns[field]._type == 'many2one':
                vals[field] = [vals[field] ,res[self._columns[field]._obj][vals[field]]]
        return vals

    def read(self, cr, uid, ids, fields=None, context=None, load='_classic_read'):
        if not fields:
            fields = [x for x in self._columns.keys() if not 'x_js' in x]
            return super(json_osv, self).read(cr, uid, ids, fields, context, load)
        elif not 'x_js_' in '/'.join(fields):
            return super(json_osv, self).read(cr, uid, ids, fields, context, load)
        else:
            js_store_fields, js_fields = self._get_js_fields(fields)
            fields_to_read = list(set(fields + js_store_fields.keys()) - set(js_fields))
            res = super(json_osv, self).read(cr, uid, ids, fields_to_read, context, load)
            if js_store_fields:
                for object in res:
                    if type(object) == dict:
                        for store_field in js_store_fields:
                            if object[store_field]:
                                values = json.loads(object[store_field])
                            else:
                                values = {}
                            for field in js_store_fields[store_field]:
                                if ('x_js_'+ store_field +'_x_') in field:
                                    object[field] = values.get(field, False)
                        for field in js_store_fields:
                            if not field in fields: 
                                del object[field] 
            return res

    def create(self, cr, uid, vals, context=None):
        if 'x_js_' in '/'.join(vals.keys()):
            js_store_fields, js_fields = self._get_js_fields(vals.keys())
            for js_store_field in js_store_fields:
                res={}
                for key in js_store_fields[js_store_field]:
                    res[key] = vals[key]
                    del vals[key]
                vals[js_store_field] = json.dumps(res)
        return super(json_osv, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        print "\n\nwrite\n\n", vals
        if 'x_js_' in '/'.join(vals.keys()):
            js_store_fields, js_fields = self._get_js_fields(vals.keys())
            wrid = []
            for object in self.read(cr, uid, ids, fields=js_store_fields, context=context):
                tmp_vals = vals.copy()
                tmp_vals = self.convert_m2o_to_json(cr, uid, tmp_vals, js_fields, context=context)
                for js_store_field in js_store_fields:
                    #Read the actual value of json store field
                    if object[js_store_field]:
                        res = json.loads(object[js_store_field])
                    else:
                        res = {}
                    #Update the json store field with the value and remove json field from the tmp_vals
                    for key in js_store_fields[js_store_field]:
                        res[key] = tmp_vals[key]
                        del tmp_vals[key]
                    tmp_vals[js_store_field] = json.dumps(res)
                print 'write in jsonnnnn', tmp_vals
                wrid += [super(json_osv, self).write(cr, uid, object['id'], tmp_vals, context=context)]
            return wrid
        else:
            print "\n\n\n pas decriture dans le json", self._name, "\n\n\n"
            return super(json_osv, self).write(cr, uid, ids, vals, context)