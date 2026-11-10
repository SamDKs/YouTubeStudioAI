"""Conector llama.cpp por loopback; nunca descarga ni selecciona un modelo por sí solo."""

from urllib.parse import urlsplit
import requests

from app.domain.package_errors import NeedsReview,StudioError


class LocalLanguageModel:
    def __init__(self,base_url: str='http://127.0.0.1:8080',session=None) -> None:
        parsed=urlsplit(base_url)
        if parsed.scheme!='http' or parsed.hostname not in {'127.0.0.1','localhost','::1'} or parsed.username or parsed.password or parsed.path not in {'','/'}:
            raise StudioError('El modelo local debe ejecutarse en loopback, sin credenciales ni rutas adicionales.')
        self.base_url=base_url.rstrip('/');self.session=session or requests.Session()
        self.session.trust_env=False

    def models(self) -> tuple[str,...]:
        try:
            response=self.session.get(self.base_url+'/v1/models',timeout=5);response.raise_for_status()
            return tuple(item['id'] for item in response.json().get('data',[]))
        except (requests.RequestException,KeyError,ValueError):raise NeedsReview('No hay un servidor llama.cpp verificable en la dirección local.') from None

    def draft(self,model: str,idea: str,research: str,editorial: str, language: str = "en-US") -> dict:
        if model not in self.models():raise NeedsReview('El modelo elegido no está cargado en el servidor local.')
        languages={'en-US':'natural American English','es-419':'neutral Latin American Spanish'}
        if language not in languages:raise NeedsReview('Idioma no compatible para el borrador.')
        instructions=('Write original '+languages[language]+' narration. Respect the channel identity. Use only the supplied research, flag unsupported claims, include a 3–8 second hook, fulfil the title promise within 30 seconds, and distinguish facts from hypotheses. Never invent sources. Return a draft for human review.\n'+editorial)
        try:
            response=self.session.post(self.base_url+'/v1/chat/completions',json={'model':model,'messages':[{'role':'system','content':instructions},{'role':'user','content':'Idea: '+idea+'\nResearch: '+research}],'temperature':.5,'max_tokens':1800},timeout=180)
            response.raise_for_status();text=response.json()['choices'][0]['message']['content']
            if not isinstance(text,str) or not text.strip():raise ValueError('Empty draft')
            return {'text':text,'provider':'llama_cpp','model':model,'requires_review':True,'verified_quality':False}
        except (requests.RequestException,KeyError,IndexError,ValueError):raise NeedsReview('El modelo local no produjo un borrador utilizable; no se sustituyó por un proveedor pagado.') from None
