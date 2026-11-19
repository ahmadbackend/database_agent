from django.apps import AppConfig


class PharmacyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pharmacy'

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from pharmacy import models
        from pharmacy.assistant.service import invalidate_assistant_cache

        def bump_data_version(raw=False, **kwargs):
            if not raw:
                invalidate_assistant_cache()

        watched = (
            models.Supervisor, models.Branch, models.Seller,
            models.Product, models.Invoice, models.InvoiceItem,
        )
        for model in watched:
            post_save.connect(bump_data_version, sender=model)
            post_delete.connect(bump_data_version, sender=model)
