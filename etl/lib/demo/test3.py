#!/usr/bin/python

import sys
sys.path.append('..')

import etl
from etl import transformer

fileconnector=etl.connector.file_connector.file_connector('input/invoice.csv')
transformer_description= {'id':transformer.transformer.LONG,'name':transformer.transformer.STRING,'invoice_date':transformer.transformer.DATE,'invoice_amount':transformer.transformer.FLOAT,'is_paid':transformer.transformer.BOOLEAN}    
transformer=transformer.transformer(transformer_description)
csv_in1= etl.component.input.csv_in.csv_in('Invoice File',fileconnector=fileconnector,transformer=transformer)
log1=etl.component.transform.logger.logger(name='Read Invoice File')
tran=etl.transition.transition(csv_in1,log1)
job1=etl.job.job('job of test3',[log1])
job1.run()
