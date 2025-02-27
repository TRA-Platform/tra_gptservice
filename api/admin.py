from django.contrib import admin
from .models import ApiKey, Request


class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ['key', 'active', 'usage']
    list_filter = ['active']
    search_fields = ['key']


class RequestAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'key',
        'short_request',
        'short_answer',
        'engine',
        'is_completed',
        'is_failed',
        'is_json',
        'asynchronous',
        'formatted_created_at',
        'formatted_generation_started_at',
        'formatted_generation_completed_at',
    ]
    list_filter = ['timestamp', 'key', 'engine']
    search_fields = ['request', 'engine', 'temperature', 'key']
    fieldsets = (
        (None, {'fields': (
            'id',
            'key',
            'request',
            'engine',
            'answer',
            'is_json',
            'asynchronous',
            'created_at_ms',
        )}),
        ('Advanced Data', {
            'classes': ('collapse',),
            'fields': (
                'prompt_tokens',
                'total_tokens',
                'completion_tokens',
                'celery_subtask_id',
                'generation_started_at_ms',
                'generation_completed_at_ms',
            ),
        }),
        ('Status', {'fields': (
            'is_processing',
            'is_cancelled',
            'is_completed',
            'is_failed',
        )}),
        ('Extra Options', {'fields': (
            'temperature',
            'max_tokens',
            'top_p',
            'frequency_penalty',
            'presence_penalty',
        )}),
    )
    readonly_fields = (
        'id',
        'celery_subtask_id',
        'created_at_ms',
        'generation_started_at_ms',
        'generation_completed_at_ms',
        'is_processing',
        'is_cancelled',
        'is_completed',
        'is_failed',
        'is_json',
        'answer',
        'request',
        'asynchronous',
        'key',
        'prompt_tokens',
        'total_tokens',
        'completion_tokens',
        'engine',
        'temperature',
        'max_tokens',
        'top_p',
        'frequency_penalty',
        'presence_penalty',
    )

    actions = ['cancel', 'resolve']

    def short_request(self, obj):
        return obj.short_request

    def formatted_created_at(self, obj):
        return self.format_datetime_with_ms(obj.created_at)

    formatted_created_at.short_description = 'Created At (ms)'

    def formatted_generation_started_at(self, obj):
        return self.format_datetime_with_ms(obj.generation_started_at)

    formatted_generation_started_at.short_description = 'Generation Started At (ms)'

    def formatted_generation_completed_at(self, obj):
        return self.format_datetime_with_ms(obj.generation_completed_at)

    formatted_generation_completed_at.short_description = 'Generation Completed At (ms)'

    def format_datetime_with_ms(self, dt):
        if dt:
            return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        return ''

    def cancel(self, request, queryset):
        for obj in queryset:
            obj.cancel()

    def resolve(self, request, queryset):
        for obj in queryset:
            obj.resolve()


admin.site.register(ApiKey, ApiKeyAdmin)
admin.site.register(Request, RequestAdmin)
