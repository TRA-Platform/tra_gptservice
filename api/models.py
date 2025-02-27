import logging
import traceback

from django.db import models, transaction
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from api import utils
from gptService import celery

logger = logging.getLogger(__name__)


class ApiKey(models.Model):
    key = models.CharField(max_length=100, verbose_name="API Key")
    active = models.BooleanField(default=True, verbose_name="Active")
    usage = models.IntegerField(default=0, verbose_name="Usage")
    openai_api_key = models.CharField(default="sk-API...", max_length=100,
                                      verbose_name="OpenAI API Key")
    deepseek_api_key = models.CharField(default="sk-API...", max_length=100,
                                        verbose_name="Deepseek API Key")
    proxy_url = models.CharField(default="http://user:pass@ip:port", max_length=100,
                                 verbose_name="Proxy URL")

    def __str__(self):
        return self.key

    class Meta:
        verbose_name_plural = "Api Keys"


class Request(models.Model):
    key = models.ForeignKey(ApiKey, on_delete=models.CASCADE, verbose_name="API Key")
    request = models.TextField(verbose_name="Request")
    timestamp = models.DateTimeField(auto_now=True, verbose_name="Timestamp")
    engine = models.CharField(default=settings.OPENAI_ENGINE, max_length=30)
    temperature = models.FloatField(default=settings.OPENAI_TEMP, null=True, blank=True, verbose_name="Temperature")
    answer = models.TextField(verbose_name="Answer", default="", blank=True)
    max_tokens = models.IntegerField(default=settings.OPENAI_MAX_TOKENS, null=True, blank=True,
                                     verbose_name="Max Tokens")
    top_p = models.FloatField(default=settings.OPENAI_TOP_P, null=True, blank=True, verbose_name="Top P")
    frequency_penalty = models.FloatField(default=settings.OPENAI_FREQUENCY_PENALTY, null=True, blank=True,
                                          verbose_name="Frequency Penalty")
    presence_penalty = models.FloatField(default=settings.OPENAI_PRESENCE_PENALTY, null=True, blank=True,
                                         verbose_name="Presence Penalty")
    is_processing = models.BooleanField(default=False, verbose_name="Is Processing")
    is_cancelled = models.BooleanField(default=False, verbose_name="Is Cancelled")
    is_completed = models.BooleanField(default=False, verbose_name="Is Completed")
    is_failed = models.BooleanField(default=False, verbose_name="Is Failed")
    is_json = models.BooleanField(default=False, verbose_name="Is JSON")
    celery_subtask_id = models.CharField(max_length=100, verbose_name="Celery Subtask ID", default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False, verbose_name="Создано", null=True, blank=True)
    generation_started_at = models.DateTimeField(verbose_name="Начало генерации", null=True, blank=True)
    generation_completed_at = models.DateTimeField(verbose_name="Окончание генерации", null=True, blank=True)
    asynchronous = models.BooleanField(default=True, verbose_name="Асинхронно")
    prompt_tokens = models.IntegerField(default=0, verbose_name="Prompt Tokens")
    total_tokens = models.IntegerField(default=0, verbose_name="Total Tokens")
    completion_tokens = models.IntegerField(default=0, verbose_name="Completion Tokens")
    chat_completion = models.CharField(max_length=100, verbose_name="Chat Completion", default="", blank=True)

    def __str__(self):
        return f"Request {self.id}"

    def cancel(self):
        self.is_cancelled = True
        if self.celery_subtask_id:
            celery.app.control.revoke(self.celery_subtask_id, terminate=True)
        self.save()

    def delete(self, using=None, keep_parents=False):
        self.cancel()

    def resolve(self):
        with transaction.atomic():
            self.is_processing = True
            self.generation_started_at = timezone.now()
            self.save()
            logger.error(f"request: {self.id} processing started.")
        logger.error(f"request: {self.id} generation started.")
        generator = utils.resolve_gateway(self)
        try:
            request, response = generator.ask(
                prompt=self.request,
                engine=self.engine,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=self.top_p,
                frequency_penalty=self.frequency_penalty,
                presence_penalty=self.presence_penalty,
                is_json=self.is_json,
            )
        except Exception as e:
            traceback.print_exc()
            logger.error(f"request: {self.id} generation failed.")
            with transaction.atomic():
                self.is_failed = True
                self.is_processing = False
                self.generation_completed_at = timezone.now()
                self.save()
            return
        with transaction.atomic():
            self.answer = response.choices[0].message.content
            self.total_tokens = response.usage.total_tokens
            self.prompt_tokens = response.usage.prompt_tokens
            self.completion_tokens = response.usage.completion_tokens
            self.is_completed = True
            self.is_processing = False
            self.generation_completed_at = timezone.now()
            self.save()
            logger.error(f"request: {self.id} generation completed.")

    @property
    def short_request(self):
        return self.request[:100] + ('...' if len(self.request) > 100 else '')

    @property
    def short_answer(self):
        return self.answer[:100] + ('...' if len(self.answer) > 100 else '')

    class Meta:
        verbose_name_plural = "Requests"

    @property
    def created_at_ms(self):
        return self.created_at.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    @property
    def generation_started_at_ms(self):
        return self.generation_started_at.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    @property
    def generation_completed_at_ms(self):
        return self.generation_completed_at.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


@receiver(post_save, sender=Request)
def trigger_request_generation(sender, instance, created, **kwargs):
    from api import tasks
    logger.error(f"Trigger request [GENERAL]: {instance.id}")
    if created and instance.asynchronous:
        logger.error(f"Trigger request [CREATION]: {instance.id}")
        with transaction.atomic():
            task_id = tasks.request_resolve.delay(instance.id)
            logger.error(f"Task ID {instance.id}: {task_id}")
            instance.celery_subtask_id = task_id
            instance.save()
            logger.error(f"Task ID {instance.id}: Saved")
