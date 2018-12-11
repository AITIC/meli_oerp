# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, osv
from odoo.tools.translate import _

import pdb
import logging
_logger = logging.getLogger(__name__)

import requests
import base64
import mimetypes
from urllib.request import urlopen

from datetime import datetime

from .meli_oerp_config import *

from ..melisdk.meli import Meli


class product_template(models.Model):
    _inherit = "product.template"

    def product_template_post(self):
        product_obj = self.env['product.template']
        product = self
        company = self.env.user.company_id
        warningobj = self.env['warning']

        REDIRECT_URI = company.mercadolibre_redirect_uri
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token


        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        if ACCESS_TOKEN=='':
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
            url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
            return {
                "type": "ir.actions.act_url",
                "url": url_login_meli,
                "target": "new",
            }

        _logger.info("Product Template Post")

        for variant in product.product_variant_ids:
            _logger.info("Variant:", variant)
            if (variant.meli_pub):
                _logger.info("Posting variant")
                variant.product_post()

        return {}

    @api.one
    def product_template_stats(self):

        _pubs = ""
        _stats = ""
        product = self
        for variant in product.product_variant_ids:
            if (variant.meli_pub):
                if ( (variant.meli_status=="active" or variant.meli_status=="paused") and variant.meli_id):
                    if (len(_pubs)):
                        _pubs = _pubs + "|" + variant.meli_id + ":" + variant.meli_status
                    else:
                        _pubs = variant.meli_id + ":" + variant.meli_status

                    if (variant.meli_status=="active"):
                        _stats = "active"

                    if (_stats == "" and variant.meli_status=="paused"):
                        _stats = "paused"

        self.meli_publications = _pubs
        self.meli_variants_status = _stats

        return {}


    @api.multi
    def action_meli_pause(self):
        product = self
        for variant in product.product_variant_ids:
            if (variant.meli_pub):
                variant.product_meli_status_pause()
        return {}

    @api.multi
    def action_meli_activate(self):
        product = self
        for variant in product.product_variant_ids:
            if (variant.meli_pub):
                variant.product_meli_status_active()
        return {}

    @api.multi
    def action_meli_close(self):
        product = self
        for variant in product.product_variant_ids:
            if (variant.meli_pub):
                variant.product_meli_status_close()
        return {}

    @api.multi
    def action_meli_delete(self):
        product = self
        for variant in product.product_variant_ids:
            if (variant.meli_pub):
                variant.product_meli_delete()
        return {}

    @api.onchange('meli_pub') # if these fields are changed, call method
    def change_meli_pub(self):
        product = self
        for variant in product.product_variant_ids:
            variant.meli_pub = product.meli_pub
        return {}


    name = fields.Char('Name', size=128, required=True, translate=False, select=True)
    meli_title = fields.Char(string='Nombre del producto en Mercado Libre',size=256)
    meli_description = fields.Text(string='Descripción')
    meli_category = fields.Many2one("mercadolibre.category","Categoría de MercadoLibre")
    meli_buying_mode = fields.Selection( [("buy_it_now","Compre ahora"),("classified","Clasificado")], string='Método de compra')
    meli_price = fields.Char(string='Precio de venta', size=128)
    meli_currency = fields.Selection([("ARS","Peso Argentino (ARS)"),
    ("MXN","Peso Mexicano (MXN)"),
    ("COP","Peso Colombiano (COP)")],string='Moneda')
    meli_condition = fields.Selection([ ("new", "Nuevo"), ("used", "Usado"), ("not_specified","No especificado")],'Condición del producto')
    meli_dimensions = fields.Char( string="Dimensiones del producto", size=128)
    meli_pub = fields.Boolean('Meli Publication',help='MELI Product')
    meli_warranty = fields.Char(string='Garantía', size=256)
    meli_listing_type = fields.Selection([("free","Libre"),("bronze","Bronce"),("silver","Plata"),("gold","Oro"),("gold_premium","Gold Premium"),("gold_special","Gold Special/Clásica"),("gold_pro","Oro Pro")], string='Tipo de lista')
    meli_attributes = fields.Text(string='Atributos')

    meli_publications = fields.Text(compute=product_template_stats,string='Publicaciones en ML')
    meli_variants_status = fields.Text(compute=product_template_stats,string='Meli Variant Status')


product_template()

