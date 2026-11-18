from django.contrib import admin
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.urls import path

from pharmacy.assistant.service import answer_question
from pharmacy.assistant.validate import SqlRejected
from pharmacy.models import (
    Branch, Invoice, InvoiceItem, Product, Seller, Supervisor,
)


@admin.register(Supervisor)
class SupervisorAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'branch_count')
    search_fields = ('name', 'email')

    @admin.display(description='Branches')
    def branch_count(self, obj):
        return obj.branches.count()


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'supervisor', 'phone', 'seller_count')
    list_filter = ('supervisor',)
    search_fields = ('name', 'address')

    @admin.display(description='Sellers')
    def seller_count(self, obj):
        return obj.sellers.count()


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'phone')
    list_filter = ('branch',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'barcode', 'price', 'stock', 'expiry_date')
    list_filter = ('expiry_date',)
    search_fields = ('name', 'barcode')


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'branch', 'seller', 'created_at', 'total')
    list_filter = ('branch', 'seller')
    search_fields = ('number',)
    readonly_fields = ('created_at',)
    inlines = (InvoiceItemInline,)


def assistant_view(request):
    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        try:
            result = answer_question(question)
        except (SqlRejected, ValueError) as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        except Exception as exc:
            return JsonResponse(
                {'error': f'Could not answer: {exc}'}, status=502,
            )
        return JsonResponse({
            'summary': result['summary'],
            'sql': result['sql'],
            'columns': result['columns'],
            'rows': [[str(cell) for cell in row] for row in result['rows']],
            'truncated': result['truncated'],
        })
    context = {
        **admin.site.each_context(request),
        'title': 'Data assistant',
    }
    return TemplateResponse(request, 'admin/pharmacy/assistant.html', context)


_default_get_urls = admin.site.get_urls


def _get_urls_with_assistant():
    custom = [
        path(
            'pharmacy/assistant/',
            admin.site.admin_view(assistant_view),
            name='pharmacy_assistant',
        ),
    ]
    return custom + _default_get_urls()


admin.site.get_urls = _get_urls_with_assistant
