# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import date, timedelta
from odoo.exceptions import UserError

class LagunesTraiteurDemande(models.Model):
    _name = 'lagunes.traiteur.demande'
    _description = 'Demande de Prestation Traiteur'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_demande desc, id desc'
    _check_company_auto = True

    reference = fields.Char(string='Référence', readonly=True, copy=False, default=lambda self: _('Nouveau'))
    date_demande = fields.Date(string='Date de la demande', default=fields.Date.context_today, required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    
    # — Informations client —
    nom_contact = fields.Char(string='Nom du contact', required=True, tracking=True)
    prenom_contact = fields.Char(string='Prénom du contact', tracking=True)
    email_contact = fields.Char(string='Email', required=True, tracking=True)
    telephone_contact = fields.Char(string='Téléphone', required=True, tracking=True)
    nom_entreprise = fields.Char(string='Entreprise / Organisation', tracking=True)
    adresse_prestation = fields.Text(string='Lieu de la prestation', tracking=True)
    
    # — Prestation —
    date_debut = fields.Date(string='Date de début', required=True, tracking=True)
    date_fin = fields.Date(string='Date de fin', required=True, tracking=True)
    nb_jours = fields.Integer(string='Nombre de jours', compute='_compute_nb_jours', store=True)
    nb_personnes = fields.Integer(string='Nombre de personnes', default=1, tracking=True)
    type_prestation_ids = fields.Many2many(
        'lagunes.traiteur.type.prestation',
        string='Types de prestation',
        help='Types d’événements sélectionnés par le client',
    )
    niveau_id = fields.Many2one(
        'lagunes.traiteur.niveau',
        string='Formule sélectionnée',
        help='Niveau/Formule sélectionné par le client sur le portail web',
    )
    
    # — Champs de synthèse (Dashboard/Stats) —
    main_type_prestation_id = fields.Many2one('lagunes.traiteur.type.prestation', string='Type principal', compute='_compute_summary', store=True)
    total_nb_personnes = fields.Integer(string='Total personnes', compute='_compute_summary', store=True)


    
    @api.onchange('date_debut', 'date_fin')
    def _onchange_dates(self):
        """Génère automatiquement les lignes de jours quand les dates changent"""
        if self.date_debut and self.date_fin:
            if self.date_debut > self.date_fin:
                return {'warning': {'title': _('Erreur de date'), 'message': _('La date de début doit être antérieure à la date de fin.')}}
            
            # Préparer les nouveaux jours
            new_days = []
            current_date = self.date_debut
            while current_date <= self.date_fin:
                # Vérifier si ce jour existe déjà pour ne pas le recréer (si on change juste une date)
                existing = self.jour_ids.filtered(lambda j: j.date == current_date)
                if not existing:
                    new_days.append((0, 0, {'date': current_date}))
                else:
                    new_days.append((4, existing[0].id))
                current_date += timedelta(days=1)
            
            self.jour_ids = new_days
    
    # — Menus —
    jour_ids = fields.One2many('lagunes.traiteur.demande.jour', 'demande_id', string='Jours de prestation')
    
    # — Logistique —
    logistique_line_ids = fields.One2many('lagunes.traiteur.logistique.line', 'demande_id', string='Options logistiques')
    
    # — Notes —
    notes_client = fields.Text(string='Commentaires client')
    notes_internes = fields.Text(string='Notes internes (privées)', tracking=True)
    
    # — Financier —
    montant_estime = fields.Monetary(string='Total Prestations', compute='_compute_montants', currency_field='currency_id', store=True)
    montant_logistique = fields.Monetary(string='Total Options Logistiques', compute='_compute_montants', currency_field='currency_id', store=True)
    montant_total_estime = fields.Monetary(string='Montant Total Devis HT', compute='_compute_montants', currency_field='currency_id', store=True)

    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    
    # — Workflow —
    state = fields.Selection([
        ('new', 'Nouveau'),
        ('en_cours', 'En cours'),
        ('devis_cree', 'Devis créé'),
        ('devis_envoye', 'Devis envoyé'),
        ('accepte', 'Accepté'),
        ('refuse', 'Refusé'),
        ('annule', 'Annulé')
    ], string='Statut', default='new', required=True, tracking=True)
    
    # — Workflow Devis Historique (Modèle B) —
    devis_ids = fields.One2many('lagunes.traiteur.devis', 'demande_id', string='Tous les devis', readonly=True)
    active_devis_id = fields.Many2one('lagunes.traiteur.devis', string='Devis actif', readonly=True, 
                                       help='Devis actuellement actif pour cette demande')
    


    # Gardé pour compatibilité, redirige vers active_devis_id
    devis_id = fields.Many2one('lagunes.traiteur.devis', related='active_devis_id', string='Devis Traiteur', readonly=True)
    user_id = fields.Many2one('res.users', string='Commercial assigné', tracking=True)
    sale_order_id = fields.Many2one('sale.order', string='Bon de commande', readonly=True)

    # — Propositions de menu —
    proposition_ids = fields.One2many(
        'lagunes.traiteur.proposition', 'demande_id',
        string='Propositions de menu',
    )
    proposition_count = fields.Integer(
        string='Nb propositions',
        compute='_compute_proposition_count',
    )

    @api.depends('proposition_ids')
    def _compute_proposition_count(self):
        for rec in self:
            rec.proposition_count = len(rec.proposition_ids)

    def action_open_menu_proposition(self):
        """Ouvre (ou crée) la proposition de menu liée à cette demande."""
        self.ensure_one()
        proposition = self.proposition_ids[:1]
        if not proposition:
            proposition = self.env['lagunes.traiteur.proposition'].create({
                'demande_id': self.id,
                'partner_email': self.email_contact,
                'nb_personnes': self.nb_personnes or 1,
            })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Proposition de menu'),
            'res_model': 'lagunes.traiteur.proposition',
            'view_mode': 'form',
            'res_id': proposition.id,
            'target': 'current',
        }

    def action_view_propositions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Propositions de menu'),
            'res_model': 'lagunes.traiteur.proposition',
            'view_mode': 'list,form',
            'domain': [('demande_id', '=', self.id)],
            'context': {'default_demande_id': self.id, 'default_partner_email': self.email_contact},
        }
    
    # — Facturation —
    invoice_status = fields.Selection(related='sale_order_id.invoice_status', string='Statut Facturation')
    invoice_count = fields.Integer(string='Factures', compute='_compute_invoice_count')
    amount_invoiced = fields.Monetary(string='Montant Facturé', related='sale_order_id.amount_invoiced', currency_field='currency_id')
    is_overdue_invoicing = fields.Boolean(string='Retard de facturation', compute='_compute_is_overdue_invoicing', store=True)


    
    # — État des stocks Marché (Prévisionnel) —
    stock_status = fields.Selection([
        ('draft', 'Non vérifié'),
        ('available', 'Stock disponible'),
        ('partial', 'Stock partiel'),
        ('missing', 'En rupture'),
    ], string='Disponibilité Stock', default='draft', tracking=True)
    
    reservation_details = fields.Text(string='Détails des besoins stock', readonly=True)
    
    is_stock_deducted = fields.Boolean(string='Stock déduit', default=False, copy=False, readonly=True)
    
    # — Champs de rafraîchissement dynamique —
    stock_availability_info = fields.Char(string='Disponibilité Stock (Réel)', compute='_compute_stock_availability')
    stock_availability_color = fields.Selection([
        ('success', 'Disponible'),
        ('warning', 'Partiel'),
        ('danger', 'Manquant'),
    ], string='Couleur Stock', compute='_compute_stock_availability')

    @api.depends('jour_ids.prestation_ids.plat_line_ids.plat_id', 'jour_ids.prestation_ids.plat_line_ids.quantite')
    def _compute_stock_availability(self):
        for rec in self:
            missing_count = 0
            total_items = 0
            for jour in rec.jour_ids:
                for prestation in jour.prestation_ids:
                    for plat_line in prestation.plat_line_ids:
                        if plat_line.plat_id and hasattr(plat_line.plat_id, 'ingredient_ids'):
                            total_items += 1
                            for ing in plat_line.plat_id.ingredient_ids:
                                if not ing.is_quantifiable:
                                    continue
                                needed = ing.quantity * plat_line.quantite
                                stock = self.env['lagunes.market.stock'].search([
                                    ('article_id', '=', ing.market_article_id.id),
                                    ('company_id', '=', rec.company_id.id)
                                ], limit=1)
                                if (stock.qty if stock else 0) < needed:
                                    missing_count += 1
                                    break  # Ce plat pose problème, pas besoin de vérifier les autres ingrédients
            
            if total_items == 0:
                rec.stock_availability_info = _("Aucun plat défini")
                rec.stock_availability_color = 'success'
            elif missing_count == 0:
                rec.stock_availability_info = _("Tout est en stock")
                rec.stock_availability_color = 'success'
            elif missing_count < total_items:
                rec.stock_availability_info = _("Certains ingrédients manquent")
                rec.stock_availability_color = 'warning'
            else:
                rec.stock_availability_info = _("Rupture de stock détectée")
                rec.stock_availability_color = 'danger'

    @api.onchange('jour_ids', 'jour_ids.prestation_ids', 'jour_ids.prestation_ids.plat_line_ids')
    def _onchange_lines_stock_check(self):
        """Déclenche une notification si le stock devient insuffisant lors de la saisie."""
        self._compute_stock_availability()
        if self.stock_availability_color in ('warning', 'danger'):
            return {
                'warning': {
                    'title': _('Alerte Stock'),
                    'message': self.stock_availability_info + _(". Veuillez vérifier les détails dans l'onglet Stock.")
                }
            }

    @api.depends('date_debut', 'date_fin')
    def _compute_nb_jours(self):
        for rec in self:
            if rec.date_debut and rec.date_fin:
                delta = (rec.date_fin - rec.date_debut).days + 1
                rec.nb_jours = max(1, delta)
            else:
                rec.nb_jours = 1

    @api.depends('sale_order_id.invoice_count')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = rec.sale_order_id.invoice_count if rec.sale_order_id else 0

    def action_view_invoices(self):
        self.ensure_one()
        if not self.sale_order_id:
            return
        return self.sale_order_id.action_view_invoice()

    @api.depends('state', 'date_fin', 'invoice_status')
    def _compute_is_overdue_invoicing(self):
        today = fields.Date.today()
        for rec in self:
            # En retard si accepté, fini depuis hier, et pas encore totalement facturé
            rec.is_overdue_invoicing = (
                rec.state == 'accepte' and 
                rec.date_fin and rec.date_fin < today and 
                rec.invoice_status != 'invoiced'
            )

    def _cron_alert_overdue_invoicing(self):
        """Action planifiée pour alerter les commerciaux des factures en retard"""
        overdue = self.search([('is_overdue_invoicing', '=', True), ('user_id', '!=', False)])
        for rec in overdue:
            # Créer une activité si elle n'existe pas déjà
            existing = self.env['mail.activity'].search([
                ('res_id', '=', rec.id),
                ('res_model_id', '=', self.env.ref('lagunes_traiteur.model_lagunes_traiteur_demande').id),
                ('activity_type_id', '=', self.env.ref('mail.mail_activity_data_todo').id),
                ('summary', '=', _("Retard de facturation"))
            ])
            if not existing:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_("Retard de facturation"),
                    note=_("Cette prestation est terminée mais n'a pas encore été entièrement facturée."),
                    user_id=rec.user_id.id
                )


    @api.depends('jour_ids.prestation_ids.type_prestation_id', 'jour_ids.prestation_ids.nb_personnes', 'type_prestation_ids')

    def _compute_summary(self):
        for rec in self:
            all_prestas = rec.jour_ids.mapped('prestation_ids')
            if all_prestas:
                rec.main_type_prestation_id = all_prestas[0].type_prestation_id.id
                # On prend le max de personnes sur une prestation (plus représentatif que la somme si c'est le même groupe)
                rec.total_nb_personnes = max(all_prestas.mapped('nb_personnes'))
            elif rec.type_prestation_ids:
                rec.main_type_prestation_id = rec.type_prestation_ids[0].id
                rec.total_nb_personnes = 0
            else:
                rec.main_type_prestation_id = False
                rec.total_nb_personnes = 0


    @api.depends('jour_ids.prestation_ids.montant_total', 'logistique_line_ids.sous_total')
    def _compute_montants(self):
        for rec in self:
            total_prestations = sum(rec.jour_ids.mapped('prestation_ids').mapped('montant_total'))
            rec.montant_estime = total_prestations
            total_log = sum(rec.logistique_line_ids.mapped('sous_total'))
            rec.montant_logistique = total_log
            rec.montant_total_estime = total_prestations + total_log


    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.reference == _('Nouveau'):
                record.reference = self.env['ir.sequence'].next_by_code('lagunes.traiteur.demande') or _('Nouveau')
        return records

    def action_send_whatsapp(self):
        """Ouvre un lien WhatsApp avec un message pré-rempli"""
        self.ensure_one()
        if not self.telephone_contact:
            raise UserError(_("Le numéro de téléphone du contact est manquant."))
        
        # Nettoyage du numéro
        phone = "".join(filter(str.isdigit, self.telephone_contact))
        if len(phone) == 10 and not phone.startswith('225'):
            phone = '225' + phone
            
        message = _("Bonjour %s, je suis le responsable Traiteur du Restaurant des Lagunes. "
                    "J'ai bien reçu votre demande %s et je reviens vers vous pour finaliser les détails.") % (
            self.prenom_contact or self.nom_contact, self.reference
        )
        
        # Encodage URL du message
        import urllib.parse
        message_encoded = urllib.parse.quote(message)
        
        url = f"https://wa.me/{phone}?text={message_encoded}"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }


    # Actions Workflow
    def action_view_sale_order(self):
        """Ouvre le bon de commande lié à cette demande"""
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError(_("Aucun bon de commande n'est lié à cette demande."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bon de Commande'),
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.sale_order_id.id,
            'target': 'current',
        }

    def action_assign_to_me(self):
        self.write({'user_id': self.env.user.id, 'state': 'en_cours'})

    def action_accept(self):
        """Accepte la demande - appelée par le devis (sens unique Devis→Demande)"""
        self.write({'state': 'accepte'})
        # Vérification automatique du stock lors de l'acceptation
        self.action_check_stock()

    def action_refuse(self):
        """Refuse la demande - appelée par le devis (sens unique Devis→Demande)"""
        self.write({'state': 'refuse'})

    def action_cancel(self):
        self.write({'state': 'annule'})

    def action_check_stock(self):
        """Vérifie la disponibilité des ingrédients et met à jour le statut sans bloquer."""
        self.ensure_one()
        missing_ingredients = []
        total_items = 0
        missing_count = 0
        
        details = []
        for jour in self.jour_ids:
            for prestation in jour.prestation_ids:
                for plat_line in prestation.plat_line_ids:
                    if plat_line.plat_id:
                        plat = plat_line.plat_id
                        if hasattr(plat, 'ingredient_ids'):
                            for ing in plat.ingredient_ids:
                                total_items += 1
                                needed_qty = ing.quantity * plat_line.quantite
                                
                                # Recherche dans le stock Marché
                                stock_item = self.env['lagunes.market.stock'].search([
                                    ('article_id', '=', ing.market_article_id.id),
                                    ('company_id', '=', self.company_id.id)
                                ], limit=1)
                                
                                available = stock_item.qty if stock_item else 0.0
                                if available < needed_qty:
                                    missing_count += 1
                                    missing_ingredients.append(
                                        f"- {ing.market_article_id.name} ({plat.name}) : Besoin {needed_qty} {ing.unit_id.name}, Dispo {available}"
                                    )
        
        # Mise à jour du statut
        if total_items == 0:
            self.stock_status = 'available'
        elif missing_count == 0:
            self.stock_status = 'available'
        elif missing_count < total_items:
            self.stock_status = 'partial'
        else:
            self.stock_status = 'missing'
            
        self.reservation_details = "\n".join(missing_ingredients) if missing_ingredients else _("Tout est en stock.")


        if missing_ingredients:
            msg = _("Certains ingrédients manquent. État mis à jour à '%s'.") % dict(self._fields['stock_status'].selection).get(self.stock_status)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Alerte Stock Partiel'),
                    'message': msg,
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Stock OK'),
                'message': _('Tous les ingrédients sont disponibles.'),
                'type': 'success',
            }
        }

    def action_post_consumption(self):
        """Déduit réellement les ingrédients du stock Marché pour cette prestation."""
        self.ensure_one()
        if self.is_stock_deducted:
            raise UserError(_("Le stock a déjà été déduit pour cette prestation."))
        
        # Guard : vérifier que le devis est accepté ET le sale.order confirmé
        if self.state != 'accepte':
            raise UserError(_("La demande doit être acceptée avant de déduire le stock."))
        if not self.sale_order_id or self.sale_order_id.state != 'sale':
            raise UserError(_("Le devis doit être confirmé par le client avant de déduire le stock."))
        
        moves_count = 0
        for jour in self.jour_ids:
            for prestation in jour.prestation_ids:
                for plat_line in prestation.plat_line_ids:
                    if plat_line.plat_id:
                        plat = plat_line.plat_id
                        if hasattr(plat, 'ingredient_ids'):
                            for ing in plat.ingredient_ids:
                                needed_qty = ing.quantity * plat_line.quantite
                                
                                # Note pour la traçabilité
                                note = _("Prestation Traiteur %s (%s) - %s") % (self.reference, self.nom_entreprise or self.nom_contact, plat.name)
                                
                                # Déduction sécurisée
                                self.env['lagunes.market.stock'].with_company(self.company_id)._remove_quantity(
                                    article_id=ing.market_article_id.id,
                                    qty=needed_qty,
                                    note=note,
                                    reference=self.reference,
                                    move_category='order_deduction',
                                    allow_capped=True,
                                    source='traiteur',
                                )
                                moves_count += 1

        
        self.is_stock_deducted = True
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Consommation validée'),
                'message': _('%s mouvements de stock ont été enregistrés au Marché.') % moves_count,
                'type': 'success',
            }
        }

    def action_create_devis(self):
        """Génère le devis traiteur et le sale.order Odoo associé"""
        self.ensure_one()
        
        # Guards workflow
        if self.state != 'en_cours':
            raise UserError(_("La demande doit être 'En cours' pour créer un devis."))
        if self.active_devis_id:
            raise UserError(_("Un devis actif existe déjà. Veuillez réviser ou annuler le devis existant."))
        if self.sale_order_id:
            raise UserError(_("Un bon de commande existe déjà pour cette demande."))
        
        # Guard : vérifier qu'il y a au moins une prestation
        prestations = self.jour_ids.mapped('prestation_ids')
        if not prestations:
            raise UserError(_("Aucune prestation définie pour cette demande. Veuillez d'abord créer les prestations pour chaque jour."))
        
        config = self.env['lagunes.traiteur.config'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not config or not config.produit_prestation_id:
            raise UserError(_("Veuillez configurer le produit générique de prestation dans les paramètres Traiteur."))

        # 1. Création du Sale Order Odoo
        # On cherche ou crée le partenaire (matching robuste: email + nom)
        partner_name = f"{self.prenom_contact} {self.nom_contact}".strip()
        partner = self.env['res.partner'].search([
            ('email', '=', self.email_contact),
            ('name', '=', partner_name)
        ], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': partner_name,
                'email': self.email_contact,
                'phone': self.telephone_contact,
                'company_type': 'person',
            })

        so_vals = {
            'partner_id': partner.id,
            'company_id': self.company_id.id,
            'origin': self.reference,
            'note': self.notes_client,
            'traiteur_demande_id': self.id,
        }
        sale_order = self.env['sale.order'].create(so_vals)

        # 2. Ajout des lignes de prestations
        nb_jours_global = (self.date_fin - self.date_debut).days + 1 if self.date_debut and self.date_fin else 1
        
        for jour in self.jour_ids:
            for prestation in jour.prestation_ids:
                # A. Titre de la prestation (Section)
                self.env['sale.order.line'].create({
                    'order_id': sale_order.id,
                    'display_type': 'line_section',
                    'name': f"{jour.jour_semaine} {jour.date} — {prestation.type_prestation_id.name} à %02dh%02d" % (int(prestation.heure_prestation), int(60 * (prestation.heure_prestation - int(prestation.heure_prestation)))),
                })

                # B. Ligne Forfaitaire de la Prestation (Ligne avec prix)
                self.env['sale.order.line'].create({
                    'order_id': sale_order.id,
                    'product_id': config.produit_prestation_id.id,
                    'name': f"{prestation.type_prestation_id.name} ({prestation.niveau_id.name})",
                    'product_uom_qty': prestation.nb_personnes,
                    'traiteur_nb_jours': prestation.nb_jours,
                    'price_unit': prestation.prix_unitaire * prestation.nb_jours,
                    'traiteur_prestation_id': prestation.id,
                })
                
                # C. Détails des plats (Lignes à 0 FCFA)
                for line in prestation.plat_line_ids:
                    if line.logistique_id: continue # Géré séparément
                    product = line.plat_id.product_id if line.plat_id else config.produit_prestation_id
                    self.env['sale.order.line'].create({
                        'order_id': sale_order.id,
                        'product_id': product.id,
                        'name': f"• {line.description}",
                        'product_uom_qty': line.quantite,
                        'price_unit': 0.0, # Inclus dans le forfait
                        'traiteur_prestation_id': prestation.id,
                    })

        # 3. Ajout des lignes logistiques (Options)
        if self.logistique_line_ids:
            self.env['sale.order.line'].create({
                'order_id': sale_order.id,
                'display_type': 'line_section',
                'name': _("Options Logistiques & Équipements"),
            })
            for line in self.logistique_line_ids:
                product = line.logistique_id.product_id or config.produit_prestation_id
                self.env['sale.order.line'].create({
                    'order_id': sale_order.id,
                    'product_id': product.id,
                    'name': line.description,
                    'product_uom_qty': line.quantite,
                    'traiteur_nb_jours': nb_jours_global,
                    'price_unit': line.prix_unitaire * nb_jours_global,
                })



        # 4. Création du devis Traiteur (Wrapper)
        devis = self.env['lagunes.traiteur.devis'].create({
            'demande_id': self.id,
            'sale_order_id': sale_order.id,
            'date_validite': date.today() + timedelta(days=config.delai_reponse_devis_jours or 7),
        })

        self.write({
            'sale_order_id': sale_order.id,
            'active_devis_id': devis.id,
            'state': 'devis_cree'
        })

        return {
            'name': _('Devis Généré'),
            'type': 'ir.actions.act_window',
            'res_model': 'lagunes.traiteur.devis',
            'view_mode': 'form',
            'res_id': devis.id,
        }