class product_product(models.Model):

    _inherit = "product.product"

    #@api.one
    @api.onchange('lst_price') # if these fields are changed, call method
    def check_change_price(self):
	# GUS
        #pdb.set_trace();
        #pricelists = self.env['product.pricelist'].search([])
        #if pricelists:
        #    if pricelists.id:
        #        pricelist = pricelists.id
        #    else:
        #        pricelist = pricelists[0].id
        self.meli_price = str(self.lst_price)
        #res = {}
        #for id in self:
        #    res[id] = self.lst_price
        #return res


    def product_meli_get_product( self ):
        company = self.env.user.company_id
        product_obj = self.env['product.product']
        #pdb.set_trace()
        product = self

        _logger.info("product_meli_get_product")
        #_logger.info(product)

        product_template_obj = self.env['product.template']
        product_template = product_template_obj.browse(product.product_tmpl_id.id)

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        try:
            response = meli.get("/items/"+product.meli_id, {'access_token':meli.access_token})
            #_logger.info(response)
            rjson = response.json()
            #_logger.info(rjson)
        except IOError as e:
            _logger.info( "I/O error({0}): {1}".format(e.errno, e.strerror) )
            return {}
        except:
            _logger.info( "Rare error" )
            return {}



        des = ''
        desplain = ''
        vid = ''
        if 'error' in rjson:
            return {}

        #if "content" in response:
        #    _logger.info(response.content)
        #    _logger.info( "product_meli_get_product > response.content: " + response.content )

        #TODO: traer la descripcion: con
        #https://api.mercadolibre.com/items/{ITEM_ID}/description?access_token=$ACCESS_TOKEN
        if rjson and rjson['descriptions']:
            response2 = meli.get("/items/"+product.meli_id+"/description", {'access_token':meli.access_token})
            rjson2 = response2.json()
            if 'text' in rjson2:
               des = rjson2['text']
            if 'plain_text' in rjson2:
               desplain = rjson2['plain_text']
            if (len(des)>0):
                desplain = des

        #TODO: verificar q es un video
        if rjson['video_id']:
            vid = ''

        #TODO: traer las imagenes
        #TODO:
        pictures = rjson['pictures']
        if pictures and len(pictures):
            thumbnail_url = pictures[0]['url']
            image = urlopen(thumbnail_url).read()
            image_base64 = base64.encodestring(image)
            product.image_medium = image_base64
            #if (len(pictures)>1):
                #complete product images:
                #delete all images...

        #categories
        mlcatid = ""
        www_cat_id = False
        if ('category_id' in rjson):
            category_id = rjson['category_id']
            ml_cat = self.env['mercadolibre.category'].search([('meli_category_id','=',category_id)])
            ml_cat_id = ml_cat.id
            if (ml_cat_id):
                #_logger.info( "category exists!" + str(ml_cat_id) )
                mlcatid = ml_cat_id
                www_cat_id = ml_cat.public_category_id
            else:
                #_logger.info( "Creating category: " + str(category_id) )
                #https://api.mercadolibre.com/categories/MLA1743
                response_cat = meli.get("/categories/"+str(category_id), {'access_token':meli.access_token})
                rjson_cat = response_cat.json()
                #_logger.info( "category:" + str(rjson_cat) )
                fullname = ""
                if ("path_from_root" in rjson_cat):
                    path_from_root = rjson_cat["path_from_root"]
                    p_id = False
                    #pdb.set_trace()
                    for path in path_from_root:
                        fullname = fullname + "/" + path["name"]

                        if (company.mercadolibre_create_website_categories):
                            www_cats = self.env['product.public.category']
                            if www_cats!=False:
                                www_cat_id = www_cats.search([('name','=',path["name"])]).id
                                if www_cat_id==False:
                                    www_cat_fields = {
                                      'name': path["name"],
                                      #'parent_id': p_id,
                                      #'sequence': 1
                                    }
                                    if p_id:
                                        www_cat_fields['parent_id'] = p_id
                                    www_cat_id = www_cats.create((www_cat_fields)).id
                                    if www_cat_id:
                                        _logger.info("Website Category created:"+fullname)

                                p_id = www_cat_id

                #fullname = fullname + "/" + rjson_cat['name']
                #_logger.info( "category fullname:" + fullname )
                cat_fields = {
                    'name': fullname,
                    'meli_category_id': ''+str(category_id),
                    'public_category_id': 0,
                }

                if www_cat_id:
                    p_cat_id = www_cats.search([('id','=',www_cat_id)])
                    cat_fields['public_category_id'] = www_cat_id
                    #cat_fields['public_category'] = p_cat_id

                ml_cat_id = self.env['mercadolibre.category'].create((cat_fields)).id
                if (ml_cat_id):
                    mlcatid = ml_cat_id

        imagen_id = ''
        meli_dim_str = ''
        if ('dimensions' in rjson):
            if (rjson['dimensions']):
                meli_dim_str = rjson['dimensions']

        if ('pictures' in rjson):
            if (len(rjson['pictures'])>0):
                imagen_id = rjson['pictures'][0]['id']

        meli_fields = {
            'name': rjson['title'].encode("utf-8"),
            'default_code': rjson['id'],
            #'name': str(rjson['id']),
            'meli_imagen_id': imagen_id,
            'meli_post_required': True,
            'meli_id': rjson['id'],
            'meli_permalink': rjson['permalink'],
            'meli_title': rjson['title'].encode("utf-8"),
            'meli_description': desplain,
#            'meli_description_banner_id': ,
            'meli_category': mlcatid,
            'meli_listing_type': rjson['listing_type_id'],
            'meli_buying_mode':rjson['buying_mode'],
            'meli_price': str(rjson['price']),
            'meli_price_fixed': True,
            'meli_currency': rjson['currency_id'],
            'meli_condition': rjson['condition'],
            'meli_available_quantity': rjson['available_quantity'],
            'meli_warranty': rjson['warranty'],
##            'meli_imagen_logo': fields.char(string='Imagen Logo', size=256),
##            'meli_imagen_id': fields.char(string='Imagen Id', size=256),
            'meli_imagen_link': rjson['thumbnail'],
##            'meli_multi_imagen_id': fields.char(string='Multi Imagen Ids', size=512),
            'meli_video': str(vid),
            'meli_dimensions': meli_dim_str,
        }

        ml_price_convert = rjson['price']

        tmpl_fields = {
          'name': meli_fields["name"],
          #'name': str(rjson['id']),
          'lst_price': ,
          'meli_title': meli_fields["meli_title"],
          'meli_description': meli_fields["meli_description"],
          'meli_category': meli_fields["meli_category"],
          'meli_listing_type': meli_fields["meli_listing_type"],
          'meli_buying_mode': meli_fields["meli_buying_mode"],
          'meli_price': meli_fields["meli_price"],
          'meli_currency': meli_fields["meli_currency"],
          'meli_condition': meli_fields["meli_condition"],
          'meli_warranty': meli_fields["meli_warranty"],
          'meli_dimensions': meli_fields["meli_dimensions"]
        }
        #pdb.set_trace()
        if www_cat_id!=False:
            #assign
            product_template.public_categ_ids = [(4,www_cat_id)]
            #tmpl_fields["public_categ_ids"] = [(4,www_cat_id)]

        product.write( meli_fields )
        product_template.write( tmpl_fields )
        if (rjson['available_quantity']>0):
            product_template.website_published = True
        else:
            product_template.website_published = False

        posting_fields = {'posting_date': str(datetime.now()),'meli_id':rjson['id'],'product_id':product.id,'name': 'Post (ML): ' + product.meli_title }

        posting_id = self.env['mercadolibre.posting'].search([('meli_id','=',rjson['id'])]).id

        if not posting_id:
            posting = self.env['mercadolibre.posting'].create((posting_fields))
            posting_id = posting.id
            if (posting):
                posting.posting_query_questions()


        b_search_nonfree_ship = False
        if ('shipping' in rjson):
            att_shipping = {
                'name': 'Con envío',
                'create_variant': False
            }
            if ('variations' in rjson):
                #_logger.info("has variations")
                pass
            else:
                rjson['variations'] = []

            if ('free_methods' in rjson['shipping']):
                att_shipping['value_name'] = 'Sí'
                #buscar referencia del template correspondiente
                b_search_nonfree_ship = True
            else:
                att_shipping['value_name'] = 'No'

            rjson['variations'].append({'attribute_combinations': [ att_shipping ]})

        published_att_variants = False
        if ('variations' in rjson):
            #recorrer los variations>attribute_combinations y agregarlos como atributos de las variantes
            #_logger.info(rjson['variations'])
            vindex = -1
            for variation in rjson['variations']:
                vindex = vindex + 1
                if ('attribute_combinations' in variation):
                    _attcomb_str = ""
                    rjson['variations'][vindex]["default_code"] = ""
                    for attcomb in variation['attribute_combinations']:
                        att = {
                            'name': attcomb['name'],
                            'value_name': attcomb['value_name'],
                            'create_variant': True
                        }
                        if ('create_variant' in attcomb):
                            att['create_variant'] = attcomb['create_variant']
                        else:
                            rjson['variations'][vindex]["default_code"] = rjson['variations'][vindex]["default_code"]+attcomb['name']+":"+attcomb['value_name']+";"
                        #_logger.info(att)
                        attribute_id = self.env['product.attribute'].search([('name','=',att['name'])]).id
                        #_logger.info(attribute_id)
                        if attribute_id:
                            #_logger.info(attribute_id)
                            pass
                        else:
                            #_logger.info("Creating attribute:")
                            attribute_id = self.env['product.attribute'].create({ 'name': att['name'],'create_variant': att['create_variant'] }).id
                        if (att['create_variant']==True):
                            published_att_variants = True
                        if (attribute_id):
                            #_logger.info("Publishing attribute")
                            attribute_value_id = self.env['product.attribute.value'].search([('attribute_id','=',attribute_id),('name','=',att['value_name'])]).id
                            #_logger.info(_logger.info(attribute_id))
                            if attribute_value_id:
                                #_logger.info(attribute_value_id)
                                pass
                            else:
                                _logger.info("Creating attribute value:")
                                attribute_value_id = self.env['product.attribute.value'].create({'attribute_id': attribute_id,'name': att['value_name']}).id
                            if (attribute_value_id):
                                #_logger.info("attribute_value_id:")
                                #_logger.info(attribute_value_id)
                                #search for line ids.
                                attribute_line =  self.env['product.attribute.line'].search([('attribute_id','=',attribute_id),('product_tmpl_id','=',product_template.id)])
                                #_logger.info(attribute_line)
                                if (attribute_line and attribute_line.id):
                                    #_logger.info(attribute_line)
                                    pass
                                else:
                                    #_logger.info("Creating att line id:")
                                    attribute_line =  self.env['product.attribute.line'].create( { 'attribute_id': attribute_id,'product_tmpl_id': product_template.id } )

                                if (attribute_line):
                                    #_logger.info("Check attribute line values id.")
                                    #_logger.info("attribute_line:")
                                    #_logger.info(attribute_line)
                                    if (attribute_line.value_ids):
                                        #check if values
                                        #_logger.info("Has value ids:")
                                        #_logger.info(attribute_line.value_ids.ids)
                                        if (attribute_value_id in attribute_line.value_ids.ids):
                                            #_logger.info(attribute_line.value_ids.ids)
                                            pass
                                        else:
                                            #_logger.info("Adding value id")
                                            attribute_line.value_ids = [(4,attribute_value_id)]
                                    else:
                                        #_logger.info("Adding value id")
                                        attribute_line.value_ids = [(4,attribute_value_id)]

        #_logger.info("product_uom_id")
        product_uom_id = self.env['product.uom'].search([('name','=','Unidad(es)')])
        if (product_uom_id.id==False):
            product_uom_id = 1
        else:
            product_uom_id = product_uom_id.id

        _product_id = product.id
        _product_name = product.name
        _product_meli_id = product.meli_id

        #this write pull the trigger for create_variant_ids()...
        #_logger.info("rewrite to create variants")
        product_template.write({ 'attribute_line_ids': product_template.attribute_line_ids  })

        if (published_att_variants):
            product_template.meli_pub_as_variant = True

            #_logger.info("Auto check product.template meli attributes to publish")
            for line in  product_template.attribute_line_ids:
                if (line.id not in product_template.meli_pub_variant_attributes.ids):
                    if (line.attribute_id.create_variant):
                        product_template.meli_pub_variant_attributes = [(4,line.id)]

            #_logger.info("check variants")
            for variant in product_template.product_variant_ids:
                #_logger.info("Created variant:")
                #_logger.info(variant)
                variant.meli_pub = product_template.meli_pub
                variant.meli_id = rjson['id']
                variant.default_code = rjson['id']
                variant.name = str(rjson['title'].encode("utf-8"))
                has_sku = False

                _v_default_code = ""
                for att in variant.attribute_value_ids:
                    _v_default_code = _v_default_code + att.attribute_id.name+':'+att.name+';'
        #                _logger.info("_v_default_code: " + _v_default_code)
                for variation in rjson['variations']:
        #                    _logger.info("variation[default_code]: " + variation["default_code"])
                    if (_v_default_code==variation["default_code"]):
                        if (variation["seller_custom_field"]):
                            #_logger.info("has_sku")
                            #_logger.info(variation["seller_custom_field"])
                            variant.default_code = variation["seller_custom_field"]
                            has_sku = True
                        else:
                            variant.default_code = variant.meli_id+'-'+_v_default_code
                        variant.meli_available_quantity = variation["available_quantity"]

                if (has_sku):
                    variant.set_bom()

                if (product_template.meli_pub_principal_variant is None):
                    product_template.meli_pub_principal_variant = variant
                    product = variant

                if (_product_id==variant.id):
                    product = variant
        else:
            #NO TIENE variantes
            if (rjson["seller_custom_field"]):
                product.default_code = rjson["seller_custom_field"]
                product.set_bom()


        if (company.mercadolibre_update_local_stock):
            product_template.type = 'product'
            wh = self.env['stock.location'].search([('usage','=','internal')]).id
            ##product_uom_cat_id = sock.execute(dbname,uid,pwd,'product.uom.categ','search',[('name','=',"Unit")])
            #print "product_uom_cat_id:",product_uom_cat_id

            for variant in product_template.product_variant_ids:

                _product_id = variant.id
                _product_name = variant.name
                _product_meli_id = variant.meli_id

                stock_inventory_fields = {
                    "product_id": _product_id,
                    "filter": "product",
                    "location_id": wh,
                    "name": "INV: "+ variant.name
                }
                if (variant.meli_available_quantity != variant.virtual_available):
                    _logger.info("Updating stock for variant." + str(variant.meli_available_quantity) )
        #                _logger.info("stock_inventory_fields:")
        #                _logger.info(stock_inventory_fields)
                    StockInventory = self.env['stock.inventory'].create(stock_inventory_fields)
        #                _logger.info("StockInventory:")
        #                _logger.info(StockInventory)
                    if (StockInventory):
                        stock_inventory_field_line = {
                            "product_qty": variant.meli_available_quantity,
                            'theoretical_qty': 0,
                            "product_id": _product_id,
                            "product_uom_id": product_uom_id,
                            "location_id": wh,
                            'inventory_location_id': wh,
                            "inventory_id": StockInventory.id,
                            #"name": "INV "+ nombre
                            #"state": "confirm",
                        }
                        StockInventoryLine = self.env['stock.inventory.line'].create(stock_inventory_field_line)
                        #print "StockInventoryLine:", StockInventoryLine, stock_inventory_field_line
        #                    _logger.info("StockInventoryLine:")
        #                    _logger.info(StockInventoryLine)
                        if (StockInventoryLine):
                            return_id = StockInventory.action_done()
        #                        _logger.info("action_done:"+str(return_id))

        #assign envio/sin envio
        #si es (Con envio: Sí): asigna el meli_default_stock_product al producto sin envio (Con evio: No)
        if (b_search_nonfree_ship):
            ptemp_nfree = False
            ptpl_same_name = self.env['product.template'].search([('name','=',product_template.name)])
            #_logger.info("ptpl_same_name:"+product_template.name)
            #_logger.info(ptpl_same_name)
            if len(ptpl_same_name):
                for ptemp in ptpl_same_name:
                    #check if sin envio
                    _logger.info(ptemp.name)
                    for line in ptemp.attribute_line_ids:
                        #_logger.info(line.attribute_id.name)
                        #_logger.info(line.value_ids)
                        es_con_envio = False
                        try:
                            line.attribute_id.name.index('Con env')
                            es_con_envio = True
                        except ValueError:
                            pass
                            #_logger.info("not con envio")
                        if (es_con_envio==True):
                            for att in line.value_ids:
                                #_logger.info(att.name)
                                if (att.name=='No'):
                                    #_logger.info("Founded")
                                    if (ptemp.meli_pub_principal_variant):
                                        #_logger.info("has meli_pub_principal_variant!")
                                        ptemp_nfree = ptemp.meli_pub_principal_variant
                                        if (ptemp_nfree.meli_default_stock_product):
                                            #_logger.info("has meli_default_stock_product!!!")
                                            ptemp_nfree = ptemp_nfree.meli_default_stock_product
                                    else:
                                        ptemp_nfree = ptemp.product_variant_ids[0]

            if (ptemp_nfree):
                #_logger.info("Founded ptemp_nfree, assign to all variants")
                for variant in product_template.product_variant_ids:
                    variant.meli_default_stock_product = ptemp_nfree

        return {}

    def product_meli_login(self ):

        company = self.env.user.company_id

        REDIRECT_URI = company.mercadolibre_redirect_uri
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)

        url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
        #url_login_oerp = "/meli_login"


        return {
	        "type": "ir.actions.act_url",
	        "url": url_login_meli,
	        "target": "new",
        }


    def product_meli_status_close( self ):
        company = self.env.user.company_id
        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        response = meli.put("/items/"+product.meli_id, { 'status': 'closed' }, {'access_token':meli.access_token})

        #_logger.info( "product_meli_status_close: " + response.content )

        return {}

    def product_meli_status_pause( self ):
        company = self.env.user.company_id
        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        response = meli.put("/items/"+product.meli_id, { 'status': 'paused' }, {'access_token':meli.access_token})

        #_logger.info( "product_meli_status_pause: " + response.content )

        return {}

    def product_meli_status_active( self ):
        company = self.env.user.company_id
        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        response = meli.put("/items/"+product.meli_id, { 'status': 'active' }, {'access_token':meli.access_token})

        #_logger.info( "product_meli_status_active: " + response.content )

        return {}

    def product_meli_delete( self ):

        company = self.env.user.company_id
        product_obj = self.env['product.product']
        product = self

        if product.meli_status!='closed':
            self.product_meli_status_close()

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        response = meli.put("/items/"+product.meli_id, { 'deleted': 'true' }, {'access_token':meli.access_token})

        #_logger.info( "product_meli_delete: " + response.content )
        rjson = response.json()
        ML_status = rjson["status"]
        if "error" in rjson:
            ML_status = rjson["error"]
        if "sub_status" in rjson:
            if len(rjson["sub_status"]) and rjson["sub_status"][0]=='deleted':
                product.write({ 'meli_id': '' })

        return {}

    def product_meli_upload_image( self ):

        company = self.env.user.company_id

        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        #
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        if product.image==None or product.image==False:
            return { 'status': 'error', 'message': 'no image to upload' }

        # _logger.info( "product_meli_upload_image" )
        #_logger.info( "product_meli_upload_image: " + response.content )
        imagebin = base64.b64decode(product.image)
        imageb64 = product.image
