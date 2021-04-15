# Copyright 2021 Tecnativa - Jairo Llopis
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _sync_resource_bookings(self):
        """On eCommerce, a draft SO produces pending/scheduled bookings."""
        result = super()._sync_resource_bookings()
        # Do not alter backend behavior
        for line in self.with_context(active_test=False):
            order = line.order_id
            # We only care about eCommerce orders
            if not order.website_id:
                continue
            bookings = line.resource_booking_ids
            # If paid, create missing partners
            if order.state == "sale":
                bookings._confirm_prereservation()
                continue
            # If it is still a cart, create pending bookings
            if order.state != "draft":
                continue
            values = {
                "sale_order_line_id": line.id,
                "type_id": line.product_id.resource_booking_type_id.id,
            }
            context = {
                "default_partner_id": line.order_id.partner_id.id,
                "default_combination_id":
                    line.product_id
                    .resource_booking_type_combination_rel_id.combination_id.id,
            }
            # Assign prereservation data if user is logged in
            prereserved_partner = order.partner_id - order.website_id.user_id.partner_id
            if prereserved_partner:
                context.update(
                    {
                        "default_prereserved_name": prereserved_partner.name,
                        "default_prereserved_email": prereserved_partner.email,
                    }
                )
            # Add/remove bookings if needed
            self.env["resource.booking"]._cron_cancel_expired(
                [("id", "in", bookings.ids)]
            )
            expected_amount = int(line.product_uom_qty) if values["type_id"] else 0
            self.with_context(**context)._add_or_cancel_bookings(
                bookings, expected_amount, values
            )
        return result
