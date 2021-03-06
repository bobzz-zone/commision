# -*- coding: utf-8 -*-
# Copyright (c) 2015, bobzz and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import  date_diff,flt,cint
import math

class CommisionSummary(Document):
	def on_submit(self):
		update = frappe.db.sql("""update `tabSales Invoice` set commision_redeemed=1 where name IN ({}) """.format(self.invoice_list))
	def on_cancel(self):
		update = frappe.db.sql("""update `tabSales Invoice` set commision_redeemed=0 where name IN ({}) """.format(self.invoice_list))
	def generate(self):
		#get all setting vriable
		special_brand = frappe.db.get_single_value('Commision Setting','brand')
		bonus_jual = flt(frappe.db.get_single_value('Commision Setting','bonus_jual'),3)
		bonus_tagih = flt(frappe.db.get_single_value('Commision Setting','bonus_tagih'),3)
		spesial_hangus = flt(frappe.db.get_single_value('Commision Setting','spesial_hangus'),3)
		jual_hangus = flt(frappe.db.get_single_value('Commision Setting','jual_hangus'),3)
		#Selecting invoice due and save to an array
		#list of sales
		sales = frappe.db.sql("""select name,supervisor from tabSales """,as_dict=1)
		
		#list of invoice for sales commision OBP , insentif
		invoice = frappe.db.sql("""select si.name,si.posting_date,sit.item_code,si.brand , si.sales , sit.qty as "jumlah", sit.amount  , DATEDIFF(pe.posting_date,si.posting_date) as "days" , si.commision_type
			from `tabSales Invoice Item` sit
			left join `tabPayment Entry Reference` per on per.reference_name = sit.parent
			left join `tabPayment Entry` pe on per.parent=pe.name
			join `tabSales Invoice`  si on si.name = sit.parent
			where si.docstatus=1 and si.outstanding_amount<=0 and si.brand is not null and si.sales is not null and si.commision_redeemed =0 and si.commision_type in ("OBP","Kursi susun")
			and si.posting_date < "{}"
		 """.format(self.to_date),as_dict=1)
		sales_total={}
		payment={}
		sales_commision={}
		supervisor_commision={}
		inv_list=""
		inv_special=""
		ks={}
		#filter total sales per brand
		for row in invoice:
			if inv_list=="":
				inv_list=""" "{}" """.format(row.name)
			elif not row.name in inv_list:
				inv_list=""" {},"{}" """.format(inv_list,row.name)
			if row['days']<=spesial_hangus and row['brand']==special_brand:
				if inv_special=="":
					inv_special=""" "{}" """.format(row.name)
				elif not row.name in inv_special:
					inv_special=""" {},"{}" """.format(inv_special,row.name)
			if not row['sales'] in sales_total:
				sales_total[row['sales']]={}
			if not row['brand'] in sales_total[row['sales']]:
				sales_total[row['sales']][row['brand']]={'qty':0,'total':0,'total_penjualan':0}

			if row['brand']==special_brand and row['commision_type']=='Kursi susun':
				if row['days']<=spesial_hangus:
					sales_total[row['sales']][row['brand']]['qty']+=flt(row['jumlah'],3)
					sales_total[row['sales']][row['brand']]['total']+=flt(row['amount'],3)
					if not row['sales'] in sales_commision:
						sales_commision[key]={}
						sales_commision[key]['sales']=row['sales']
						sales_commision[key]['insentif']=0
						sales_commision[key]['obp']=0
						sales_commision[key]['supervisor_insentif']=0
						sales_commision[key]['kupon']=0
						sales_commision[key]['kursi susun']=0
						sales_commision[key]['tagih']=0
						sales_commision[key]['supervisor']=0
					sales_commision[key]['kursi susun']+=flt(row['jumlah'],3)*bonus_jual
					if not row['sales'] in ks:
						ks[row['sales']]={}
						ks[row['sales']]['omset']=0
						ks[row['sales']]['komisi']=0
					ks[row['sales']]['komisi']+=flt(row['jumlah'],3)*bonus_jual
					ks[row['sales']]['omset']=flt(row['amount'],3)
			elif row['days'] <= jual_hangus:
				sales_total[row['sales']][row['brand']]['qty']+=flt(row['jumlah'],3)
				sales_total[row['sales']][row['brand']]['total']+=flt(row['amount'],3)
			sales_total[row['sales']][row['brand']]['total_penjualan']+=flt(row['amount'],3)
			
		#get sales target
		sales_target = frappe.db.sql("""select st.sales,st.target,st.brand,s.supervisor from `tabSales Target` st join tabSales s on st.sales=s.name""",as_dict=1)
		for da in sales_target:
			if not da['sales'] in sales_total:
				sales_total[da['sales']]={}
			if not da['brand'] in sales_total[da['sales']]:
				sales_total[da['sales']][da['brand']]={'qty':0,'total':0,'total_penjualan':0}
			sales_total[da['sales']][da['brand']]['target']=flt(da.target,3)
			if not da['sales'] in sales_commision:
				sales_commision[da['sales']]={}
				sales_commision[da['sales']]['sales']=da['sales']
				sales_commision[da['sales']]['insentif']=0
				sales_commision[da['sales']]['obp']=0
				sales_commision[da['sales']]['supervisor_insentif']=0
				sales_commision[da['sales']]['kupon']=0
				sales_commision[da['sales']]['kursi susun']=0
				sales_commision[da['sales']]['tagih']=0
				sales_commision[da['sales']]['supervisor']=0
			sales_commision[da['sales']]['supervisor']=da.supervisor
			
		#get insentf per sales
		brand_with_insentif = frappe.db.sql("""select brand from `tabTarget Matrix`""",as_list=1)
		for brand in brand_with_insentif:
			level = frappe.db.sql("""select target,bonus,bonus90 from `tabTarget Matrix Item` order by target asc """,as_list=1)
			for key in sales_total.keys():
				if not brand[0] in sales_total[key]:
					continue
				if not key in sales_commision:
					sales_commision[key]={}
					sales_commision[key]['sales']=key
					sales_commision[key]['insentif']=0
					sales_commision[key]['obp']=0
					sales_commision[key]['supervisor_insentif']=0
					sales_commision[key]['kupon']=0
					sales_commision[key]['kursi susun']=0
					sales_commision[key]['tagih']=0
					sales_commision[key]['supervisor']=0
				if brand[0] not in sales_total[key]:
					continue
				if 'target' not in sales_total[key][brand[0]]:
					continue
				if (sales_total[key][brand[0]]['total']*0.95)>=sales_total[key][brand[0]]['target']:
					for step in level:
						if step[0]==sales_total[key][brand[0]]['target']:
							sales_commision[key]['insentif']+=step[1]
							break
				elif (sales_total[key][brand[0]]['total']*0.95)>=(sales_total[key][brand[0]]['target']*0.9):
					for step in level:
						if step[0]==sales_total[key][brand[0]]['target']:
							sales_commision[key]['insentif']+=step[2]
							break

		#get sales OBP per sales
		brand_with_obp = frappe.db.sql("""select brand from `tabOBP Matrix`""",as_list=1)
		for brand in brand_with_obp:
			level = frappe.db.sql("""select achieve,commision from `tabOBP Matrix Item` order by achieve asc """,as_list=1)
			for key in sales_total.keys():
				if brand[0] not in sales_total[key]:
					continue
				if 'target' not in sales_total[key][brand[0]]:
					continue
				obp = ((sales_total[key][brand[0]]['total']*0.95)/sales_total[key][brand[0]]['target'])*100
				if not key in sales_commision:
					sales_commision[key]={}
					sales_commision[key]['sales']=key
					sales_commision[key]['obp']=0
					sales_commision[key]['supervisor_insentif']=0
					sales_commision[key]['kupon']=0
					sales_commision[key]['kursi susun']=0
					sales_commision[key]['insentif']=0
					sales_commision[key]['supervisor']=0
					sales_commision[key]['tagih']=0
				multi=0
				for step in level:
					if step[0]<obp:
						multi=step[1]
				sales_commision[key]['obp']+=multi*(sales_total[key][brand[0]]['total']*0.95)
				if obp>=100:
					sales_commision[key]['supervisor_insentif']+=0.13*(sales_total[key][brand[0]]['total_penjualan']*0.95)
				else:
					sales_commision[key]['supervisor_insentif']+=0.1*(sales_total[key][brand[0]]['total_penjualan']*0.95)

		#get komisi tagih per sales
		if inv_list!="":
		#get payment data
			payment_data = frappe.db.sql("""select pr.sales,(pr.allocated_amount-pr.discount_accumulated) as "payment",
				DATEDIFF(pe.posting_date,si.posting_date) as 'days'
				from `tabPayment Entry Reference` pr 
				join `tabPayment Entry` pe on pr.parent=pe.name
				left join `tabSales Invoice` si on pr.reference_name = si.name
				where pr.reference_doctype="Sales Invoice" and pe.docstatus=1 and pr.reference_name IN ({})
			""".format(inv_list),as_dict=1)

			komisi_tagih = frappe.db.sql("""select days,commision from `tabKomisi Tagih` order by days asc""",as_dict=1)

			for p in payment_data:
				if not p['sales'] in sales_commision:
					sales_commision[p['sales']]={}
					sales_commision[p['sales']]['sales']=p['sales']
					sales_commision[p['sales']]['obp']=0
					sales_commision[p['sales']]['supervisor_insentif']=0
					sales_commision[p['sales']]['kupon']=0
					sales_commision[p['sales']]['kursi susun']=0
					sales_commision[p['sales']]['insentif']=0
					sales_commision[p['sales']]['tagih']=0
					sales_commision[p['sales']]['supervisor']=0
				lc=0
				for kt in komisi_tagih:
					if kt['days']>p['days']:
						sales_commision[p['sales']]['tagih']+= flt(kt['commision'])*flt(p['payment'],3)/100
						lc=-1
						break
					lc = flt(kt['commision'],3)
				#give the last tier of commision
				if lc >-1:
					sales_commision[p['sales']]['tagih']+=lc*flt(p['payment'],3)/100
		#calculate kupon
		#should make a query for kupon	
		invoice_kupon = frappe.db.sql("""select sit.kupon_bonus as 'bonus' , si.sales,si.name
		from `tabSales Invoice Item` sit
		join `tabSales Invoice` si on sit.parent=si.name
		where si.docstatus=1 and si.commision_type="Kupon" and si.sales is not null and si.commision_redeemed =0 and si.posting_date<"{}" 
		""".format(self.to_date),as_dict=1)
		for row_kupon in invoice_kupon:
			if inv_list=="":
				inv_list=""" "{}" """.format(row_kupon['name'])
			elif not row_kupon['name'] in inv_list:
				inv_list=""" {},"{}" """.format(inv_list,row_kupon['name'])
			if not row_kupon['sales'] in sales_commision:
				sales_commision[row_kupon['sales']]={}
				sales_commision[row_kupon['sales']]['sales']=row_kupon['sales']
				sales_commision[row_kupon['sales']]['obp']=0
				sales_commision[row_kupon['sales']]['supervisor_insentif']=0
				sales_commision[row_kupon['sales']]['kupon']=0
				sales_commision[row_kupon['sales']]['kursi susun']=0
				sales_commision[row_kupon['sales']]['insentif']=0
				sales_commision[row_kupon['sales']]['tagih']=0
				sales_commision[row_kupon['sales']]['supervisor']=""
			sales_commision[row_kupon['sales']]['kupon']+=flt(row_kupon['bonus'])

		self.invoice_list=inv_list
		self.sales=[]
		for det in sales_commision:
			det_item = self.append("sales",{})
			det_item.sales =sales_commision[det]['sales']
			det_item.supervisor = sales_commision[det]['supervisor']
			det_item.jual =flt(sales_commision[det]['obp'])
			det_item.insentif_sales = flt(sales_commision[det]['insentif'])
			det_item.tagih=flt(sales_commision[det]['tagih'])
			det_item.kupon = flt(sales_commision[det]['kupon'])
			det_item.kursi_susun = flt(sales_commision[det]['kursi susun'])
			det_item.total_sales = flt(sales_commision[det]['obp'])+flt(sales_commision[det]['insentif'])+flt(sales_commision[det]['kupon'])+flt(sales_commision[det]['tagih'])
			det_item.total_supervisor = flt(sales_commision[det]['supervisor_insentif'])
			

def invoice_on_submit(doc,method):
	if doc.commision_type=="Kupon":
		coupon = frappe.db.sql("""select item,qty,bonus,valid_to,valid_from from `tabCoupon Bonus` where valid_from<="{}" and valid_to >="{}" """.format(doc.posting_date),as_dict=1)
		for item in doc.items:
			for x in coupon:
				if item.item_code == x.item:
					item.kupon_bonus = floor(flt(item.qty)/flt(x.qty))*flt(x.bonus)
					continue