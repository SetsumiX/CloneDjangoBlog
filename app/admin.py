from django.contrib import admin
from .models import Post, Product, Category, ProductImage
from PIL import Image

# Register your models here.
admin.site.register(Post)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "description"]
    search_fields = ["name"]

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'image', 'is_primary', 'order']
    list_filter = ['product', 'is_primary']
    search_fields = ['product__name']

class ProductImageInline(admin.TabularInline): # Или StackedInline для более подробного отображения
    model = ProductImage
    extra = 1 # Количество пустых форм для добавления новых изображений
    fields = ('image', 'is_primary', 'order')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'description']
    inlines = [ProductImageInline]