#       _logger.info( "data:image/png;base64,"+imageb64 )
#       files = [ ('images', ('image_medium', imagebin, "image/png")) ]
        files = { 'file': ('image.jpg', imagebin, "image/jpeg"), }
        #_logger.info(  files )
        response = meli.upload("/pictures", files, { 'access_token': meli.access_token } )
       # _logger.info( response.content )

        rjson = response.json()
        if ("error" in rjson):
            raise osv.except_osv( _('MELI WARNING'), _('No se pudo cargar la imagen en MELI! Error: %s , Mensaje: %s, Status: %s') % ( rjson["error"], rjson["message"],rjson["status"],))
            return { 'status': 'error', 'message': 'not uploaded'}

        _logger.info( rjson )

        if ("id" in rjson):
            #guardar id
            product.write( { "meli_imagen_id": rjson["id"], "meli_imagen_link": rjson["variations"][0]["url"] })
            #asociar imagen a producto
            if product.meli_id:
                response = meli.post("/items/"+product.meli_id+"/pictures", { 'id': rjson["id"] }, { 'access_token': meli.access_token } )
            else:
                return { 'status': 'warning', 'message': 'uploaded but not assigned' }

        return { 'status': 'success', 'message': 'uploaded and assigned' }

    def product_meli_upload_multi_images( self  ):

        company = self.env.user.company_id

        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        #
        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        if product.product_image_ids==None:
            return { 'status': 'error', 'message': 'no images to upload' }

        image_ids = []
        c = 0

        #loop over images
        for product_image in product.product_image_ids:
            if (product_image.image):
                _logger.info( "product_image.image:" + str(product_image.image) )
                imagebin = base64.b64decode( product_image.image )
                #files = { 'file': ('image.png', imagebin, "image/png"), }
                files = { 'file': ('image.jpg', imagebin, "image/jpeg"), }
                response = meli.upload("/pictures", files, { 'access_token': meli.access_token } )
                _logger.info( "meli upload:" + response.content )
                rjson = response.json()
                if ("error" in rjson):
                    raise osv.except_osv( _('MELI WARNING'), _('No se pudo cargar la imagen en MELI! Error: %s , Mensaje: %s, Status: %s') % ( rjson["error"], rjson["message"],rjson["status"],))
                    #return { 'status': 'error', 'message': 'not uploaded'}
                else:
                    image_ids+= [ { 'id': rjson['id'] }]
                    c = c + 1
                    _logger.info( "image_ids:" + str(image_ids) )

        product.write( { "meli_multi_imagen_id": "%s" % (image_ids) } )

        return image_ids


    def product_on_change_meli_banner(self, banner_id ):

        banner_obj = self.env['mercadolibre.banner']

        #solo para saber si ya habia una descripcion completada
        product_obj = self.env['product.product']
        product = self
        #if len(ids):
        #    product = self
        #else:
        #    product = product_obj.browse(ids)

        banner = banner_obj.browse( banner_id )

        #banner.description
        _logger.info( banner.description )
        result = ""
        if (banner.description!="" and banner.description!=False and product.meli_imagen_link!=""):
            imgtag = "<img style='width: 420px; height: auto;' src='%s'/>" % ( product.meli_imagen_link )
            result = banner.description.replace( "[IMAGEN_PRODUCTO]", imgtag )
            if (result):
                _logger.info( "result: %s" % (result) )
            else:
                result = banner.description

        return { 'value': { 'meli_description' : result } }


    @api.one
    def product_get_meli_update( self ):
        #self.ensure_one()
        #pdb.set_trace()
        company = self.env.user.company_id
        warningobj = self.env['warning']

        product_obj = self.env['product.product']
        product = self

        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token

        ML_status = "unknown"
        ML_permalink = ""
        ML_state = False

        if (ACCESS_TOKEN=='' or ACCESS_TOKEN==False):
            ML_status = "unknown"
            ML_permalink = ""
            ML_state = True
        else:
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)
            if product.meli_id:
                response = meli.get("/items/"+product.meli_id, {'access_token':meli.access_token} )
                rjson = response.json()
                if "status" in rjson:
                    ML_status = rjson["status"]
                if "permalink" in rjson:
                    ML_permalink = rjson["permalink"]
                if "error" in rjson:
                    ML_status = rjson["error"]
                    ML_permalink = ""
                if "sub_status" in rjson:
                    if len(rjson["sub_status"]) and rjson["sub_status"][0]=='deleted':
                        product.write({ 'meli_id': '' })

                self.meli_status = ML_status
                self.meli_permalink = ML_permalink


        self.meli_state = ML_state


    def product_post(self):
        #import pdb;pdb.set_trace();
        _logger.debug('[DEBUG] product_post')

        product_obj = self.env['product.product']
        product_tpl_obj = self.env['product.template']
        product = self
        product_tmpl = self.product_tmpl_id
        company = self.env.user.company_id
        warningobj = self.env['warning']

        REDIRECT_URI = company.mercadolibre_redirect_uri
        CLIENT_ID = company.mercadolibre_client_id
        CLIENT_SECRET = company.mercadolibre_secret_key
        ACCESS_TOKEN = company.mercadolibre_access_token
        REFRESH_TOKEN = company.mercadolibre_refresh_token


        meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET, access_token=ACCESS_TOKEN, refresh_token=REFRESH_TOKEN)

        if ACCESS_TOKEN=='':
            meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
            url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
            return {
                "type": "ir.actions.act_url",
                "url": url_login_meli,
                "target": "new",
            }

        if (product.meli_id):
            response = meli.get("/items/%s" % product.meli_id, {'access_token':meli.access_token})


        #check from company's default
        if company.mercadolibre_listing_type and product_tmpl.meli_listing_type==False:
            product_tmpl.meli_listing_type = company.mercadolibre_listing_type

        if company.mercadolibre_buying_mode and product_tmpl.meli_buying_mode==False:
            product_tmpl.meli_buying_mode = company.mercadolibre_buying_mode

        if company.mercadolibre_currency and product_tmpl.meli_currency==False:
            product_tmpl.meli_currency = company.mercadolibre_currency

        if company.mercadolibre_condition and product_tmpl.meli_condition==False:
            product_tmpl.meli_condition = company.mercadolibre_condition

        if company.mercadolibre_warranty and product_tmpl.meli_warranty==False:
            product_tmpl.meli_warranty = company.mercadolibre_warranty


        # _logger.info( product.meli_category.meli_category_id )

        if product_tmpl.meli_title==False:
            product_tmpl.meli_title = product_tmpl.name

        if company.mercadolibre_pricelist:
            pl = company.mercadolibre_pricelist
            return_val = pl.price_get(product.id,1.0)
            product_tmpl.meli_price = return_val[pl.id]

        if product_tmpl.meli_price==False or product_tmpl.meli_price==0:
            product_tmpl.meli_price = product_tmpl.standard_price

        if product_tmpl.meli_description==False or len(product_tmpl.meli_description)==0:
            product_tmpl.meli_description = product_tmpl.description_sale


        if product.meli_title==False or len(product.meli_title)==0:
            # _logger.info( 'Assigning title: product.meli_title: %s name: %s' % (product.meli_title, product.name) )
            product.meli_title = product_tmpl.meli_title

        if product.meli_price==False or product.meli_price==0.0:
            # _logger.info( 'Assigning price: product.meli_price: %s standard_price: %s' % (product.meli_price, product.standard_price) )

            if product_tmpl.meli_price:
                _logger.info("Assign tmpl price:"+str(product_tmpl.meli_price))
                product.meli_price = product_tmpl.meli_price

        if product.meli_description==False:
            product.meli_description = product_tmpl.meli_description



        if product.meli_category==False:
            product.meli_category=product_tmpl.meli_category
        if product.meli_listing_type==False:
            product.meli_listing_type=product_tmpl.meli_listing_type
        if product.meli_buying_mode==False:
            product.meli_buying_mode=product_tmpl.meli_buying_mode
        if product.meli_price==False:
            product.meli_price=product_tmpl.meli_price
        if product.meli_currency==False:
            product.meli_currency=product_tmpl.meli_currency
        if product.meli_condition==False:
            product.meli_condition=product_tmpl.meli_condition
        if product.meli_warranty==False:
            product.meli_warranty=product_tmpl.meli_warranty

        attributes = []
        if product_tmpl.attribute_line_ids:
            _logger.info(product_tmpl.attribute_line_ids)
            for at_line_id in product_tmpl.attribute_line_ids:
                atid = at_line_id.attribute_id.name
                atval = at_line_id.value_ids.name
                _logger.info(atid+":"+atval)
                if (atid=="MARCA" or atid=="BRAND"):
                    attribute = { "id": "BRAND", "value_name": atval }
                    attributes.append(attribute)
                if (atid=="MODELO" or atid=="MODEL"):
                    attribute = { "id": "MODEL", "value_name": atval }
                    attributes.append(attribute)

            _logger.info(attributes)
            product.meli_attributes = str(attributes);


        if product.public_categ_ids:
            for cat_id in product.public_categ_ids:
                _logger.info(cat_id)
                if (cat_id.mercadolibre_category):
                    _logger.info(cat_id.mercadolibre_category)
                    product.meli_category = cat_id.mercadolibre_category



        if (product.virtual_available):
            product.meli_available_quantity = product.virtual_available


        body = {
            "title": product.meli_title or '',
            "category_id": product.meli_category.meli_category_id or '0',
            "listing_type_id": product.meli_listing_type or '0',
            "buying_mode": product.meli_buying_mode or '',
            "price": product.meli_price  or '0',
            "currency_id": product.meli_currency  or '0',
            "condition": product.meli_condition  or '',
            "available_quantity": product.meli_available_quantity  or '0',
            "warranty": product.meli_warranty or '',
            #"pictures": [ { 'source': product.meli_imagen_logo} ] ,
            "video_id": product.meli_video  or '',
        }

        bodydescription = {
            "plain_text": product.meli_description or '',
        }

        # _logger.info( body )

        assign_img = False and product.meli_id

        #publicando imagen cargada en OpenERP
        if product.image==None:
            return warningobj.info( title='MELI WARNING', message="Debe cargar una imagen de base en el producto.", message_html="" )
        elif product.meli_imagen_id==False:
            # _logger.info( "try uploading image..." )
            resim = product.product_meli_upload_image()
            if "status" in resim:
                if (resim["status"]=="error" or resim["status"]=="warning"):
                    error_msg = 'MELI: mensaje de error:   ', resim
                    _logger.error(error_msg)
                else:
                    assign_img = True and product.meli_imagen_id

        #modificando datos si ya existe el producto en MLA
        if (product.meli_id):
            body = {
                "title": product.meli_title or '',
                #"description": { 'plain_text': product.meli_description or '' },
                #"category_id": product.meli_category.meli_category_id,
                #"listing_type_id": product.meli_listing_type,
                "buying_mode": product.meli_buying_mode or '',
                "price": product.meli_price or '0',
                #"currency_id": product.meli_currency,
                "condition": product.meli_condition or '',
                "available_quantity": product.meli_available_quantity or '0',
                "warranty": product.meli_warranty or '',
                "pictures": [],
                #"pictures": [ { 'source': product.meli_imagen_logo} ] ,
                "video_id": product.meli_video or '',
            }

            #resdescription = meli.get("/items/"+product.meli_id+"/description", {'access_token':meli.access_token})
            #_logger.info("res description:",resdescription)
            #rjsondes = resdescription.json()
        else:
            body["description"] = bodydescription


        #publicando multiples imagenes
        multi_images_ids = {}
        if (product.product_image_ids):
            # _logger.info( 'website_multi_images presente:   ', product.images )
            #recorrer las imagenes y publicarlas
            multi_images_ids = product.product_meli_upload_multi_images()

        #asignando imagen de logo (por source)
        #if product.meli_imagen_logo:
        if product.meli_imagen_id:
            if 'pictures' in body.keys():
                body["pictures"]+= [ { 'id': product.meli_imagen_id } ]
            else:
                body["pictures"] = [ { 'id': product.meli_imagen_id } ]

            if (multi_images_ids):
                if 'pictures' in body.keys():
                    body["pictures"]+= multi_images_ids
                else:
                    body["pictures"] = multi_images_ids

            if product.meli_imagen_logo:
                if 'pictures' in body.keys():
                    body["pictures"]+= [ { 'source': product.meli_imagen_logo} ]
                else:
                    body["pictures"] = [ { 'source': product.meli_imagen_logo} ]
        else:
            imagen_producto = ""
            #if (product.meli_description!="" and product.meli_description!=False and product.meli_imagen_link!=""):
            #    imgtag = "<img style='width: 420px; height: auto;' src='%s'/>" % ( product.meli_imagen_link )
            #    result = product.meli_description.replace( "[IMAGEN_PRODUCTO]", imgtag )
            #    if (result):
            #        _logger.info( "result: %s" % (result) )
            #        product.meli_description = result
            #    else:
            #        result = product.meli_description

        if len(attributes):
            body["attributes"] =  attributes


        #else:
        #    return warningobj.info(title='MELI WARNING', message="Debe completar el campo 'Imagen_Logo' con un url", message_html="")

        #check fields
        if product.meli_description==False:
            return warningobj.info(title='MELI WARNING', message="Debe completar el campo 'description' (en html)", message_html="")

        #put for editing, post for creating
        #_logger.info(body)
        #_logger.info(bodydescription)

        if product.meli_id:
            _logger.info(body)
            response = meli.put("/items/"+product.meli_id, body, {'access_token':meli.access_token})
            resdescription = meli.put("/items/"+product.meli_id+"/description", bodydescription, {'access_token':meli.access_token})
            rjsondes = resdescription.json()
            #_logger.info(resdescription)
        else:
            assign_img = True and product.meli_imagen_id
            response = meli.post("/items", body, {'access_token':meli.access_token})

        #check response
        # _logger.info( response.content )
        rjson = response.json()
        _logger.info(rjson)


        #check error
        if "error" in rjson:
            #_logger.info( "Error received: %s " % rjson["error"] )
            error_msg = 'MELI: mensaje de error:  %s , mensaje: %s, status: %s, cause: %s ' % (rjson["error"], rjson["message"], rjson["status"], rjson["cause"])
            _logger.error(error_msg)

            missing_fields = error_msg

            #expired token
            if "message" in rjson and (rjson["message"]=='invalid_token' or rjson["message"]=="expired_token"):
                meli = Meli(client_id=CLIENT_ID,client_secret=CLIENT_SECRET)
                url_login_meli = meli.auth_url(redirect_URI=REDIRECT_URI)
                #_logger.info( "url_login_meli:", url_login_meli )
                #raise osv.except_osv( _('MELI WARNING'), _('INVALID TOKEN or EXPIRED TOKEN (must login, go to Edit Company and login):  error: %s, message: %s, status: %s') % ( rjson["error"], rjson["message"],rjson["status"],))
                return warningobj.info( title='MELI WARNING', message="Debe iniciar sesión en MELI.  ", message_html="")
            else:
                 #Any other errors
                return warningobj.info( title='MELI WARNING', message="Completar todos los campos!  ", message_html="<br><br>"+missing_fields )

        #last modifications if response is OK
        if "id" in rjson:
            product.write( { 'meli_id': rjson["id"]} )

        posting_fields = {'posting_date': str(datetime.now()),'meli_id':rjson['id'],'product_id':product.id,'name': 'Post: ' + product.meli_title }

        posting_id = self.env['mercadolibre.posting'].search( [('meli_id','=',rjson['id'])]).id

        if not posting_id:
            posting_id = self.env['mercadolibre.posting'].create((posting_fields)).id


        return {}

    #typical values
    meli_title = fields.Char(string='Nombre del producto en Mercado Libre',size=256)
    meli_description = fields.Text(string='Descripción')
    meli_category = fields.Many2one("mercadolibre.category","Categoría de MercadoLibre")
    meli_price = fields.Char(string='Precio de venta', size=128)
    meli_dimensions = fields.Char( string="Dimensiones del producto", size=128)
    meli_pub = fields.Boolean('Meli Publication',help='MELI Product')

    meli_buying_mode = fields.Selection( [("buy_it_now","Compre ahora"),("classified","Clasificado")], string='Método de compra')
    meli_currency = fields.Selection([("ARS","Peso Argentino (ARS)"),
    ("MXN","Peso Mexicano (MXN)"),
    ("COP","Peso Colombiano (COP)")],string='Moneda')
    meli_condition = fields.Selection([ ("new", "Nuevo"), ("used", "Usado"), ("not_specified","No especificado")],'Condición del producto')
    meli_warranty = fields.Char(string='Garantía', size=256)
    meli_listing_type = fields.Selection([("free","Libre"),("bronze","Bronce"),("silver","Plata"),("gold","Oro"),("gold_premium","Gold Premium"),("gold_special","Gold Special/Clásica"),("gold_pro","Oro Pro")], string='Tipo de lista')


    #post only fields
    meli_post_required = fields.Boolean(string='Este producto es publicable en Mercado Libre')
    meli_id = fields.Char( string='Id del item asignado por Meli', size=256)
    meli_description_banner_id = fields.Many2one("mercadolibre.banner","Banner")
    meli_buying_mode = fields.Selection( [("buy_it_now","Compre ahora"),("classified","Clasificado")], string='Método de compra')
    meli_price = fields.Char(string='Precio de venta', size=128)
    meli_price_fixed = fields.Boolean(string='Price is fixed')
    meli_available_quantity = fields.Integer(string='Cantidad disponible')
    meli_imagen_logo = fields.Char(string='Imagen Logo', size=256)
    meli_imagen_id = fields.Char(string='Imagen Id', size=256)
    meli_imagen_link = fields.Char(string='Imagen Link', size=256)
    meli_multi_imagen_id = fields.Char(string='Multi Imagen Ids', size=512)
    meli_video = fields.Char( string='Video (id de youtube)', size=256)

    meli_permalink = fields.Char( compute=product_get_meli_update, size=256, string='PermaLink in MercadoLibre', store=False )
    meli_state = fields.Boolean( compute=product_get_meli_update, string="Inicio de sesión requerida", store=False )
    meli_status = fields.Char( compute=product_get_meli_update, size=128, string="Estado del producto en ML", store=False )

    meli_attributes = fields.Text(string='Atributos')

	### Agregar imagen/archivo uno o mas, y la descripcion en HTML...
	# TODO Agregar el banner

    _defaults = {
        'meli_imagen_logo': 'None',
        'meli_video': ''
    }



product_product()
