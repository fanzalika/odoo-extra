# -*- encoding: utf-8 -*-
##############################################################################
#
#    ETL system- Extract Transfer Load system
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
"""
This is an ETL Component that use to write data into facebook.
"""

from etl.component import component


class facebook_out(component):
    """
    # To do: to make comment here..
    """

    def __init__(self,facebook_connector,method,domain=[],fields=['name'],name='component.input.facebook_out',transformer=None,row_limit=0):
        super(facebook_out, self).__init__(name=name, connector=facebook_connector, transformer=transformer,row_limit=row_limit)        
        self._type='component.output.facebook_out'
        self.method=method
        self.domain=domain
        self.fields=fields

    def __copy__(self):        
        res=facebook_out(self.connector, self.name, self.transformer, self.row_limit)
        return res  

    def end(self):
        super(facebook_out, self).end()
        if self.facebook:
            self.connector.close(self.facebook)
            self.facebook=False
        

    def process(self): 
        self.facebook = False
        for channel,trans in self.input_get().items():
            for iterator in trans:
                for d in iterator:  
                    if not self.facebook:                       
                        self.facebook=self.connector.open()
                    self.connector.execute(self.facebook,self.method,fields=self.fields)                    
                    yield d, 'main'
                           


def test():
    pass

if __name__ == '__main__':
    pass
