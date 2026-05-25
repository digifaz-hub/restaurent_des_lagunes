# -*- coding: utf-8 -*-

from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, vals_list):
        """
        Désactiver automatiquement la TVA pour les produits de cantine
        (régime micro-entreprise)
        """
        res = super(ProductTemplate, self).create(vals_list)

        # Vérifier si c'est un produit créé via lagunes.plat
        for product in res:
            # Retirer toutes les taxes
            if product.categ_id and 'Cantine' in product.categ_id.complete_name:
                product.taxes_id = [(5, 0, 0)]
                product.supplier_taxes_id = [(5, 0, 0)]

        # Auto-tag boissons
        self._sync_boisson_tag(res)

        return res

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if 'categ_id' in vals:
            self._sync_boisson_tag(self)
        return res

    def _sync_boisson_tag(self, records):
        """Auto-tag les produits de la catégorie Boissons avec le tag 'Boisson'."""
        tag_boisson = self.env.ref('lagunes_cantine.product_tag_boisson', raise_if_not_found=False)
        if not tag_boisson:
            return
        for product in records:
            categ = product.categ_id
            if categ and categ.name and 'Boisson' in categ.name:
                if tag_boisson not in product.product_tag_ids:
                    product.product_tag_ids = [(4, tag_boisson.id)]
            else:
                # Retirer le tag si le produit n'est plus dans la catégorie Boissons
                if tag_boisson in product.product_tag_ids:
                    product.product_tag_ids = [(3, tag_boisson.id)]
