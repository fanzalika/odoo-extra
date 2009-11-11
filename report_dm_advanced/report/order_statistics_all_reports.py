# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import datetime

from report.interface import report_rml
from report.interface import toxml 
from tools.misc import ustr
import pooler
from tools.translate import _

def lengthmonth(year, month):
    if month == 2 and ((year % 4 == 0) and ((year % 100 != 0) or (year % 400 == 0))):
        return 29
    return [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    
def get_month_name(cr, uid, month):
    _months = {1:_("January"), 2:_("February"), 3:_("March"), 4:_("April"), 5:_("May"), 6:_("June"), 7:_("July"), 8:_("August"), 9:_("September"), 10:_("October"), 11:_("November"), 12:_("December")}
    return _months[month]
    
def get_weekday_name(cr, uid, weekday):
    _weekdays = {1:_('Mon'), 2:_('Tue'), 3:_('Wed'), 4:_('Thu'), 5:_('Fri'), 6:_('Sat'), 7:_('Sun')}
    return _weekdays[weekday]    
    
def origin_create_xml(cr, uid, s_id, som, eom, origin, field, s_field, model):
    cond = " where %s in %s and s.date_order >= '%s' and s.date_order < '%s'"%(field, tuple(s_id), som.strftime('%Y-%m-%d'), eom.strftime('%Y-%m-%d'))
    if origin : 
        cond += " and %s = '%s' " %(s_field,origin)
    elif s_field :
        cond += " and %s is not null "%s_field 
    sql = "select count(id) as so_no from sale_order s %s and amount_total = 0 group by s.date_order"%cond
    cr.execute(sql)        
    so_zero_count = cr.dictfetchone()
    sql = "select count(id) as so_no, sum(amount_total) from sale_order s %s and amount_total > 0 group by s.date_order"%cond
    cr.execute(sql)        
    so_non_zero = cr.dictfetchone()
    vg = so_zero_count and  so_zero_count['so_no'] or 0
    so = so_non_zero and  so_non_zero['so_no'] or 0
    tx_conv = vg and (so/vg) or 0
    ca = so_non_zero and  so_non_zero['sum'] or 0
    mmc = so and (ca/so) or 0
    xml = '''
    <origin name="%s"> 
        <vg>%s</vg>
        <so>%s</so>
        <tx_conv>%s</tx_conv>
        <ca>%s</ca>
        <mmc>%s</mmc>
    </origin>
    '''%(origin or 'Total', vg, so, tx_conv, ca, mmc)
    return xml

def row_create_xml(cr, uid, s_id, som, eom, origin, field, s_field, cal, model):
    # Compunting the attendence by analytical account
    cond = " where %s = %s and s.date_order >= '%s' and s.date_order < '%s' "%(field, s_id, som.strftime('%Y-%m-%d'), eom.strftime('%Y-%m-%d'))
    if origin : 
        cond += " and %s = '%s' " %(s_field,origin)
    elif s_field :
        cond += " and %s is not null "%s_field
    sql = "select %s as qty, s.date_order from sale_order s %s group by s.date_order"%(cal, cond)
    cr.execute(sql)
    # Sum by day
    month = {}
    res = cr.dictfetchall()
    for r in res:
        day = int(r['date_order'][-2:])
        month[day] = month.get(day, 0.0) + r['qty']
    
    xml = '''
    <time-element date="%s">
        <amount>%.2f</amount>
    </time-element>
    '''
    time_xml = ([xml % (day, amount) for day, amount in month.iteritems()])

    pool = pooler.get_pool(cr.dbname)
    segment = pool.get(model).browse(cr,uid,s_id).name

    # Computing the xml
    xml = '''
    <row id="%d" name="%s">
    %s
    </row>
    ''' % (s_id, ustr(toxml(segment)), '\n'.join(time_xml))
    return xml

class report_custom(report_rml):
    def create_xml(self, cr, uid, ids, data, context):
        pool = pooler.get_pool(cr.dbname)
        
       
        # Computing the dates (start of month: som, and end of month: eom)
        som = datetime.datetime.strptime(data['form']['start_date'],'%Y-%m-%d')
        eom = datetime.datetime.strptime(data['form']['end_date'],'%Y-%m-%d')

        level_selection = {
                'campaign':'Campaign',
                'offer':'Commercial Offer',
                'segment':'Segment'
                }
        result_selection = {
                'qty':'Quantity',
                'amt':'Amount',
                }
                
        date_xml = ['<date from_month_year="%s" to_month_year="%s"/>'
                %(datetime.datetime.strftime(som,'%d/%m/%Y'),
                    datetime.datetime.strftime(eom,'%d/%m/%Y')) , '<days>' ]
                    
        date_xml += ['<day number="%d" string="%d"/>' % 
                                (x+1, 
                                (som+datetime.timedelta(days=x)).day 
                                )
                                for x in range(0, (eom-som).days+1)]   
        col_widths = [1.25]*((eom-som).days+1)
        title_width = col_widths < 20 and 20.00 or 10.00
        total_width = sum([1.25]*((eom-som).days+1), title_width + 1.25)
        date_xml.append('</days>')
        date_xml.append('<cols twidth="%s" >%scm%s,1.25cm</cols>\n'
                            % (str(total_width), title_width, ',1.25cm' * ((eom-som).days+1)))
        
        if data['form']['level'] in ('segment','campaign') :
            camp_id = data['form']['campaign_id']
            camp = pool.get('dm.campaign').browse(cr,uid,camp_id)
            name = camp.name
            if data['form']['level'] == 'segment' :
                row_id = pool.get('dm.campaign.proposition.segment').search(cr,uid,[('campaign_id','=',camp_id)])
                field = 'segment_id'
                model = 'dm.campaign.proposition.segment'
                t2 = " per Segments Of Campaign"
            else :
                offer_id = camp.offer_id.id
                row_id = pool.get('dm.offer.step').search(cr,uid,[('offer_id','=',offer_id)])
                field = 'offer_step_id'
                model = 'dm.offer.step'
                t2 = " per Offer Step of Campaign"
        elif data['form']['level'] == 'offer' :
            offer_id = data['form']['offer_id']
            offer = pool.get('dm.offer.step').browse(cr,uid,offer_id)
            name = offer.name
            row_id = pool.get('dm.offer.step').search(cr,uid,[('offer_id','=',offer_id)])        
            field = 'offer_step_id'
            model = 'dm.offer.step'
            t2 = " per Offer Steps"

        if data['form']['result'] == 'amt' :
            cal = 'sum(amount_total)'
            t1 = 'Income'
        elif data['form']['result'] == 'qty' :
            cal = 'count(id)'
            t1 = 'Order Quantity'
        
        origin=['',]
        s_field = ''
        split_by = data['form']['split_by']
        if split_by == 'origin_partner':
            cr.execute("select distinct origin from sale_order where origin is not null")
            origin = map(lambda x: x[0],cr.fetchall())
            origin.sort()
            s_field = 'origin'
        elif split_by == 'segment' and data['form']['level'] == 'campaign':
            origin = pool.get('dm.campaign.proposition.segment').search(cr,uid,[('campaign_id','=',camp_id)])
            s_field = 'segment_id'

        header_xml = '<header level="%s" result="%s" name="%s" split_by="%s" />' \
                      %(level_selection[data['form']['level']],
                       result_selection[data['form']['result']],
                       ustr(name), data['form']['split_by'] or '' )


        story_xml = ''
        n = name = t1 + t2
        origin_xml = ''
        for i in range(len(origin)) :
            row_xml=''
            for r_id in row_id:
                row_xml += row_create_xml(cr, uid, r_id, som, eom, origin[i], field, s_field, cal, model)
            if origin[i]:
                n =name + ' from %s'%origin[i]
            origin_xml += origin_create_xml(cr, uid, row_id, som, eom, origin[i], field, s_field, model)
            story_xml += "<story s_id='%d' name='%s'> %s </story>"%(i,ustr(toxml(n)),ustr(row_xml))
            
        if split_by:
            origin_xml += origin_create_xml(cr, uid, row_id, som, eom, '', field, s_field, model)
        # Computing the xml
        xml = '''<?xml version="1.0" encoding="UTF-8" ?>
        <report>%s
        %s
        %s
        %s
        </report>
        ''' % (ustr(header_xml), ustr(origin_xml), ustr(''.join(date_xml)), ustr(story_xml) or '<story/>' )
        
        return xml

report_custom('report.dm.statistics.so.all', 'dm.campaign', '', 'addons/report_dm_advanced/report/order_statistics_all_reports.xsl')
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
