import logging

import httpx
from openai import OpenAI

from django.conf import settings
from openai.types.chat import ChatCompletion

timeout = httpx.Timeout(
    connect=60.0, # 60 seconds
    read=600.0, # 600 seconds
    write=60.0, # 60 seconds
    pool=300.0 # 300 seconds
)


class Gateway:
    def __init__(self, proxy_url: str, openai_api_key: str):
        http_client = httpx.Client(proxies={
            'http://': settings.PROXY_URL if proxy_url is None else proxy_url,
            'https://': settings.PROXY_URL if proxy_url is None else proxy_url,
        })
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY if openai_api_key is None else openai_api_key,
                             http_client=http_client, timeout=timeout)

    def ask(self, prompt: str, engine: str, is_json: bool = False, **kwargs) -> tuple[str, ChatCompletion]:
        new_kwargs = {}
        for key, value in kwargs.items():
            if value is not None:
                new_kwargs[key] = value
        if is_json:
            kwargs['response_format'] = {"type": "json_object"}
        response = self.client.chat.completions.create(model=engine, messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant. You only to write the answer, without any other intro/exit text."
            },
            {
                "role": "user",
                "content": prompt
            }
        ], **kwargs)
        logging.error(f"{prompt} -> {response.choices[0]}")
        logging.error(f"{response}")
        return prompt, response


class DeepseekGateway(Gateway):
    def __init__(self, proxy_url: str, openai_api_key: str):
        super().__init__(proxy_url, openai_api_key)
        http_client = httpx.Client()
        self.client = OpenAI(api_key=settings.DEEPSEEK_API_KEY if openai_api_key is None else openai_api_key,
                             http_client=http_client, base_url="https://api.deepseek.com/v1", timeout=timeout)


def resolve_gateway(request: 'Request') -> Gateway:
    if "deepseek" in request.engine:
        return DeepseekGateway(request.key.proxy_url, request.key.deepseek_api_key)
    return Gateway(request.key.proxy_url, request.key.openai_api_key)
